import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Root health
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

        # Api v1 health
        res_v1 = await client.get("/api/v1/health")
        assert res_v1.status_code == 200
        assert res_v1.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_auth_and_questionnaire_oem_restriction():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login as Admin
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get Brands
        brands_res = await client.get("/api/v1/masters/brands", headers=headers)
        assert brands_res.status_code == 200
        brands = brands_res.json()
        hyundai = next((b for b in brands if "HYUNDAI" in b["name"].upper()), None)
        mg = next((b for b in brands if "MG" in b["name"].upper()), None)

        assert hyundai is not None
        assert hyundai["has_happiness_calling"] is True
        assert mg is not None
        assert mg["has_happiness_calling"] is False

        # 3. List Questionnaires
        q_res = await client.get("/api/v1/questionnaires", headers=headers)
        assert q_res.status_code == 200
        q_list = q_res.json()
        assert len(q_list) >= 5

        # 4. OEM Constraint Verification:
        # Creating a HAPPINESS questionnaire for MG must be blocked with HTTP 400
        bad_payload = {
            "brand_id": mg["id"],
            "type": "HAPPINESS",
            "title": "Unauthorized MG Happiness Survey",
            "is_active": True,
        }
        blocked_res = await client.post("/api/v1/questionnaires", json=bad_payload, headers=headers)
        assert blocked_res.status_code == 400
        assert "exclusively permitted for Hyundai" in blocked_res.json()["detail"]

