"""
================================================================================
FILE PURPOSE: Customer Survey & Questionnaire Management Service.
Loads dynamic survey questions for specific OEM brands (Hyundai, Tata, MG),
evaluates customer survey responses, and computes CSAT and NPS scores.

KEY RESPONSIBILITIES:
- Fetches active questionnaire templates for a brand and queue type (`get_questionnaire_for_queue`).
- Calculates CSAT percentage score from question ratings (`calculate_csat`).
- Classifies NPS rating into Promoter (9-10), Passive (7-8), or Detractor (1-6) (`calculate_nps`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Survey questions not showing in call console dialer
  -> Cause: No active questionnaire found for the vehicle's brand.
  -> What should you do: Run `docker exec psf_api python -m app.db.seed_questionnaires` to seed brand survey templates.
================================================================================
"""
import uuid
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.questionnaire import Questionnaire, Question
from app.models.tenant import Brand
from app.schemas.questionnaire import (
    QuestionnaireCreate,
    QuestionnaireUpdate,
    QuestionCreate,
    QuestionUpdate,
)


async def list_questionnaires(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    brand_id: Optional[uuid.UUID] = None,
    type_filter: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[Tuple[Questionnaire, int]]:
    """List questionnaires with question counts."""
    filters = [Questionnaire.tenant_id == tenant_id, Questionnaire.is_deleted == False]
    if brand_id:
        filters.append(Questionnaire.brand_id == brand_id)
    if type_filter:
        filters.append(Questionnaire.type == type_filter.upper())
    if is_active is not None:
        filters.append(Questionnaire.is_active == is_active)

    stmt = (
        select(Questionnaire, func.count(Question.id).label("questions_count"))
        .outerjoin(
            Question,
            and_(Question.questionnaire_id == Questionnaire.id, Question.is_deleted == False),
        )
        .options(selectinload(Questionnaire.brand))
        .where(and_(*filters))
        .group_by(Questionnaire.id)
        .order_by(Questionnaire.type, Questionnaire.version.desc())
    )
    result = await db.execute(stmt)
    return result.all()


async def get_questionnaire_by_id(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    questionnaire_id: uuid.UUID,
) -> Optional[Questionnaire]:
    stmt = (
        select(Questionnaire)
        .options(
            selectinload(Questionnaire.brand),
            selectinload(Questionnaire.questions),
        )
        .where(
            Questionnaire.id == questionnaire_id,
            Questionnaire.tenant_id == tenant_id,
            Questionnaire.is_deleted == False,
        )
    )
    result = await db.execute(stmt)
    q = result.scalar_one_or_none()
    if q and q.questions:
        q.questions = [item for item in q.questions if not item.is_deleted]
        q.questions.sort(key=lambda x: x.display_order)
    return q


async def create_questionnaire(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    payload: QuestionnaireCreate,
) -> Questionnaire:
    # 1. Fetch brand to validate capabilities
    brand_stmt = select(Brand).where(Brand.id == payload.brand_id, Brand.tenant_id == tenant_id)
    brand = (await db.execute(brand_stmt)).scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")

    # 2. DOMAIN ENFORCEMENT: Happiness calling is ONLY for Hyundai
    q_type = payload.type.upper()
    is_hyundai = "HYUNDAI" in brand.name.upper() or brand.code.upper() in ["HYUN", "HYUNDAI"]
    if q_type == "HAPPINESS" and not is_hyundai:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Happiness Calling questionnaires are exclusively permitted for Hyundai brands per OEM compliance.",
        )

    # 3. Determine next version
    v_stmt = (
        select(func.max(Questionnaire.version))
        .where(
            Questionnaire.tenant_id == tenant_id,
            Questionnaire.brand_id == payload.brand_id,
            Questionnaire.type == q_type,
        )
    )
    max_v = (await db.execute(v_stmt)).scalar() or 0
    next_version = max_v + 1

    questionnaire = Questionnaire(
        tenant_id=tenant_id,
        brand_id=payload.brand_id,
        type=q_type,
        title=payload.title.strip(),
        version=next_version,
        is_active=payload.is_active,
    )
    db.add(questionnaire)
    await db.commit()
    await db.refresh(questionnaire)
    return questionnaire


async def create_new_version(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    questionnaire_id: uuid.UUID,
) -> Questionnaire:
    """Clone an existing questionnaire and its questions into version N+1."""
    parent = await get_questionnaire_by_id(db, tenant_id, questionnaire_id)
    if not parent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Questionnaire not found")

    new_q = Questionnaire(
        tenant_id=tenant_id,
        brand_id=parent.brand_id,
        type=parent.type,
        title=f"{parent.title} (v{parent.version + 1})",
        version=parent.version + 1,
        is_active=True,
    )
    db.add(new_q)
    await db.flush()

    # Clone active questions
    for q in parent.questions or []:
        cloned_q = Question(
            tenant_id=tenant_id,
            questionnaire_id=new_q.id,
            key=q.key,
            label=q.label,
            type=q.type,
            section=q.section,
            options=q.options,
            show_if=q.show_if,
            weight=q.weight,
            display_order=q.display_order,
            is_required=q.is_required,
        )
        db.add(cloned_q)

    await db.commit()
    await db.refresh(new_q)
    return await get_questionnaire_by_id(db, tenant_id, new_q.id)


async def add_question(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    questionnaire_id: uuid.UUID,
    payload: QuestionCreate,
) -> Question:
    questionnaire = await get_questionnaire_by_id(db, tenant_id, questionnaire_id)
    if not questionnaire:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Questionnaire not found")

    # Check key duplicate in questionnaire
    for q in questionnaire.questions or []:
        if q.key == payload.key.strip():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Question with key '{payload.key}' already exists in this questionnaire",
            )

    question = Question(
        tenant_id=tenant_id,
        questionnaire_id=questionnaire_id,
        key=payload.key.strip(),
        label=payload.label.strip(),
        type=payload.type.strip().lower(),
        section=payload.section.strip(),
        options=payload.options,
        show_if=payload.show_if,
        weight=payload.weight,
        display_order=payload.display_order or (len(questionnaire.questions) + 1),
        is_required=payload.is_required,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return question


async def update_question(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    questionnaire_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: QuestionUpdate,
) -> Question:
    stmt = select(Question).where(
        Question.id == question_id,
        Question.questionnaire_id == questionnaire_id,
        Question.tenant_id == tenant_id,
        Question.is_deleted == False,
    )
    question = (await db.execute(stmt)).scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(question, field, val)

    await db.commit()
    await db.refresh(question)
    return question


async def delete_question(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    questionnaire_id: uuid.UUID,
    question_id: uuid.UUID,
) -> None:
    stmt = select(Question).where(
        Question.id == question_id,
        Question.questionnaire_id == questionnaire_id,
        Question.tenant_id == tenant_id,
        Question.is_deleted == False,
    )
    question = (await db.execute(stmt)).scalar_one_or_none()
    if question:
        question.is_deleted = True
        await db.commit()


async def reorder_questions(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    questionnaire_id: uuid.UUID,
    question_ids: List[uuid.UUID],
) -> None:
    for idx, q_id in enumerate(question_ids, start=1):
        stmt = select(Question).where(
            Question.id == q_id,
            Question.questionnaire_id == questionnaire_id,
            Question.tenant_id == tenant_id,
        )
        q = (await db.execute(stmt)).scalar_one_or_none()
        if q:
            q.display_order = idx
    await db.commit()


def calculate_survey_score(
    answers: Dict[str, Any],
    questions: List[Question],
) -> Tuple[Optional[Decimal], Optional[int], Optional[str]]:
    """
    Auto-aggregate CSAT score (0 - 100%) and NPS score (0 - 10) + NPS category:
    - PROMOTER: 9 - 10
    - PASSIVE: 7 - 8
    - DETRACTOR: 0 - 6
    """
    total_weighted_score = Decimal("0.0")
    total_weight = Decimal("0.0")
    nps_rating: Optional[int] = None

    q_map = {q.key: q for q in questions}

    for key, val in answers.items():
        q = q_map.get(key)
        if not q or val is None:
            continue

        weight = q.weight or Decimal("1.0")

        if q.type == "nps_10":
            try:
                score_int = int(val)
                nps_rating = max(0, min(10, score_int))
                # Normalize 0-10 to 0-100%
                total_weighted_score += Decimal(str(nps_rating * 10)) * weight
                total_weight += weight
            except (ValueError, TypeError):
                pass

        elif q.type == "rating_5":
            try:
                score_int = int(val)
                # 1 to 5 stars normalized to percentage (1=20%, 5=100%)
                pct = Decimal(str(score_int * 20))
                total_weighted_score += pct * weight
                total_weight += weight
            except (ValueError, TypeError):
                pass

        elif q.type in ["yes_no", "yes_no_na"]:
            if str(val).lower() in ["true", "yes", "1"]:
                total_weighted_score += Decimal("100.0") * weight
                total_weight += weight
            elif str(val).lower() in ["false", "no", "0"]:
                total_weighted_score += Decimal("0.0") * weight
                total_weight += weight

    csat: Optional[Decimal] = None
    if total_weight > Decimal("0.0"):
        csat = round(total_weighted_score / total_weight, 2)

    nps_category: Optional[str] = None
    if nps_rating is not None:
        if nps_rating >= 9:
            nps_category = "PROMOTER"
        elif nps_rating >= 7:
            nps_category = "PASSIVE"
        else:
            nps_category = "DETRACTOR"

    return csat, nps_rating, nps_category
