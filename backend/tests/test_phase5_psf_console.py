import pytest
import uuid
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_psf_dashboard_and_call_console():
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

        # 2. Test PSF Dashboard Stats Endpoint
        dash_res = await client.get("/api/v1/psf/dashboard", headers=headers)
        assert dash_res.status_code == 200
        stats = dash_res.json()
        assert "total_pending" in stats
        assert "total_contacted" in stats
        assert "connect_rate_pct" in stats
        assert "by_brand_branch" in stats
        assert "by_call_status" in stats

        # 3. Test List Calling Queues (Pick Hyundai queue)
        queues_res = await client.get("/api/v1/psf/queues?queue_type=PSF", headers=headers)
        assert queues_res.status_code == 200
        q_data = queues_res.json()
        assert "items" in q_data
        assert "total" in q_data
        assert len(q_data["items"]) > 0

        target_queue = next((item for item in q_data["items"] if "HYUN" in item["brand_code"].upper()), q_data["items"][0])
        queue_id = target_queue["id"]

        # Verify Customer snapshot
        assert target_queue["customer_phone_masked"].startswith("+91")
        assert "*" in target_queue["customer_phone_masked"]

        # 4. Test Call Console Dossier
        console_res = await client.get(f"/api/v1/psf/console/{queue_id}", headers=headers)
        assert console_res.status_code == 200
        console = console_res.json()
        assert "customer" in console
        assert "vehicle" in console
        assert "job_card" in console
        assert "call_history" in console
        assert "questionnaire" in console

        # Construct survey answers from the questionnaire's questions
        survey_answers = {}
        if console["questionnaire"] and console["questionnaire"]["questions"]:
            for q in console["questionnaire"]["questions"]:
                if q["type"] == "nps_10":
                    survey_answers[q["key"]] = 6  # Detractor score
                elif q["type"] == "rating_5":
                    survey_answers[q["key"]] = 2
                elif q["type"] in ["yes_no", "yes_no_na"]:
                    survey_answers[q["key"]] = "Yes"
        else:
            survey_answers = {"hyundai_recommend": 6}

        submit_payload = {
            "followup_queue_id": queue_id,
            "call_status": "Connected",
            "case_status": "Complaint Registered",
            "duration_seconds": 145,
            "voc": "Customer reported vibration at high speed after wheel alignment was done.",
            "survey_answers": survey_answers,
            "has_complaint": True,
            "complaint_severity": "HIGH",
            "complaint_description": "Vibration in steering at 80 km/h after service.",
        }

        call_res = await client.post("/api/v1/psf/calls/submit", json=submit_payload, headers=headers)
        assert call_res.status_code == 200
        call_data = call_res.json()
        assert call_data["queue_status"] == "COMPLAINT_REGISTERED"
        assert call_data["nps_score"] == 6
        assert call_data["nps_category"] == "DETRACTOR"
        assert call_data["complaint_ticket_no"] is not None
        assert call_data["complaint_ticket_no"].startswith("CMP-")

        # 6. Test Bulk Queue Assignment
        cre_user_id = console_res.json()["queue"]["assigned_to_id"] or console_res.json()["queue"]["customer_id"]
        bulk_res = await client.post(
            "/api/v1/psf/queues/bulk-assign",
            json={"queue_ids": [queue_id], "assigned_to_id": None},
            headers=headers,
        )
        assert bulk_res.status_code == 200
        assert bulk_res.json()["count"] == 1
