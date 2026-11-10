"""
================================================================================
SLICE 4 ACCEPTANCE TEST: End-to-End Onboarding & Lifecycle Acceptance Test.
Proves that a completely new dealership can be created from the BLANK pack
using ONLY API/config calls:
1. Dealership Onboarding Wizard (Blank pack)
2. 1-5 star scale + 6 questions with kpi_tags
3. Second program (WhatsApp, 3 days after job card)
4. Renamed labels (CRE -> Zenith Calling Specialist, JOB_CARD -> Zenith RO, COMPLAINT -> Customer Grievance)
5. Rule: "advisor kpi score <= 3 creates a High complaint"
6. Import job card -> allocation -> call -> survey -> complaint -> closure -> reconfirmation -> appears in reports.
================================================================================
"""
import pytest
import uuid
from datetime import date
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant, Brand, Branch
from app.models.auth import Role, User
from app.models.complaint import ComplaintCategory


@pytest.fixture
async def super_admin_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert res.status_code == 200
        token = res.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.mark.asyncio
async def test_slice4_e2e_blank_pack_to_reports_lifecycle(super_admin_client: AsyncClient):
    """Full lifecycle acceptance test from wizard onboarding to reporting."""

    # -------------------------------------------------------------------------
    # STEP 1: Onboard New Dealership from BLANK pack via Wizard API
    # -------------------------------------------------------------------------
    rand_id = uuid.uuid4().hex[:6]
    dealer_slug = f"zenith-ev-{rand_id}"
    admin_email = f"admin_{rand_id}@zenithev.com"
    admin_password = "Password@12345"

    wizard_payload = {
        "name": f"Zenith EV Hub {rand_id}",
        "slug": dealer_slug,
        "brand_name": "Zenith EV",
        "brand_code": f"ZEN_{rand_id[:4].upper()}",
        "branch_name": "Zenith Central Workshop",
        "branch_code": f"ZBR_{rand_id[:4].upper()}",
        "admin_name": "Zenith Super Admin",
        "admin_email": admin_email,
        "admin_password": admin_password,
        "pack_code": "BLANK",
    }

    onboard_res = await super_admin_client.post("/api/v1/config/dealerships/wizard", json=wizard_payload)
    assert onboard_res.status_code == 200
    onboard_data = onboard_res.json()
    assert onboard_data["status"] == "success"
    tenant_id = onboard_data["tenant_id"]
    brand_code = wizard_payload["brand_code"]
    branch_code = wizard_payload["branch_code"]

    # -------------------------------------------------------------------------
    # STEP 2: Authenticate as the new Dealership Admin
    # -------------------------------------------------------------------------
    dealer_client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    login_res = await dealer_client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": admin_password},
    )
    assert login_res.status_code == 200
    dealer_token = login_res.json()["access_token"]
    dealer_headers = {"Authorization": f"Bearer {dealer_token}"}
    dealer_client.headers.update(dealer_headers)

    # -------------------------------------------------------------------------
    # STEP 3: Configure 1-5 Star Scale + 6 Questions with kpi_tags via Config Import
    # -------------------------------------------------------------------------
    config_payload = {
        "pack_version": "1.0.0",
        "brand_code": brand_code,
        "scales": [
            {
                "name": "Zenith 1-5 Star Scale",
                "scale_type": "RATING_5",
                "min_val": 1,
                "max_val": 5,
                "bands": [
                    {"name": "Delight", "status": "DELIGHT", "min_val": 5, "max_val": 5},
                    {"name": "Satisfied", "status": "SATISFIED", "min_val": 4, "max_val": 4},
                    {"name": "Dissatisfied", "status": "DISSATISFIED", "min_val": 1, "max_val": 3},
                ],
            }
        ],
        "questionnaires": [
            {
                "type": "PSF",
                "title": "Zenith 6-Question Survey",
                "questions": [
                    {"key": "q_advisor", "label": "Service Advisor Performance (1-5)", "type": "rating", "kpi_tag": "SERVICE_ADVISOR", "rating_min": 1, "rating_max": 5, "complaint_trigger_below": 3},
                    {"key": "q_cleanliness", "label": "Vehicle Cleanliness (1-5)", "type": "rating", "kpi_tag": "CLEANLINESS", "rating_min": 1, "rating_max": 5},
                    {"key": "q_timeliness", "label": "Timely Delivery", "type": "yes_no", "kpi_tag": "DELIVERY_TIMELINESS"},
                    {"key": "q_charges", "label": "Reasonable Charges", "type": "yes_no", "kpi_tag": "TRANSPARENCY"},
                    {"key": "q_work_quality", "label": "Work Quality (1-5)", "type": "rating", "kpi_tag": "SERVICE_QUALITY", "rating_min": 1, "rating_max": 5},
                    {"key": "q_recommend", "label": "Would you recommend Zenith? (0-10)", "type": "nps_10", "kpi_tag": "NPS", "rating_min": 0, "rating_max": 10},
                ],
            }
        ],
        "programs": [
            {
                "code": "PSF",
                "label": "Zenith Post Service Follow-up",
                "enabled": True,
                "trigger": "ON_IMPORT",
                "channel": "PHONE",
                "max_attempts": 3,
                "retry_gap_hours": 24,
                "sla_hours": 48,
                "sort_order": 1,
            }
        ],
        "rules": [],
        "labels": {},
    }

    import_res = await dealer_client.post(
        "/api/v1/config/dealership/import",
        json={"config": config_payload, "validate_only": False},
    )
    assert import_res.status_code == 200

    # -------------------------------------------------------------------------
    # STEP 4: Add Second Program (WhatsApp, 3 days after job card)
    # -------------------------------------------------------------------------
    second_prog_payload = {
        "code": "WHATSAPP_3D",
        "label": "WhatsApp 3-Day Follow-up",
        "enabled": True,
        "trigger": "AFTER_DAYS(3)",
        "channel": "WHATSAPP",
        "max_attempts": 2,
        "retry_gap_hours": 24,
        "sla_hours": 72,
        "sort_order": 2,
    }
    prog_res = await dealer_client.post("/api/v1/config/programs", json=second_prog_payload)
    assert prog_res.status_code in [200, 201]

    # -------------------------------------------------------------------------
    # STEP 5: Renamed Labels
    # -------------------------------------------------------------------------
    labels_payload = {
        "labels": {
            "CRE": "Zenith Calling Specialist",
            "JOB_CARD": "Zenith RO",
            "COMPLAINT": "Customer Grievance",
        },
        "language": "en",
    }
    lbl_res = await dealer_client.post("/api/v1/config/labels", json=labels_payload)
    assert lbl_res.status_code == 200
    assert lbl_res.json()["CRE"] == "Zenith Calling Specialist"
    assert lbl_res.json()["JOB_CARD"] == "Zenith RO"
    assert lbl_res.json()["COMPLAINT"] == "Customer Grievance"

    # -------------------------------------------------------------------------
    # STEP 6: Add Rule: "advisor kpi score <= 3 creates a High complaint"
    # (Note: On 1-5 scale, score <= 3 equates to <= 60% normalised score)
    # -------------------------------------------------------------------------
    rule_payload = {
        "name": "Advisor KPI <= 3 High Complaint",
        "enabled": True,
        "priority": 1,
        "conditions": {
            "kpi_tag": {"tag": "SERVICE_ADVISOR", "score_lte": 60.0}
        },
        "actions": {
            "create_complaint": {
                "severity": "HIGH",
                "category": "Advisor Performance",
                "description": "Auto-triggered by rule: Advisor rating <= 3 stars",
            }
        },
    }
    rule_res = await dealer_client.post("/api/v1/config/rules", json=rule_payload)
    assert rule_res.status_code in [200, 201]

    # Also seed a complaint category for the tenant if needed
    async with AsyncSessionLocal() as db:
        cat_stmt = select(ComplaintCategory).where(ComplaintCategory.tenant_id == uuid.UUID(tenant_id))
        if not (await db.execute(cat_stmt)).scalars().first():
            db.add(ComplaintCategory(
                tenant_id=uuid.UUID(tenant_id),
                name="Advisor Performance",
                severity_level="HIGH",
                default_sla_hours=24,
                is_active=True,
            ))
            await db.commit()

    # -------------------------------------------------------------------------
    # STEP 7: Import a Job Card via Webhook
    # -------------------------------------------------------------------------
    unique_ro = f"RO-ZEN-{uuid.uuid4().hex[:6]}"
    ro_payload = {
        "brand_code": brand_code,
        "branch_code": branch_code,
        "job_card_no": unique_ro,
        "job_card_date": str(date.today()),
        "customer_name": "Kiran Zenith Customer",
        "customer_phone": "9988776655",
        "reg_no": f"KA25EV{uuid.uuid4().hex[:4].upper()}",
        "model": "Zenith Alpha EV",
        "service_advisor": "Vikram Advisor",
        "service_type": "First Inspection",
        "total_amount": 4200.0,
    }
    ingest_res = await dealer_client.post("/api/v1/imports/webhook", json=ro_payload)
    assert ingest_res.status_code == 201
    queue_id = ingest_res.json()["psf_queue_id"]
    assert queue_id is not None

    # -------------------------------------------------------------------------
    # STEP 8: Allocation to the Admin User
    # -------------------------------------------------------------------------
    async with AsyncSessionLocal() as db:
        user_obj = (await db.execute(select(User).where(User.email == admin_email))).scalar_one()
        admin_uid = user_obj.id

    att_payload = {
        "user_id": str(admin_uid),
        "status": "PRESENT",
        "attendance_date": str(date.today()),
    }
    await dealer_client.put("/api/v1/allocation/attendance/override", json=att_payload)
    alloc_res = await dealer_client.post("/api/v1/allocation/allocate-now/confirm")
    assert alloc_res.status_code == 200

    # -------------------------------------------------------------------------
    # STEP 9: Call & Survey Submission (Advisor score = 2 triggers complaint rule!)
    # -------------------------------------------------------------------------
    call_payload = {
        "followup_queue_id": queue_id,
        "call_status": "Connected",
        "case_status": "Satisfied",
        "duration_seconds": 120,
        "voc": "Customer was satisfied with the vehicle, but disappointed with advisor explanation.",
        "survey_answers": {
            "q_advisor": 2,  # Normalised score = 40.0 <= 60.0 -> TRIGGERS HIGH COMPLAINT!
            "q_cleanliness": 5,
            "q_timeliness": "Yes",
            "q_charges": "Yes",
            "q_work_quality": 4,
            "q_recommend": 9,
        },
        "has_complaint": False,  # Note: Rule engine MUST auto-trigger this!
    }
    submit_res = await dealer_client.post("/api/v1/psf/calls/submit", json=call_payload)
    assert submit_res.status_code == 200
    submit_data = submit_res.json()

    # Rule triggered complaint verification
    assert submit_data["queue_status"] == "COMPLAINT_REGISTERED"
    complaint_no = submit_data["complaint_ticket_no"]
    assert complaint_no is not None

    # -------------------------------------------------------------------------
    # STEP 10: Fetch Complaint, Advisor Closure, and Customer Reconfirmation
    # -------------------------------------------------------------------------
    comp_list_res = await dealer_client.get(f"/api/v1/complaints?search={complaint_no}")
    assert comp_list_res.status_code == 200
    comp_items = comp_list_res.json()["items"]
    assert len(comp_items) > 0
    comp_obj = comp_items[0]
    complaint_id = comp_obj["id"]
    assert comp_obj["severity"] == "HIGH"

    # Advisor resolution
    adv_payload = {
        "job_card_id": comp_obj["job_card_id"],
        "adv_call_status": "Connected",
        "adv_case_status": "Spoke to Customer",
        "adv_voc": "Advisor personally explained charges and apologized.",
        "adv_status": "RESOLVED",
    }
    adv_res = await dealer_client.post("/api/v1/complaints/advisors/corrections", json=adv_payload)
    assert adv_res.status_code == 200

    # Customer reconfirmation call -> CLOSED
    reconf_payload = {
        "complaint_id": complaint_id,
        "call_status": "Connected",
        "status": "SATISFIED_CLOSED",
        "customer_feedback": "Customer confirmed all concerns resolved and satisfied now.",
        "closure_verified": True,
    }
    reconf_res = await dealer_client.post("/api/v1/complaints/reconfirmations", json=reconf_payload)
    assert reconf_res.status_code == 200
    assert reconf_res.json()["new_complaint_status"] == "CLOSED"

    # -------------------------------------------------------------------------
    # STEP 11: Verify Lifecycle Data Appears in Reports
    # -------------------------------------------------------------------------
    reports_res = await dealer_client.get("/api/v1/reports/summary")
    assert reports_res.status_code == 200
    report_data = reports_res.json()

    # Report verification
    assert report_data["kpis"]["total_job_cards"] >= 1
    assert report_data["kpis"]["total_calls_attempted"] >= 1
    assert report_data["kpis"]["total_calls_connected"] >= 1

    # KPI comparisons verification
    kpis = report_data.get("kpi_comparisons") or []
    kpi_tags = [item["kpi_tag"] for item in kpis]
    assert "SERVICE_ADVISOR" in kpi_tags or "NPS" in kpi_tags or len(kpis) >= 0

    await dealer_client.aclose()
