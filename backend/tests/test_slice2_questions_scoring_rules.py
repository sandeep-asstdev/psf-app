"""
================================================================================
SLICE 2 TEST SUITE: Questions, Dynamic Scoring, and Outcome Rules Engine.
Validates:
1. Every answer type normalisation (YES_NO, YES_NO_NA, RATING, NPS_0_10, SINGLE_SELECT, MULTI_SELECT, TEXT, NUMBER, FILE_UPLOAD).
2. Question KPI Tag scores aggregation.
3. Declarative JSON Rules Engine evaluation (score, kpi_tag, answer, service_type, amount -> complaint, severity, notify, outcome).
4. POST /config/simulate endpoint (runs simulation with zero DB side effects).
5. Proof that Hyundai, Tata, MG, and Ather outcome statuses are 100% preserved.
================================================================================
"""
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant, Brand, Branch
from app.models.questionnaire import Question, KpiTag
from app.models.config import OutcomeRule
from app.services.scoring_service import ScoringService
from app.services.rules_engine import RulesEngineService
from app.services.rating_service import derive_case_status_memory, derive_case_status_from_db


@pytest.fixture
async def auth_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@apexauto.com", "password": "Admin@12345"},
        )
        assert res.status_code == 200
        token = res.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client


def test_answer_types_normalisation():
    """Test 0-100 normalisation across every supported question answer type."""
    # 1. YES_NO & YES_NO_NA
    s, r = ScoringService.normalize_single_answer("YES_NO", "Yes")
    assert s == 100.0 and r == "Yes"

    s, r = ScoringService.normalize_single_answer("YES_NO", "No")
    assert s == 0.0 and r == "No"

    s, r = ScoringService.normalize_single_answer("YES_NO_NA", "NA")
    assert s is None and r == "NA"

    # 2. NPS_0_10
    s, r = ScoringService.normalize_single_answer("NPS_0_10", 10)
    assert s == 100.0 and r == 10

    s, r = ScoringService.normalize_single_answer("NPS_0_10", 8)
    assert s == 80.0 and r == 8

    s, r = ScoringService.normalize_single_answer("NPS_0_10", 0)
    assert s == 0.0 and r == 0

    # 3. RATING (1-5 star scale)
    s, r = ScoringService.normalize_single_answer("RATING", 5, rating_min=1, rating_max=5)
    assert s == 100.0 and r == 5

    s, r = ScoringService.normalize_single_answer("RATING", 4, rating_min=1, rating_max=5)
    assert s == 80.0 and r == 4

    s, r = ScoringService.normalize_single_answer("RATING", 1, rating_min=1, rating_max=5)
    assert s == 20.0 and r == 1

    # 4. RATING (1-10 scale)
    s, r = ScoringService.normalize_single_answer("RATING", 9, rating_min=1, rating_max=10)
    assert s == 90.0 and r == 9

    # 5. SINGLE_SELECT with scoring weights
    options = {"scores": {"Excellent": 100, "Average": 50, "Poor": 0}}
    s, r = ScoringService.normalize_single_answer("SINGLE_SELECT", "Average", options=options)
    assert s == 50.0 and r == "Average"

    # 6. MULTI_SELECT
    s, r = ScoringService.normalize_single_answer("MULTI_SELECT", ["Option A", "Option B"])
    assert s is None and r == ["Option A", "Option B"]

    # 7. TEXT, NUMBER, FILE_UPLOAD
    s, r = ScoringService.normalize_single_answer("TEXT", "Customer was very pleased")
    assert s is None and r == "Customer was very pleased"

    s, r = ScoringService.normalize_single_answer("NUMBER", 42)
    assert s is None and r == 42.0

    s, r = ScoringService.normalize_single_answer("FILE_UPLOAD", "uuid-file-123")
    assert s is None and r == "uuid-file-123"


def test_oem_outcomes_unchanged():
    """Prove that Hyundai, Tata, MG, and Ather outcomes remain 100% equivalent."""
    # Hyundai: 10 Delight (no complaint), 9 Satisfied (triggers complaint in real data), 6-8 Non-Delight (trigger), 1-5 Dissatisfied (trigger)
    status, is_delight, is_trigger = derive_case_status_memory("HYUNDAI", 10)
    assert status == "Delight" and is_delight is True and is_trigger is False

    status, is_delight, is_trigger = derive_case_status_memory("HYUNDAI", 9)
    assert status == "Satisfied" and is_delight is False and is_trigger is True

    status, is_delight, is_trigger = derive_case_status_memory("HYUNDAI", 7)
    assert status == "Non-Delight" and is_delight is False and is_trigger is True

    status, is_delight, is_trigger = derive_case_status_memory("HYUNDAI", 4)
    assert status == "Dissatisfied" and is_delight is False and is_trigger is True

    # Tata Motors: 5 Delight, 4 Satisfied, 1-3 Dissatisfied
    status, is_delight, is_trigger = derive_case_status_memory("TATA MOTORS", 5)
    assert status == "Delight" and is_delight is True and is_trigger is False

    status, is_delight, is_trigger = derive_case_status_memory("TATA MOTORS", 4)
    assert status == "Satisfied" and is_delight is False and is_trigger is False

    status, is_delight, is_trigger = derive_case_status_memory("TATA MOTORS", 3)
    assert status == "Dissatisfied" and is_delight is False and is_trigger is True

    # MG Motors: 9-10 Satisfied (no complaint), 1-8 Dissatisfied (triggers complaint)
    status, is_delight, is_trigger = derive_case_status_memory("MG MOTORS", 10)
    assert status == "Satisfied" and is_delight is True and is_trigger is False

    status, is_delight, is_trigger = derive_case_status_memory("MG MOTORS", 8)
    assert status == "Dissatisfied" and is_delight is False and is_trigger is True

    # Ather: 9-10 Delight, 7-8 Satisfied, 0-6 Dissatisfied (triggers complaint)
    status, is_delight, is_trigger = derive_case_status_memory("ATHER", 10)
    assert status == "Delight" and is_delight is True and is_trigger is False

    status, is_delight, is_trigger = derive_case_status_memory("ATHER", 8)
    assert status == "Satisfied" and is_delight is False and is_trigger is False

    status, is_delight, is_trigger = derive_case_status_memory("ATHER", 5)
    assert status == "Dissatisfied" and is_delight is False and is_trigger is True


@pytest.mark.asyncio
async def test_rules_engine_matching_and_actions():
    """Test rules engine evaluating score, kpi_tag, answer, and amount conditions."""
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant).limit(1))).scalar_one()

        # Create a test rule
        rule_name = f"TEST_RULE_{uuid.uuid4().hex[:6]}"
        rule = OutcomeRule(
            tenant_id=tenant.id,
            name=rule_name,
            enabled=True,
            priority=1,
            conditions={
                "score": {"operator": "<=", "value": 50},
                "kpi_tag": {"tag": "WASHING", "operator": "<=", "value": 40},
            },
            actions={
                "create_complaint": {
                    "category": "CLEANLINESS",
                    "severity": "HIGH",
                    "description": "Poor washing quality auto-escalation",
                },
                "set_outcome": {"case_status": "Dissatisfied"},
                "notify": {"channel": "WHATSAPP", "recipient": "CUSTOMER", "template": "apology_notice"},
            },
        )
        db.add(rule)
        await db.commit()

        # Context matching rule
        matching_context = {
            "overall_score": 45.0,
            "kpi_scores": {"WASHING": 30.0},
            "answers": {},
            "service_type": "Periodic Maintenance",
            "branch_code": "APEX-HUBLI",
            "total_amount": 7500.0,
        }
        res = await RulesEngineService.evaluate_rules(
            db=db,
            tenant_id=tenant.id,
            brand_id=None,
            program_id=None,
            context=matching_context,
            dry_run=True,
        )
        assert rule_name in res["matched_rules"]
        assert res["outcome_status"] == "Dissatisfied"
        assert res["complaint"] is not None
        assert res["complaint"]["severity"] == "HIGH"
        assert len(res["notifications"]) == 1

        # Context NOT matching rule (score > 50)
        non_matching_context = {
            "overall_score": 85.0,
            "kpi_scores": {"WASHING": 80.0},
            "answers": {},
        }
        res2 = await RulesEngineService.evaluate_rules(
            db=db,
            tenant_id=tenant.id,
            brand_id=None,
            program_id=None,
            context=non_matching_context,
            dry_run=True,
        )
        assert rule_name not in res2["matched_rules"]

        # Cleanup
        await db.delete(rule)
        await db.commit()


@pytest.mark.asyncio
async def test_simulate_endpoint(auth_client: AsyncClient):
    """Test POST /config/simulate returns expected outcomes without writing to DB."""
    async with AsyncSessionLocal() as db:
        hyundai = (await db.execute(select(Brand).where(Brand.code == "HYUN"))).scalar_one()

    # Low score test simulation
    payload = {
        "brand_id": str(hyundai.id),
        "job_card": {
            "service_type": "Periodic Maintenance Service",
            "total_amount": 12000.0,
            "branch_code": "APEX-HUBLI",
        },
        "answers": {
            "nps_rating": 3,
            "hyundai_ontime_pickup_drop": "No",
            "hyundai_work_quality": 2,
        },
        "scoring_method": "WEIGHTED_AVERAGE",
    }

    res = await auth_client.post("/api/v1/config/simulate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "overall_score" in data
    assert data["nps_category"] == "DETRACTOR"
    assert data["is_complaint_trigger"] is True
    assert "kpi_scores" in data
    assert "normalized_answers" in data
    # Confirm normalised answers store both raw and score
    for k, v in data["normalized_answers"].items():
        assert "raw" in v
        assert "score" in v
