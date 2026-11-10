import pytest
import os
import uuid
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant, Brand, Branch
from app.models.service import JobCard, ImportBatch
from app.models.complaint import Complaint, ComplaintEvent
from app.models.followup import FollowupQueue, CallAttempt, SurveyResponse
from app.services.rating_service import derive_case_status_memory, derive_case_status_from_db


def test_rating_band_derivation_hyundai():
    """Unit tests for Hyundai rating scale derivation"""
    status, is_delight, is_trigger = derive_case_status_memory("HYUNDAI", 10)
    assert status == "Delight"
    assert is_delight is True
    assert is_trigger is False

    status, is_delight, is_trigger = derive_case_status_memory("HYUNDAI", 9)
    assert status == "Satisfied"
    assert is_delight is False
    assert is_trigger is True  # In real data, 9 triggers a complaint (WATSAPP RATING <=9)

    for score in (6, 7, 8):
        status, is_delight, is_trigger = derive_case_status_memory("HYUNDAI", score)
        assert status == "Non-Delight"
        assert is_delight is False
        assert is_trigger is True

    for score in (1, 2, 3, 4, 5):
        status, is_delight, is_trigger = derive_case_status_memory("HYUNDAI", score)
        assert status == "Dissatisfied"
        assert is_delight is False
        assert is_trigger is True


def test_rating_band_derivation_tata():
    """Unit tests for Tata Motors rating scale derivation (5-point scale)"""
    status, is_delight, is_trigger = derive_case_status_memory("TATA MOTORS", 5)
    assert status == "Delight"
    assert is_delight is True
    assert is_trigger is False

    status, is_delight, is_trigger = derive_case_status_memory("TATA MOTORS", 4)
    assert status == "Satisfied"
    assert is_delight is False
    assert is_trigger is False

    for score in (1, 2, 3):
        status, is_delight, is_trigger = derive_case_status_memory("TATA MOTORS", score)
        assert status == "Dissatisfied"
        assert is_delight is False
        assert is_trigger is True


def test_rating_band_derivation_mg():
    """Unit tests for MG Motors rating scale derivation (10-point scale)"""
    for score in (9, 10):
        status, is_delight, is_trigger = derive_case_status_memory("MG MOTORS", score)
        assert status == "Satisfied"
        assert is_delight is True
        assert is_trigger is False

    for score in range(1, 9):
        status, is_delight, is_trigger = derive_case_status_memory("MG MOTORS", score)
        assert status == "Dissatisfied"
        assert is_delight is False
        assert is_trigger is True


@pytest.mark.asyncio
async def test_db_rating_scale_bands():
    """Verify DB-driven rating scale band querying for Hyundai, Tata, and MG"""
    async with AsyncSessionLocal() as db:
        t_stmt = select(Tenant).where(Tenant.slug == "apex-auto")
        tenant = (await db.execute(t_stmt)).scalar_one_or_none()
        assert tenant is not None

        # Hyundai
        h_brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant.id, Brand.code == "HYUN"))).scalar_one_or_none()
        assert h_brand is not None

        status, delight, trig = await derive_case_status_from_db(db, tenant.id, h_brand.id, 10)
        assert status == "Delight" and delight is True and trig is False

        status, delight, trig = await derive_case_status_from_db(db, tenant.id, h_brand.id, 9)
        assert status == "Satisfied" and delight is False and trig is True

        status, delight, trig = await derive_case_status_from_db(db, tenant.id, h_brand.id, 7)
        assert status == "Non-Delight" and trig is True

        status, delight, trig = await derive_case_status_from_db(db, tenant.id, h_brand.id, 3)
        assert status == "Dissatisfied" and trig is True


@pytest.mark.asyncio
async def test_imported_legacy_data_assertions():
    """
    Asserts requirements on the 29 imported rows:
    - 29 Job Cards
    - 28 Hubli + 1 Gadag
    - 6 Complaints with closure
    - 1 No Response row with 5 attempts / 0 contacted
    - 0 duplicate job cards
    - Survey answers normalized (Yes/No, ratings)
    """
    async with AsyncSessionLocal() as db:
        t_stmt = select(Tenant).where(Tenant.slug == "apex-auto")
        tenant = (await db.execute(t_stmt)).scalar_one_or_none()
        assert tenant is not None

        # 1. Assert exactly 29 Job Cards exist for this batch
        jc_stmt = (
            select(JobCard)
            .join(Branch, Branch.id == JobCard.branch_id)
            .where(JobCard.tenant_id == tenant.id, JobCard.job_card_no.like("S%"))
        )
        job_cards = (await db.execute(jc_stmt)).scalars().all()
        assert len(job_cards) == 29, f"Expected 29 job cards, got {len(job_cards)}"

        # 2. Assert 28 Hubli + 1 Gadag
        hubli_count = sum(1 for jc in job_cards if jc.job_card_no.startswith("S8211"))
        gadag_count = sum(1 for jc in job_cards if jc.job_card_no.startswith("S8827"))
        assert hubli_count == 28, f"Expected 28 Hubli job cards, got {hubli_count}"
        assert gadag_count == 1, f"Expected 1 Gadag job card, got {gadag_count}"

        # 3. Assert 0 duplicate job card numbers
        jc_numbers = [jc.job_card_no for jc in job_cards]
        assert len(jc_numbers) == len(set(jc_numbers)), "Found duplicate job card numbers!"

        # 4. Assert 6 Complaints with closure
        cmp_stmt = (
            select(Complaint)
            .where(Complaint.tenant_id == tenant.id, Complaint.complaint_no.like("CMP-S%"))
        )
        complaints = (await db.execute(cmp_stmt)).scalars().all()
        assert len(complaints) == 6, f"Expected 6 complaints, got {len(complaints)}"
        for cmp in complaints:
            assert cmp.status == "Closed in Time"
            assert cmp.resolution_remarks is not None and len(cmp.resolution_remarks.strip()) > 0
            assert cmp.closed_by_id is not None
            assert cmp.closed_at is not None

        # 5. Assert 1 No Response row with 5 attempts / 0 contacted
        nr_jc_stmt = select(JobCard).where(JobCard.job_card_no == "S8211_R202600449")
        nr_jc = (await db.execute(nr_jc_stmt)).scalar_one_or_none()
        assert nr_jc is not None, "Job card S8211_R202600449 not found"

        queue_stmt = select(FollowupQueue).where(FollowupQueue.job_card_id == nr_jc.id, FollowupQueue.queue_type == "PSF")
        queue = (await db.execute(queue_stmt)).scalar_one_or_none()
        assert queue is not None
        assert queue.attempts == 5, f"Expected 5 attempts, got {queue.attempts}"
        assert queue.contacted_count == 0, f"Expected 0 contacted, got {queue.contacted_count}"
        assert queue.status == "NOT_CONTACTED"

        att_stmt = select(CallAttempt).where(CallAttempt.followup_queue_id == queue.id)
        attempts = (await db.execute(att_stmt)).scalars().all()
        assert len(attempts) == 5, f"Expected 5 CallAttempt records, got {len(attempts)}"
        assert attempts[-1].case_status == "No Response"

        # 6. Assert Normalized Survey Answers
        sr_stmt = (
            select(SurveyResponse)
            .join(JobCard, JobCard.id == SurveyResponse.job_card_id)
            .where(JobCard.job_card_no.like("S%"), JobCard.job_card_no != "S8211_R202600449")
        )
        survey_responses = (await db.execute(sr_stmt)).scalars().all()
        assert len(survey_responses) > 0

        for sr in survey_responses:
            for q_key, answer in sr.answers.items():
                if isinstance(answer, str):
                    # Check normalization: no raw lowercase "yes" or all-caps "YES"
                    assert answer in ("Yes", "No", "Not Aware") or not answer.lower() in ("yes", "no"), \
                        f"Unnormalized answer found: {answer} for key {q_key}"
                elif isinstance(answer, int):
                    assert 1 <= answer <= 10, f"Rating outside 1-10: {answer}"
