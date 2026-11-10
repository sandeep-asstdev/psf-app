"""
================================================================================
FILE PURPOSE: Dynamic Survey Questionnaire Endpoints.
Provides endpoints for retrieving brand survey questions, submitting customer survey responses,
and calculating CSAT / NPS scores.

KEY RESPONSIBILITIES:
- Returns survey questions for a specific brand and queue (`GET /questionnaires`).
- Records survey answer ratings from Call Console (`POST /questionnaires/submit`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Empty questions array returned
  -> Cause: No active survey template seeded for the requested brand.
  -> What should you do: Run `docker exec psf_api python -m app.db.seed_questionnaires` to seed survey templates.
================================================================================
"""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_active_user, require, PermissionKey
from app.models.auth import User
from app.schemas.questionnaire import (
    QuestionnaireCreate,
    QuestionnaireUpdate,
    QuestionnaireDetailResponse,
    QuestionnaireListItem,
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    ReorderQuestionsRequest,
)
from app.services.questionnaire_service import (
    list_questionnaires,
    get_questionnaire_by_id,
    create_questionnaire,
    create_new_version,
    add_question,
    update_question,
    delete_question,
    reorder_questions,
)

router = APIRouter(prefix="/questionnaires", tags=["Dynamic Questionnaire Builder"])


@router.get("", response_model=List[QuestionnaireListItem])
async def get_questionnaires(
    brand_id: Optional[uuid.UUID] = None,
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all versioned questionnaires with question counts."""
    results = await list_questionnaires(
        db=db,
        tenant_id=current_user.tenant_id,
        brand_id=brand_id,
        type_filter=type,
        is_active=is_active,
    )

    items = []
    for q, count in results:
        items.append(
            QuestionnaireListItem(
                id=q.id,
                tenant_id=q.tenant_id,
                brand_id=q.brand_id,
                brand_name=q.brand.name if q.brand else None,
                brand_code=q.brand.code if q.brand else None,
                type=q.type,
                title=q.title,
                version=q.version,
                questions_count=count,
                is_active=q.is_active,
                created_at=q.created_at,
                updated_at=q.updated_at,
            )
        )
    return items


@router.post("", response_model=QuestionnaireDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_new_questionnaire(
    payload: QuestionnaireCreate,
    current_user: User = Depends(require(PermissionKey.QUESTIONNAIRE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new dynamic questionnaire.
    Note: HAPPINESS questionnaires are strictly permitted only for Hyundai brands.
    """
    q = await create_questionnaire(db=db, tenant_id=current_user.tenant_id, payload=payload)
    return await get_questionnaire_by_id(db, current_user.tenant_id, q.id)


@router.get("/{questionnaire_id}", response_model=QuestionnaireDetailResponse)
async def get_questionnaire(
    questionnaire_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get complete questionnaire schema with ordered questions and conditional logic rules."""
    q = await get_questionnaire_by_id(db, current_user.tenant_id, questionnaire_id)
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Questionnaire not found")

    return QuestionnaireDetailResponse(
        id=q.id,
        tenant_id=q.tenant_id,
        brand_id=q.brand_id,
        brand_name=q.brand.name if q.brand else None,
        brand_code=q.brand.code if q.brand else None,
        type=q.type,
        title=q.title,
        version=q.version,
        is_active=q.is_active,
        questions=[
            QuestionResponse(
                id=item.id,
                tenant_id=item.tenant_id,
                questionnaire_id=item.questionnaire_id,
                key=item.key,
                label=item.label,
                type=item.type,
                section=item.section,
                options=item.options,
                show_if=item.show_if,
                weight=item.weight,
                display_order=item.display_order,
                is_required=item.is_required,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in (q.questions or [])
        ],
        created_at=q.created_at,
        updated_at=q.updated_at,
    )


@router.post("/{questionnaire_id}/new-version", response_model=QuestionnaireDetailResponse)
async def bump_version(
    questionnaire_id: uuid.UUID,
    current_user: User = Depends(require(PermissionKey.QUESTIONNAIRE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Clone questionnaire to version N+1 preserving existing historical responses on version N."""
    cloned = await create_new_version(db, current_user.tenant_id, questionnaire_id)
    return cloned


@router.post("/{questionnaire_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def add_new_question(
    questionnaire_id: uuid.UUID,
    payload: QuestionCreate,
    current_user: User = Depends(require(PermissionKey.QUESTIONNAIRE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Add a question to the questionnaire."""
    question = await add_question(db, current_user.tenant_id, questionnaire_id, payload)
    return question


@router.put("/{questionnaire_id}/questions/{question_id}", response_model=QuestionResponse)
async def edit_question(
    questionnaire_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: QuestionUpdate,
    current_user: User = Depends(require(PermissionKey.QUESTIONNAIRE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Update question label, options, conditional logic, weight, or section."""
    return await update_question(db, current_user.tenant_id, questionnaire_id, question_id, payload)


@router.delete("/{questionnaire_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_question(
    questionnaire_id: uuid.UUID,
    question_id: uuid.UUID,
    current_user: User = Depends(require(PermissionKey.QUESTIONNAIRE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a question from the active template."""
    await delete_question(db, current_user.tenant_id, questionnaire_id, question_id)
    return None


@router.post("/{questionnaire_id}/reorder")
async def update_question_order(
    questionnaire_id: uuid.UUID,
    payload: ReorderQuestionsRequest,
    current_user: User = Depends(require(PermissionKey.QUESTIONNAIRE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Reorder display order of questions in the questionnaire."""
    await reorder_questions(db, current_user.tenant_id, questionnaire_id, payload.question_ids)
    return {"message": "Questions reordered successfully"}

