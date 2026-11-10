import pytest
import uuid
from decimal import Decimal
from app.services.questionnaire_service import calculate_survey_score
from app.models.questionnaire import Question


def test_calculate_survey_score_csat_and_nps():
    """Verify that CSAT (0-100%) and NPS categorization work as required by OEM specs."""
    # Mock questions
    q_star = Question(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        questionnaire_id=uuid.uuid4(),
        key="hyundai_courtesy",
        label="Courtesy of advisor",
        type="rating_5",
        weight=Decimal("1.0"),
    )
    q_nps = Question(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        questionnaire_id=uuid.uuid4(),
        key="hyundai_recommend",
        label="Recommend dealer to friend",
        type="nps_10",
        weight=Decimal("2.0"),
    )
    q_yes_no = Question(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        questionnaire_id=uuid.uuid4(),
        key="hyundai_clean",
        label="Was car cleaned properly?",
        type="yes_no",
        weight=Decimal("1.0"),
    )

    questions = [q_star, q_nps, q_yes_no]

    # Test Case 1: Excellent Experience (Promoter)
    # 5 stars = 100% * 1.0 weight = 100
    # 10 NPS = 100% * 2.0 weight = 200
    # Yes = 100% * 1.0 weight = 100
    # Total = 400 / 4.0 weight = 100%
    answers_promoter = {
        "hyundai_courtesy": 5,
        "hyundai_recommend": 10,
        "hyundai_clean": "yes",
    }
    csat, nps, category = calculate_survey_score(answers_promoter, questions)
    assert csat == Decimal("100.00")
    assert nps == 10
    assert category == "PROMOTER"

    # Test Case 2: Poor Experience (Detractor)
    # 2 stars = 40% * 1.0 = 40
    # 4 NPS = 40% * 2.0 = 80
    # No = 0% * 1.0 = 0
    # Total = 120 / 4.0 = 30%
    answers_detractor = {
        "hyundai_courtesy": 2,
        "hyundai_recommend": 4,
        "hyundai_clean": "no",
    }
    csat, nps, category = calculate_survey_score(answers_detractor, questions)
    assert csat == Decimal("30.00")
    assert nps == 4
    assert category == "DETRACTOR"

    # Test Case 3: Passive Customer
    answers_passive = {
        "hyundai_courtesy": 4,
        "hyundai_recommend": 8,
        "hyundai_clean": "yes",
    }
    csat, nps, category = calculate_survey_score(answers_passive, questions)
    assert nps == 8
    assert category == "PASSIVE"

