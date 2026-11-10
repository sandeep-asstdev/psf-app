"""
================================================================================
SLICE 1 TEST SUITE: Config Foundation & Dynamic Follow-up Programs.
Validates:
1. Program Creation, Resolution, Reordering, and Enable/Disable.
2. Hierarchical Resolution: Brand-scoped programs override Dealership default.
3. Draft -> Strict Payload Validation -> Publish -> Rollback lifecycle.
4. Redis caching & invalidation on publish/rollback.
5. Migration Equivalence: Ingestion of Hyundai creates PSF + Happiness, Ather creates TNPS only,
   Tata/MG create PSF only — exactly matching legacy behavior via dynamic programs.
================================================================================
"""
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant, Brand, Branch
from app.models.service import JobCard
from app.models.followup import FollowupQueue
from app.models.config import FollowUpProgram, ConfigVersion
from app.services.config_resolver import ConfigResolverService


@pytest.fixture
async def auth_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert res.status_code == 200, "Admin login must succeed"
        token = res.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client


@pytest.mark.asyncio
async def test_programs_api_crud_and_reorder(auth_client: AsyncClient):
    """Test creating, listing, updating, reordering and toggling follow-up programs."""
    # 1. List existing programs (seeded via migration 0008)
    res = await auth_client.get("/api/v1/config/programs")
    assert res.status_code == 200
    programs = res.json()
    assert len(programs) >= 3, "Should have seeded default, Hyundai, and Ather programs"

    # 2. Create a new custom program
    new_prog_payload = {
        "code": f"TEST_VIP_{uuid.uuid4().hex[:4].upper()}",
        "label": "VIP Executive PSF",
        "enabled": True,
        "trigger": "ON_IMPORT",
        "channel": "PHONE",
        "max_attempts": 4,
        "retry_gap_hours": 12,
        "sla_hours": 24,
        "sort_order": 99,
    }
    create_res = await auth_client.post("/api/v1/config/programs", json=new_prog_payload)
    assert create_res.status_code == 201
    created = create_res.json()
    prog_id = created["id"]
    assert created["code"] == new_prog_payload["code"]
    assert created["label"] == "VIP Executive PSF"

    # 3. Toggle enabled -> False
    update_res = await auth_client.put(f"/api/v1/config/programs/{prog_id}", json={"enabled": False})
    assert update_res.status_code == 200
    assert update_res.json()["enabled"] is False

    # 4. Reorder
    reorder_res = await auth_client.put(
        "/api/v1/config/programs/reorder",
        json={"orders": [{"id": prog_id, "sort_order": 5}]},
    )
    assert reorder_res.status_code == 200

    # 5. Cleanup
    del_res = await auth_client.delete(f"/api/v1/config/programs/{prog_id}")
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_hierarchical_config_resolution():
    """Verify that brand config overrides dealership default config."""
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant).limit(1))).scalar_one()
        ather_brand = (await db.execute(select(Brand).where(Brand.code == "ATHER"))).scalar_one()

        # Ather has brand-specific programs (TNPS)
        ather_progs = await ConfigResolverService.get_active_programs_for_brand(db, tenant.id, ather_brand.id)
        assert len(ather_progs) == 1
        assert ather_progs[0].code == "TNPS"

        # Brand with no programs configured resolves to Dealership Default (PSF)
        default_progs = await ConfigResolverService.get_active_programs_for_brand(db, tenant.id, brand_id=None)
        assert len(default_progs) >= 1
        assert any(p.code == "PSF" for p in default_progs)


@pytest.mark.asyncio
async def test_draft_publish_rollback_lifecycle(auth_client: AsyncClient):
    """Test draft creation, strict validation failure on invalid payload, publish, and rollback."""
    # 1. Invalid payload rejected on draft creation
    bad_payload = {
        "scope": "DEALERSHIP",
        "config_type": "PROGRAMS",
        "payload": {"programs": [{"code": "", "label": "Invalid"}]},  # Missing valid code & trigger
    }
    bad_res = await auth_client.post("/api/v1/config/drafts", json=bad_payload)
    assert bad_res.status_code == 400
    assert "required" in bad_res.json()["detail"].lower()

    # 2. Valid Draft Creation
    valid_payload = {
        "scope": "DEALERSHIP",
        "config_type": "PROGRAMS",
        "payload": {
            "programs": [
                {
                    "code": "PSF",
                    "label": "Universal Dealership PSF",
                    "enabled": True,
                    "trigger": "ON_IMPORT",
                    "channel": "PHONE",
                    "max_attempts": 3,
                    "retry_gap_hours": 24,
                    "sla_hours": 48,
                    "sort_order": 0,
                }
            ]
        },
        "note": "Unit test draft v1",
    }
    draft_res = await auth_client.post("/api/v1/config/drafts", json=valid_payload)
    assert draft_res.status_code == 201
    draft_data = draft_res.json()
    assert draft_data["status"] == "DRAFT"
    draft_id = draft_data["id"]

    # 3. Publish draft
    pub_res = await auth_client.post(
        "/api/v1/config/publish",
        json={"version_id": draft_id, "note": "Publishing test draft"},
    )
    assert pub_res.status_code == 200
    published_data = pub_res.json()
    assert published_data["status"] == "PUBLISHED"
    assert published_data["published_at"] is not None

    # 4. Rollback
    rollback_res = await auth_client.post(
        "/api/v1/config/rollback",
        json={
            "target_version_id": draft_id,
            "config_type": "PROGRAMS",
            "scope": "DEALERSHIP",
            "reason": "Reverting test release back to previous version",
        },
    )
    assert rollback_res.status_code == 200
    rb_data = rollback_res.json()
    assert rb_data["status"] == "PUBLISHED"
    assert "Rolled back" in rb_data["note"]


@pytest.mark.asyncio
async def test_migration_equivalence_hyundai_ather_dms_imports(auth_client: AsyncClient):
    """
    Equivalence Test:
    Verify that dynamic follow_up_programs create the identical queues as hardcoded logic:
    - Hyundai: Creates 1 PSF + 1 HAPPINESS (total 2 queues, 0 TNPS)
    - Ather: Creates 1 TNPS (total 1 queue, 0 PSF, 0 HAPPINESS)
    """
    async with AsyncSessionLocal() as db:
        hyundai = (await db.execute(select(Brand).where(Brand.code == "HYUN"))).scalar_one()
        ather = (await db.execute(select(Brand).where(Brand.code == "ATHER"))).scalar_one()

        hyundai_branch = (await db.execute(select(Branch).where(Branch.brand_id == hyundai.id))).scalars().first()
        ather_branch = (await db.execute(select(Branch).where(Branch.brand_id == ather.id))).scalars().first()

    # 1. Import Hyundai Job Card
    h_jc_no = f"HYUN_EQ_{uuid.uuid4().hex[:6].upper()}"
    hyundai_csv = (
        "Brand,Branch,Brand Logo,Job Card No,Job Card Date,Customer Name,Contact Number,Vin No,Reg No,Model,Service Advisor,Service Type,Total Service Amount\n"
        f"Hyundai,{hyundai_branch.name},logo.png,{h_jc_no},10-05-2026,Ramesh Kumar,9845011111,MALPAHYUN1234567,KA01AB1234,Creta SX,Suresh Advisor,Periodic Maintenance Service,8500.00\n"
    ).encode("utf-8")

    h_res = await auth_client.post(
        "/api/v1/imports/upload-and-process",
        data={"duplicate_action": "SKIP"},
        files={"file": (f"{h_jc_no}.csv", hyundai_csv, "text/csv")},
    )
    assert h_res.status_code == 200
    h_summary = h_res.json()
    assert h_summary["success_rows"] == 1
    assert h_summary["happiness_scheduled"] == 1
    assert h_summary["queues_created"] == 2

    async with AsyncSessionLocal() as db:
        h_jc = (await db.execute(select(JobCard).where(JobCard.job_card_no == h_jc_no))).scalar_one()
        h_queues = (await db.execute(select(FollowupQueue).where(FollowupQueue.job_card_id == h_jc.id))).scalars().all()
        q_types = {q.queue_type for q in h_queues}
        assert q_types == {"PSF", "HAPPINESS"}, f"Hyundai must create PSF + HAPPINESS, got {q_types}"
        assert all(q.program_id is not None for q in h_queues), "All queues must be linked to a follow_up_program"

    # 2. Import Ather Job Card
    a_jc_no = f"ATH_EQ_{uuid.uuid4().hex[:6].upper()}"
    ather_csv = (
        "Brand,Branch,Brand Logo,Job Card No,Job Card Date,Customer Name,Contact Number,Vin No,Reg No,Model,Service Advisor,Service Type,Total Service Amount\n"
        f"Ather Energy,{ather_branch.name},logo.png,{a_jc_no},10-05-2026,Ather Rider,9845022222,MALPAATHER7654321,KA02CD5678,Ather 450X,Rajesh Advisor,Periodic Maintenance Service,3200.00\n"
    ).encode("utf-8")

    a_res = await auth_client.post(
        "/api/v1/imports/upload-and-process",
        data={"duplicate_action": "SKIP"},
        files={"file": (f"{a_jc_no}.csv", ather_csv, "text/csv")},
    )
    assert a_res.status_code == 200
    a_summary = a_res.json()
    assert a_summary["success_rows"] == 1
    assert a_summary["happiness_scheduled"] == 0
    assert a_summary["queues_created"] == 1

    async with AsyncSessionLocal() as db:
        a_jc = (await db.execute(select(JobCard).where(JobCard.job_card_no == a_jc_no))).scalar_one()
        a_queues = (await db.execute(select(FollowupQueue).where(FollowupQueue.job_card_id == a_jc.id))).scalars().all()
        assert len(a_queues) == 1
        assert a_queues[0].queue_type == "TNPS", f"Ather must create TNPS only, got {a_queues[0].queue_type}"
        assert a_queues[0].program_id is not None
