"""
================================================================================
FILE PURPOSE: PSF Calling Workspace, Dashboard & Call Console Endpoints.
Powers the main calling interface: provides dashboard KPI stats, lists calling line items,
delivers complete customer dossier to the calling dialer modal, and records submitted call outcomes.

KEY RESPONSIBILITIES:
- Returns dashboard KPI counters (`GET /psf/dashboard`).
- Returns paginated calling line items with CRE role scoping (`GET /psf/queues`).
- Delivers full dossier to Call Console modal (`GET /psf/console/{queue_id}`).
- Saves completed call log, updating customer sentiment and queue status (`POST /psf/calls/submit`).
- Bulk reassigns calling queue line items (`POST /psf/queues/bulk-assign`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Dashboard shows 0 or table says 'Loading line items...'
  -> Cause: Network timeout or API error.
  -> What should you do: Check browser DevTools Network tab. Verify that /psf/dashboard returns HTTP 200.
================================================================================
"""
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_active_user, require, PermissionKey
from app.models.auth import User
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.followup import CallAttempt, FollowupQueue
from app.schemas.psf import (
    PsfDashboardStats,
    FollowupQueueListItem,
    CallConsoleDetails,
    SubmitCallRequest,
    SubmitCallResponse,
    BulkAssignRequest,
    CallAttemptResponse,
)
from app.services.psf_service import (
    get_dashboard_stats,
    list_followup_queues,
    get_call_console_data,
    submit_call_log,
    bulk_assign_queues,
)

router = APIRouter(prefix="/psf", tags=["PSF Calling Workspace & Call Console"])


@router.get("/dashboard", response_model=PsfDashboardStats)
async def get_psf_dashboard_stats(
    brand_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
    cre_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(require(PermissionKey.CALL_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves high-level follow-up counters, connect rates, and grouped widget summaries."""
    from app.core.permissions import get_user_effective_permissions, DataScope
    eff = await get_user_effective_permissions(db, current_user)
    scope = eff.get("permissions", {}).get(PermissionKey.CALL_VIEW, DataScope.ALL)
    user_role_name = eff.get("role_name", "").upper()

    if not eff.get("is_super_admin", False) and (scope == DataScope.OWN or user_role_name in ["CRE", "BRANCH_CRE"]):
        # A CRE only sees their own assigned calls on their dashboard
        cre_id = current_user.id

    return await get_dashboard_stats(
        db=db,
        tenant_id=current_user.tenant_id,
        brand_id=brand_id,
        branch_id=branch_id,
        cre_id=cre_id,
    )


@router.get("/queues")
async def get_calling_queues(
    queue_type: str = Query("PSF", description="PSF | TNPS | HAPPINESS | RECONFIRMATION | ALL"),
    status: Optional[str] = Query(None, description="PENDING | NOT_CONTACTED | CALLBACK_REQUESTED | CONTACTED | ALL"),
    brand_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
    assigned_to_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require(PermissionKey.CALL_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Lists drill-down follow-up queue records with customer snapshot & call history indicators."""
    items, total = await list_followup_queues(
        db=db,
        tenant_id=current_user.tenant_id,
        queue_type=queue_type,
        status_filter=status,
        brand_id=brand_id,
        branch_id=branch_id,
        assigned_to_id=assigned_to_id,
        search=search,
        skip=skip,
        limit=limit,
        current_user=current_user,
    )
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/console/{queue_id}", response_model=CallConsoleDetails)
async def get_call_console(
    queue_id: uuid.UUID,
    current_user: User = Depends(require(PermissionKey.CALL_MAKE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches full customer dossier, vehicle service snapshot, call history,
    brand-specific dynamic questionnaire, and the next queue item for 'Save & Next'.
    """
    return await get_call_console_data(
        db=db,
        tenant_id=current_user.tenant_id,
        queue_id=queue_id,
        current_user=current_user,
    )


@router.post("/calls/submit", response_model=SubmitCallResponse)
async def submit_call(
    payload: SubmitCallRequest,
    current_user: User = Depends(require(PermissionKey.CALL_MAKE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits completed follow-up call, scores answers, triggers automated SLA complaints,
    and returns next candidate in caller queue.
    """
    return await submit_call_log(
        db=db,
        tenant_id=current_user.tenant_id,
        current_user=current_user,
        payload=payload,
    )


@router.post("/queues/bulk-assign")
async def bulk_assign(
    payload: BulkAssignRequest,
    current_user: User = Depends(require(PermissionKey.CALL_ALLOCATE)),
    db: AsyncSession = Depends(get_db),
):
    """Bulk allocates selected calling queue records to a designated CRE caller."""
    updated_count = await bulk_assign_queues(
        db=db,
        tenant_id=current_user.tenant_id,
        queue_ids=payload.queue_ids,
        assigned_to_id=payload.assigned_to_id,
    )
    return {"message": f"Successfully assigned {updated_count} records", "count": updated_count}


# -------------------------------------------------------------
# Call Attempt History Endpoints
# -------------------------------------------------------------
@router.get("/queues/{queue_id}/attempts", response_model=List[CallAttemptResponse])
async def get_queue_call_attempts(
    queue_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full per-attempt call logs for a specific calling queue."""
    stmt = (
        select(CallAttempt)
        .options(selectinload(CallAttempt.called_by))
        .where(
            CallAttempt.tenant_id == current_user.tenant_id,
            CallAttempt.followup_queue_id == queue_id,
        )
        .order_by(CallAttempt.attempt_number)
    )
    attempts_res = await db.execute(stmt)
    attempts = attempts_res.scalars().all()

    items = []
    for att in attempts:
        caller_name = att.called_by.full_name if att.called_by else None
        items.append(
            CallAttemptResponse(
                id=att.id,
                followup_queue_id=att.followup_queue_id,
                attempt_number=att.attempt_number,
                call_status=att.call_status,
                case_status=att.case_status,
                voc=att.voc,
                rating=att.rating,
                called_by_id=att.called_by_id,
                called_by_name=caller_name,
                called_at=att.called_at,
                duration_seconds=att.duration_seconds,
            )
        )
    return items


@router.get("/job-cards/{job_card_id}/attempts", response_model=List[CallAttemptResponse])
async def get_job_card_call_attempts(
    job_card_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full per-attempt call logs across queues for a given job card."""
    stmt = (
        select(CallAttempt)
        .options(selectinload(CallAttempt.called_by))
        .join(FollowupQueue, FollowupQueue.id == CallAttempt.followup_queue_id)
        .where(
            CallAttempt.tenant_id == current_user.tenant_id,
            FollowupQueue.job_card_id == job_card_id,
        )
        .order_by(CallAttempt.called_at, CallAttempt.attempt_number)
    )
    attempts_res = await db.execute(stmt)
    attempts = attempts_res.scalars().all()

    items = []
    for att in attempts:
        caller_name = att.called_by.full_name if att.called_by else None
        items.append(
            CallAttemptResponse(
                id=att.id,
                followup_queue_id=att.followup_queue_id,
                attempt_number=att.attempt_number,
                call_status=att.call_status,
                case_status=att.case_status,
                voc=att.voc,
                rating=att.rating,
                called_by_id=att.called_by_id,
                called_by_name=caller_name,
                called_at=att.called_at,
                duration_seconds=att.duration_seconds,
            )
        )
    return items


