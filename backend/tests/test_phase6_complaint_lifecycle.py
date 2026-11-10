import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_complaint_lifecycle_and_reconfirmation():
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

        # 2. Get Complaints List
        comp_res = await client.get("/api/v1/complaints", headers=headers)
        assert comp_res.status_code == 200
        comp_data = comp_res.json()
        assert "items" in comp_data
        assert "total" in comp_data
        assert len(comp_data["items"]) > 0

        target_complaint = next((c for c in comp_data["items"] if c["status"] == "OPEN" and not c["complaint_no"].startswith("CMP-S")), comp_data["items"][0])
        complaint_id = target_complaint["id"]
        assert target_complaint["complaint_no"].startswith("CMP-")

        # 3. Get Detail with Event Timeline
        detail_res = await client.get(f"/api/v1/complaints/{complaint_id}", headers=headers)
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert "events" in detail
        assert len(detail["events"]) >= 1
        assert detail["events"][0]["event_type"] == "CREATED"

        # 4. Status Transition: OPEN -> IN_PROGRESS
        in_prog_res = await client.put(
            f"/api/v1/complaints/{complaint_id}/status",
            json={"status": "IN_PROGRESS", "remarks": "Workshop manager inspected vehicle"},
            headers=headers,
        )
        assert in_prog_res.status_code == 200
        assert in_prog_res.json()["status"] == "IN_PROGRESS"

        # 5. Status Transition: IN_PROGRESS -> RESOLVED (Triggers auto reconfirmation calling queue!)
        resolved_res = await client.put(
            f"/api/v1/complaints/{complaint_id}/status",
            json={
                "status": "RESOLVED",
                "resolution_remarks": "Steering wheel recalibrated and wheel balance re-done free of charge.",
            },
            headers=headers,
        )
        assert resolved_res.status_code == 200
        assert resolved_res.json()["status"] == "RESOLVED"
        assert resolved_res.json()["resolution_remarks"] is not None

        # 6. Verify Reconfirmation Queue was auto-scheduled for 24h later
        reconf_q_res = await client.get("/api/v1/psf/queues?queue_type=RECONFIRMATION", headers=headers)
        assert reconf_q_res.status_code == 200
        assert len(reconf_q_res.json()["items"]) > 0

        # 7. Post-Resolution Reconfirmation Call: Customer Confirms Satisfaction
        reconf_payload = {
            "complaint_id": complaint_id,
            "call_status": "Connected",
            "status": "SATISFIED_CLOSED",
            "customer_feedback": "Customer confirmed vehicle is driving smoothly with zero vibration.",
            "closure_verified": True,
        }
        submit_reconf_res = await client.post(
            "/api/v1/complaints/reconfirmations",
            json=reconf_payload,
            headers=headers,
        )
        assert submit_reconf_res.status_code == 200
        assert submit_reconf_res.json()["new_complaint_status"] == "CLOSED"

        # 8. Test Service Advisor Follow-up Tasks
        adv_res = await client.get("/api/v1/complaints/advisors/tasks", headers=headers)
        assert adv_res.status_code == 200
        adv_tasks = adv_res.json()
        assert len(adv_tasks) > 0

        # Advisor submits correction
        adv_correct_res = await client.post(
            "/api/v1/complaints/advisors/corrections",
            json={
                "job_card_id": adv_tasks[0]["job_card_id"],
                "adv_call_status": "Connected",
                "adv_case_status": "Customer Convinced",
                "adv_voc": "Personally called customer and ensured rework done under senior technician supervision.",
                "adv_status": "RESOLVED",
            },
            headers=headers,
        )
        assert adv_correct_res.status_code == 200

        # 9. Test Happiness Calling Queue (HYUNDAI EXCLUSIVE RULE)
        hap_res = await client.get("/api/v1/complaints/happiness/queues", headers=headers)
        assert hap_res.status_code == 200
        hap_items = hap_res.json()["items"]
        assert len(hap_items) > 0
        for item in hap_items:
            assert "HYUN" in item["brand_code"].upper()

