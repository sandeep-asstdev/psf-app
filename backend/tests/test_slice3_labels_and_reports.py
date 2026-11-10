"""
================================================================================
SLICE 3 TEST SUITE: Labels & Dynamic Reports.
Validates:
1. label_overrides CRUD (GET, POST batch upsert, DELETE reset)
2. Dynamic report aggregation using kpi_tag and normalised scores
3. NPS calculation from any 0-10 recommend question
4. KPI comparison by brand/branch and complaint ageing buckets
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
from app.models.followup import Call, SurveyResponse
from app.models.complaint import Complaint
from app.services.report_service import get_comprehensive_report_data


@pytest.fixture
async def auth_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.mark.asyncio
async def test_label_overrides_crud(auth_client: AsyncClient):
    """Test GET, POST batch upsert, and DELETE for label overrides."""
    # 1. GET default labels
    get_res = await auth_client.get("/api/v1/config/labels")
    assert get_res.status_code == 200
    labels = get_res.json()
    assert "CRE" in labels
    assert "JOB_CARD" in labels
    assert "COMPLAINT" in labels

    # 2. POST update custom labels
    update_payload = {
        "labels": {
            "CRE": "Calling Specialist",
            "JOB_CARD": "Repair Order (RO)",
            "COMPLAINT": "Customer Escalation",
            "TNPS": "Ather TNPS Survey",
        },
        "language": "en",
    }
    post_res = await auth_client.post("/api/v1/config/labels", json=update_payload)
    assert post_res.status_code == 200
    updated_labels = post_res.json()
    assert updated_labels["CRE"] == "Calling Specialist"
    assert updated_labels["JOB_CARD"] == "Repair Order (RO)"
    assert updated_labels["COMPLAINT"] == "Customer Escalation"
    assert updated_labels["TNPS"] == "Ather TNPS Survey"

    # 3. DELETE reset label
    del_res = await auth_client.delete("/api/v1/config/labels/CRE")
    assert del_res.status_code == 200
    get_res_after = await auth_client.get("/api/v1/config/labels")
    assert get_res_after.json()["CRE"] == "Customer Relationship Executive"


@pytest.mark.asyncio
async def test_dynamic_reports_kpi_tags_and_scores():
    """Test report service calculates CSAT, NPS, KPI comparisons and complaint ageing without question keys."""
    async with AsyncSessionLocal() as db:
        # Fetch tenant
        tenant = (await db.execute(select(Tenant).limit(1))).scalar_one()

        report = await get_comprehensive_report_data(
            db=db,
            tenant_id=tenant.id,
        )

        assert report.kpis is not None
        assert report.kpis.total_job_cards > 0
        assert report.kpis.average_csat >= 0.0
        assert report.kpis.net_promoter_score is not None

        # Check KPI comparisons by brand/branch
        assert report.kpi_comparisons is not None
        assert isinstance(report.kpi_comparisons, list)

        # Check Complaint Ageing
        assert report.complaint_ageing is not None
        assert len(report.complaint_ageing) == 4
        brackets = [b.age_bracket for b in report.complaint_ageing]
        assert "<24h" in brackets
        assert "24-48h" in brackets
        assert "48-72h" in brackets
        assert ">72h" in brackets
