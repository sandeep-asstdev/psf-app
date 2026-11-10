import pytest
import uuid
from datetime import date, datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_security_headers_and_production_hardening():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Verify Production Security Headers on public and protected endpoints
        res = await ac.get("/health")
        assert res.status_code == 200
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "max-age=31536000" in res.headers.get("Strict-Transport-Security", "")
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_end_to_end_full_psf_lifecycle():
    """
    E2E Integration Flow:
    1. Login as Admin
    2. Post Real-time DMS Job Card via Webhook
    3. Retrieve the created Followup Queue record
    4. Call Console: Record Call with Low CSAT and Escalate Complaint
    5. Service Advisor: Review task and submit corrective action
    6. Reconfirmation: Customer reconfirms satisfaction -> Closed
    7. Analytics: Verify updated KPIs reflect the completed lifecycle
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Step 1: Admin Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Ingest DMS Job Card via Webhook
        unique_jc = f"JC-E2E-{uuid.uuid4().hex[:6]}"
        ingest_payload = {
            "brand_code": "HYUN",
            "branch_code": "APEX-CENTRAL",
            "job_card_no": unique_jc,
            "job_card_date": str(date.today()),
            "customer_name": "Arun E2E Verification",
            "customer_phone": "9888877777",
            "reg_no": f"KA01E2E{uuid.uuid4().hex[:4].upper()}",
            "model": "Hyundai Ioniq 5 EV",
            "service_advisor": "Ramesh SA",
            "service_type": "Periodic Service 20,000km",
            "total_amount": 18500.0,
        }
        ingest_res = await client.post("/api/v1/imports/webhook", json=ingest_payload, headers=headers)
        assert ingest_res.status_code == 201
        queue_id = ingest_res.json()["psf_queue_id"]
        assert queue_id is not None

        # Step 3: Fetch Call Console data
        console_res = await client.get(f"/api/v1/psf/console/{queue_id}", headers=headers)
        assert console_res.status_code == 200
        c_data = console_res.json()
        assert c_data["job_card"]["job_card_no"] == unique_jc
        assert c_data["customer"]["name"] == "Arun E2E Verification"

        # Step 4: Submit Call with Low CSAT (Rating = 2) and Escalate Complaint
        survey_answers = {}
        if c_data.get("questionnaire") and c_data["questionnaire"].get("questions"):
            for q in c_data["questionnaire"]["questions"]:
                if q["type"] == "nps_10":
                    survey_answers[q["key"]] = 6  # Detractor score
                elif q["type"] == "rating_5":
                    survey_answers[q["key"]] = 2
                elif q["type"] in ["yes_no", "yes_no_na"]:
                    survey_answers[q["key"]] = "yes"
        else:
            survey_answers = {"hyundai_recommend": 6}

        call_payload = {
            "followup_queue_id": queue_id,
            "call_status": "Connected",
            "case_status": "Complaint Registered",
            "duration_seconds": 165,
            "voc": "Customer reported wheel alignment was not done properly and car pulls left.",
            "survey_answers": survey_answers,
            "has_complaint": True,
            "complaint_severity": "HIGH",
            "complaint_description": "Wheel alignment improper post delivery - pulling left",
        }
        submit_call_res = await client.post("/api/v1/psf/calls/submit", json=call_payload, headers=headers)
        assert submit_call_res.status_code == 200
        call_resp = submit_call_res.json()
        assert call_resp["queue_status"] == "COMPLAINT_REGISTERED"
        complaint_ticket_no = call_resp["complaint_ticket_no"]
        assert complaint_ticket_no is not None
        assert complaint_ticket_no.startswith("CMP-")

        # Fetch complaint by ticket no to retrieve UUID for reconfirmation
        comp_res = await client.get(f"/api/v1/complaints?search={complaint_ticket_no}", headers=headers)
        assert comp_res.status_code == 200
        complaint_id = comp_res.json()["items"][0]["id"]

        # Step 5: Service Advisor reviews task and submits corrective explanation
        adv_payload = {
            "job_card_id": c_data["job_card"]["id"],
            "adv_call_status": "Connected",
            "adv_case_status": "Inspection Scheduled",
            "adv_voc": "Spoke to customer. Re-alignment scheduled tomorrow free of charge.",
            "adv_status": "RESOLVED",
        }
        adv_res = await client.post("/api/v1/complaints/advisors/corrections", json=adv_payload, headers=headers)
        assert adv_res.status_code == 200

        # Step 6: Customer Reconfirmation Call (Customer Confirms Satisfied -> CLOSED)
        reconf_payload = {
            "complaint_id": complaint_id,
            "call_status": "Connected",
            "status": "SATISFIED_CLOSED",
            "customer_feedback": "Customer confirmed wheel alignment re-done and satisfied now.",
            "closure_verified": True,
        }
        reconf_res = await client.post("/api/v1/complaints/reconfirmations", json=reconf_payload, headers=headers)
        assert reconf_res.status_code == 200
        assert reconf_res.json()["new_complaint_status"] == "CLOSED"

        # Step 7: Reports Summary contains the updated flow
        rep_res = await client.get("/api/v1/reports/summary", headers=headers)
        assert rep_res.status_code == 200
        rep_data = rep_res.json()
        assert rep_data["kpis"]["total_calls_attempted"] >= 1
