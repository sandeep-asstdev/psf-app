"""
============================================================================
FILE PURPOSE: Ather Energy TNPS Model Correction & Brand Scoping Tests.
Tests the verified domain architecture:
1. Ather Energy follow-up program is brand-scoped with queue_type="TNPS" (PSF-style).
2. Ather imports create TNPS queue items only (0 PSF, 0 Happiness).
3. Hyundai imports create PSF + Happiness items (0 TNPS).
4. Dashboard "TNPS Calls" widget displays only Ather branches.
5. Ather Call Console dynamically presents Ather TNPS Questionnaire (ather_jobs_satisfaction & ather_tnps_rating).
6. JobCard.legacy_tnps_date preserves legacy DMS audit data without scheduling unwanted calls.
============================================================================
"""
import pytest
import uuid
from datetime import date
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant, Brand, Branch
from app.models.service import JobCard
from app.models.followup import FollowupQueue


@pytest.mark.asyncio
async def test_ather_import_creates_tnps_queue_only():
    """Verify that importing Ather DMS rows creates queue_type='TNPS' and 0 PSF/Happiness items."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Check Ather brand configuration in database
        async with AsyncSessionLocal() as db:
            ather_brand = (await db.execute(select(Brand).where(Brand.code == "ATHER"))).scalar_one_or_none()
            assert ather_brand is not None, "Ather brand should be seeded"
            assert ather_brand.enable_tnps is True
            assert ather_brand.tnps_label == "TNPS"

            ather_branch = (await db.execute(select(Branch).where(Branch.brand_id == ather_brand.id))).scalars().first()
            assert ather_branch is not None, "Ather branch should be seeded"
            ather_branch_name = ather_branch.name

        jc_no = f"ATHER_{uuid.uuid4().hex[:6].upper()}"
        csv_content = (
            "Brand,Branch,Brand Logo,Job Card No,Job Card Date,Customer Name,Contact Number,Vin No,Reg No,Model,Service Advisor,Service Type,Total Service Amount\n"
            f"Ather Energy,{ather_branch_name},logo.png,{jc_no},10-05-2026,Ather Rider One,9845012345,MALPAATHER1234567,KA25AT1111,Ather 450X,Rajesh Kumar,Periodic Maintenance Service,4500.00\n"
        ).encode("utf-8")

        res = await client.post(
            "/api/v1/imports/upload-and-process",
            data={"duplicate_action": "SKIP"},
            files={"file": (f"ather_{jc_no}.csv", csv_content, "text/csv")},
            headers=headers,
        )
        assert res.status_code == 200
        summary = res.json()
        assert summary["success_rows"] == 1
        assert summary["queues_created"] == 1  # 1 TNPS queue item only

        # Query created queues from database
        async with AsyncSessionLocal() as db:
            q_res = await db.execute(
                select(FollowupQueue)
                .join(JobCard, FollowupQueue.job_card_id == JobCard.id)
                .where(JobCard.job_card_no == jc_no)
            )
            queues = q_res.scalars().all()

            # Must have exactly 1 queue item of type TNPS
            assert len(queues) == 1
            assert queues[0].queue_type == "TNPS"
            assert queues[0].status == "PENDING"


@pytest.mark.asyncio
async def test_hyundai_import_creates_psf_and_happiness_zero_tnps():
    """Verify that importing Hyundai DMS rows creates PSF + Happiness items and 0 TNPS items."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        jc_no = f"HYUN_{uuid.uuid4().hex[:6].upper()}"
        csv_content = (
            "Brand,Branch,Brand Logo,Job Card No,Job Card Date,Customer Name,Contact Number,Vin No,Reg No,Model,Service Advisor,Service Type,Total Service Amount\n"
            f"Hyundai,HYUNDAI HUBLI,logo.png,{jc_no},10-05-2026,Hyundai Driver One,9845098765,MALCUHYUN12345678,KA25HY2222,Creta 1.5,Rajesh Kumar,Paid Service,7500.00\n"
        ).encode("utf-8")

        res = await client.post(
            "/api/v1/imports/upload-and-process",
            data={"duplicate_action": "SKIP"},
            files={"file": (f"hyun_{jc_no}.csv", csv_content, "text/csv")},
            headers=headers,
        )
        assert res.status_code == 200
        summary = res.json()
        assert summary["success_rows"] == 1
        assert summary["queues_created"] == 2  # 1 PSF + 1 Happiness Calling

        # Query created queues
        async with AsyncSessionLocal() as db:
            q_res = await db.execute(
                select(FollowupQueue)
                .join(JobCard, FollowupQueue.job_card_id == JobCard.id)
                .where(JobCard.job_card_no == jc_no)
            )
            queues = q_res.scalars().all()

            types = [q.queue_type for q in queues]
            assert "PSF" in types
            assert "HAPPINESS" in types
            assert "TNPS" not in types


@pytest.mark.asyncio
async def test_tnps_calls_widget_dashboard_ather_branches_only():
    """Verify that dashboard tnps_calls_by_branch only lists Ather branches."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        dash_res = await client.get("/api/v1/psf/dashboard", headers=headers)
        assert dash_res.status_code == 200
        stats = dash_res.json()

        assert "tnps_calls_by_branch" in stats
        tnps_branches = stats["tnps_calls_by_branch"]

        # If any branches are present in tnps_calls_by_branch, they MUST be Ather branches
        for b in tnps_branches:
            assert b["brand_code"].upper() in ["ATHER", "ATHER_ENERGY"] or "ATHER" in b["branch_name"].upper()
            assert "HYUNDAI" not in b["branch_name"].upper()


@pytest.mark.asyncio
async def test_ather_tnps_questionnaire_and_console_scoring():
    """Verify that Ather TNPS console loads Ather questionnaire and scores CSAT / NPS."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Find an Ather TNPS queue item
        queues_res = await client.get("/api/v1/psf/queues?queue_type=TNPS&limit=5", headers=headers)
        assert queues_res.status_code == 200
        items = queues_res.json().get("items", [])
        if not items:
            pytest.skip("No Ather TNPS items found for console test")

        q_id = items[0]["id"]

        # Open Call Console
        console_res = await client.get(f"/api/v1/psf/console/{q_id}", headers=headers)
        assert console_res.status_code == 200
        console = console_res.json()

        # Questionnaire must be of type TNPS with Ather questions
        assert console["questionnaire"] is not None
        assert console["questionnaire"]["type"] == "TNPS"
        q_keys = [q["key"] for q in console["questionnaire"]["questions"]]
        assert "ather_jobs_satisfaction" in q_keys
        assert "ather_tnps_rating" in q_keys

        # Submit call attempt with Promoter score (9)
        payload = {
            "followup_queue_id": q_id,
            "call_status": "Connected",
            "case_status": "Satisfied",
            "duration_seconds": 65,
            "voc": "Smooth scooter performance after general service",
            "survey_answers": {
                "ather_jobs_satisfaction": "Yes",
                "ather_tnps_rating": 9,
            },
            "has_complaint": False,
        }
        submit_res = await client.post("/api/v1/psf/calls/submit", json=payload, headers=headers)
        assert submit_res.status_code == 200
        data = submit_res.json()
        assert data["queue_status"] == "CONTACTED"
        assert data["nps_score"] == 9
        assert data["nps_category"] == "PROMOTER"


@pytest.mark.asyncio
async def test_legacy_tnps_date_field_no_scheduling():
    """Verify that JobCard.legacy_tnps_date stores legacy date without secondary queue generation."""
    async with AsyncSessionLocal() as db:
        from app.models.customer import Customer, Vehicle

        tenant = (await db.execute(select(Tenant).limit(1))).scalar_one()
        hyundai_brand = (await db.execute(select(Brand).where(Brand.code == "HYUN"))).scalar_one()
        hyundai_branch = (await db.execute(select(Branch).where(Branch.brand_id == hyundai_brand.id))).scalars().first()
        cust = (await db.execute(select(Customer).limit(1))).scalar_one()
        veh = (await db.execute(select(Vehicle).limit(1))).scalar_one()

        jc = JobCard(
            tenant_id=tenant.id,
            brand_id=hyundai_brand.id,
            branch_id=hyundai_branch.id,
            customer_id=cust.id,
            vehicle_id=veh.id,
            job_card_no=f"LEGACY_TEST_{uuid.uuid4().hex[:6]}",
            job_card_date=date(2026, 3, 30),
            legacy_tnps_date=date(2026, 4, 9),
            total_amount=Decimal("1200.00"),
        )
        db.add(jc)
        await db.commit()
        await db.refresh(jc)

        assert jc.legacy_tnps_date == date(2026, 4, 9)

        # Confirm no FollowupQueue with scheduled_tnps_date was created
        q_res = await db.execute(select(FollowupQueue).where(FollowupQueue.job_card_id == jc.id))
        assert len(q_res.scalars().all()) == 0
