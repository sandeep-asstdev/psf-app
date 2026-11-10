"""
================================================================================
FILE PURPOSE: Call Allocation, Attendance & Notification WebSocket Endpoints.
Provides endpoints for viewing present CRE callers, setting manual attendance overrides,
configuring allocation rules, triggering mid-shift rebalances, undoing allocation runs,
and establishing live WebSocket connections for personal caller assignment notifications.

KEY RESPONSIBILITIES:
- Returns present CREs roster with pending call counts (`GET /allocation/present-cres`).
- Toggles manual CRE attendance ('Present' or 'On Leave') (`PUT /allocation/attendance/override`).
- Retrieves and updates allocation rules (`GET/PUT /allocation/rules`).
- Previews and executes manual Allocate Now (`POST /allocation/allocate-now`).
- Provides 15-minute undo capability (`POST /allocation/runs/{run_id}/undo`).
- Live real-time WebSocket for caller toast notifications (`WebSocket /allocation/ws/notifications/{token}`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: WebSocket disconnects or fails to connect
  -> Cause: Invalid or expired token passed in WebSocket URL.
  -> What should you do: Frontend should pass fresh access token in ws URL: `/allocation/ws/notifications/${token}`.
- Error: Undo fails with HTTP 400 'Undo window expired'
  -> Cause: Attempted to undo an allocation run after the 15-minute grace window.
  -> What should you do: Use bulk reassignment on the PSF table instead.
================================================================================
"""
import uuid
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.auth import User
from app.models import FollowupQueue, JobCard
from app.core.permissions import require, require_any, PermissionKey, get_user_effective_permissions
from app.schemas.allocation import (
    AttendanceOverrideRequest,
    AttendanceOverrideResponse,
    PresentCreItem,
    PresentCresResponse,
    AllocationRulesConfig,
    AllocationRunSummary,
    RebalancePreviewResponse,
    UnallocatedQueuesResponse,
    AllocateNowPreviewResponse,
)
from app.services.allocation_service import (
    get_present_cres,
    set_attendance_override,
    get_allocation_rules,
    update_allocation_rules,
    preview_rebalance,
    confirm_rebalance,
    undo_allocation_run,
    preview_allocate_now,
    confirm_allocate_now,
)
from app.services.auth_service import cleanup_stale_login_sessions

logger = logging.getLogger("psf.endpoints.allocation")

router = APIRouter(prefix="/allocation", tags=["Automatic Call Allocation"])


@router.get("/present-cres", response_model=PresentCresResponse)
async def list_present_cres(
    attendance_date: Optional[date] = Query(None, description="Date for presence check, defaults to today"),
    current_user: User = Depends(require_any(PermissionKey.CALL_ALLOCATE, PermissionKey.CALL_VIEW, PermissionKey.JOBCARD_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """
    List all eligible CREs for the dealership with their live presence, active logins,
    attendance overrides, and current pending call counts.
    """
    target_date = attendance_date or date.today()
    cres = await get_present_cres(db, current_user.tenant_id, target_date)

    items = [PresentCreItem(**c) for c in cres]
    total_present = sum(1 for c in cres if c["is_present"])
    total_absent = len(cres) - total_present

    return PresentCresResponse(
        attendance_date=target_date,
        total_eligible=len(cres),
        total_present=total_present,
        total_absent=total_absent,
        cres=items,
    )


@router.put("/attendance-override", response_model=AttendanceOverrideResponse)
async def set_cre_attendance_override(
    payload: AttendanceOverrideRequest,
    current_user: User = Depends(require(PermissionKey.CALL_ALLOCATE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a CRE as PRESENT, ABSENT, or ON_LEAVE manually.
    Manual marks take precedence over login session logs for that date.
    """
    override = await set_attendance_override(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=payload.user_id,
        status=payload.status,
        marked_by_id=current_user.id,
        attendance_date=payload.attendance_date,
        reason=payload.reason,
    )

    return AttendanceOverrideResponse(
        id=override.id,
        user_id=override.user_id,
        attendance_date=override.attendance_date,
        status=override.status,
        marked_by_id=override.marked_by_id,
        marked_by_name=current_user.full_name,
        reason=override.reason,
        created_at=override.created_at,
        updated_at=override.updated_at,
    )


@router.post("/rebalance/preview", response_model=RebalancePreviewResponse)
async def preview_call_rebalance(
    current_user: User = Depends(require(PermissionKey.CALL_ALLOCATE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Simulate rebalancing untouched calls across currently present CREs.
    Returns current vs proposed pending counts before any change is made.
    """
    preview = await preview_rebalance(db, current_user.tenant_id)
    return RebalancePreviewResponse(**preview)


@router.post("/rebalance/confirm", response_model=AllocationRunSummary)
async def confirm_call_rebalance(
    current_user: User = Depends(require(PermissionKey.CALL_ALLOCATE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute rebalance of untouched calls across currently present CREs.
    Only untouched calls (attempts == 0 and status == 'PENDING') are moved;
    calls already attempted or in progress never move.
    """
    run = await confirm_rebalance(db, current_user.tenant_id, current_user.id)
    return AllocationRunSummary(
        id=run.id,
        run_type=run.run_type,
        strategy=run.strategy,
        import_batch_id=run.import_batch_id,
        present_cre_count=run.present_cre_count,
        total_items=run.total_items,
        allocated_items=run.allocated_items,
        unallocated_items=run.unallocated_items,
        started_by_id=run.started_by_id,
        started_by_name=current_user.full_name,
        summary=run.summary or {},
        undone_at=run.undone_at,
        created_at=run.created_at,
        can_undo=True,
    )


@router.post("/runs/{run_id}/undo", response_model=Dict[str, Any])
async def undo_batch_allocation(
    run_id: uuid.UUID,
    current_user: User = Depends(require(PermissionKey.CALL_ALLOCATE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Undo an allocation run within the configurable safety window (default 15 minutes)
    if no call attempts have been made on those assigned items yet.
    """
    return await undo_allocation_run(db, current_user.tenant_id, run_id, current_user.id)


@router.get("/unallocated", response_model=UnallocatedQueuesResponse)
async def list_unallocated_calls(
    current_user: User = Depends(require_any(PermissionKey.CALL_ALLOCATE, PermissionKey.CALL_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """
    List all pending followup queue calls that currently have no assigned CRE.
    """
    eff = await get_user_effective_permissions(db, current_user)
    is_super = eff.get("is_super_admin", False)
    perms = eff.get("permissions", {})
    can_unmask = is_super or PermissionKey.CONTACT_UNMASK in perms

    stmt = (
        select(FollowupQueue)
        .options(
            selectinload(FollowupQueue.job_card).selectinload(JobCard.customer),
            selectinload(FollowupQueue.job_card).selectinload(JobCard.brand),
            selectinload(FollowupQueue.job_card).selectinload(JobCard.branch),
        )
        .where(
            FollowupQueue.tenant_id == current_user.tenant_id,
            FollowupQueue.assigned_to_id == None,
            FollowupQueue.status == "PENDING",
            FollowupQueue.is_deleted == False,
        )
        .order_by(FollowupQueue.due_at)
        .limit(200)
    )
    result = await db.execute(stmt)
    queues = result.scalars().all()

    items = []
    for q in queues:
        jc = q.job_card
        cust = jc.customer if jc else None
        phone = cust.phone if cust else ""
        if phone and not can_unmask and len(phone) >= 10:
            phone = phone[:2] + "******" + phone[-2:]

        items.append({
            "queue_id": str(q.id),
            "job_card_no": jc.job_card_no if jc else "N/A",
            "customer_name": cust.name if cust else "Unknown",
            "customer_phone": phone,
            "brand_name": jc.brand.name if jc and jc.brand else "N/A",
            "branch_name": jc.branch.name if jc and jc.branch else "N/A",
            "due_at": q.due_at.isoformat() if q.due_at else None,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        })

    return UnallocatedQueuesResponse(
        total_unallocated=len(items),
        items=items,
    )


@router.get("/rules", response_model=AllocationRulesConfig)
async def get_allocation_rules_config(
    current_user: User = Depends(require_any(PermissionKey.CONFIG_VIEW, PermissionKey.CALL_ALLOCATE, PermissionKey.ALLOCATION_CONFIGURE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the tenant's current allocation rules configuration.
    """
    rules = await get_allocation_rules(db, current_user.tenant_id)
    return AllocationRulesConfig(**rules)


@router.put("/rules", response_model=AllocationRulesConfig)
async def update_allocation_rules_config(
    payload: AllocationRulesConfig,
    current_user: User = Depends(require(PermissionKey.ALLOCATION_CONFIGURE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Update tenant allocation rules (strategy, pool mode, sticky customers, logout policy, weights).
    STRICTLY restricted to Super Admin (L1). CRE Admin (L2) cannot modify allocation rules.
    """
    updated = await update_allocation_rules(
        db=db,
        tenant_id=current_user.tenant_id,
        rules_payload=payload.model_dump(),
        updated_by_id=current_user.id,
    )
    return AllocationRulesConfig(**updated)


@router.post("/allocate-now/preview", response_model=AllocateNowPreviewResponse)
async def preview_allocate_now_endpoint(
    current_user: User = Depends(require(PermissionKey.CALL_ALLOCATE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Simulate manual "Allocate Now" of all currently unallocated calls
    across currently present CREs before executing.
    """
    preview = await preview_allocate_now(db, current_user.tenant_id)
    return AllocateNowPreviewResponse(**preview)


@router.post("/allocate-now/confirm", response_model=AllocationRunSummary)
async def confirm_allocate_now_endpoint(
    current_user: User = Depends(require(PermissionKey.CALL_ALLOCATE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute manual "Allocate Now" to immediately divide all unallocated calls
    equally among currently present CREs.
    """
    run = await confirm_allocate_now(db, current_user.tenant_id, current_user.id)
    return AllocationRunSummary(
        id=run.id,
        run_type=run.run_type,
        strategy=run.strategy,
        import_batch_id=run.import_batch_id,
        present_cre_count=run.present_cre_count,
        total_items=run.total_items,
        allocated_items=run.allocated_items,
        unallocated_items=run.unallocated_items,
        started_by_id=run.started_by_id,
        started_by_name=current_user.full_name,
        summary=run.summary or {},
        undone_at=run.undone_at,
        created_at=run.created_at,
        can_undo=True,
    )


@router.post("/cleanup-sessions")
async def cleanup_sessions_endpoint(
    before_date: Optional[date] = Query(None, description="Clean up open sessions strictly before this date (defaults to today)"),
    current_user: User = Depends(require_any(PermissionKey.CALL_ALLOCATE, PermissionKey.USER_EDIT)),
    db: AsyncSession = Depends(get_db),
):
    """
    Automatically terminate stale open login sessions from previous days (logout_at IS NULL).
    Sessions older than the start of today/target date are marked AUTO_LOGGED_OUT_EOD.
    """
    closed = await cleanup_stale_login_sessions(db, current_user.tenant_id, before_date)
    return {
        "status": "SUCCESS",
        "closed_sessions_count": closed,
        "message": f"Successfully closed {closed} abandoned login sessions from previous shifts.",
    }


@router.websocket("/ws/notifications/{token}")
async def websocket_notifications(
    websocket: WebSocket,
    token: str,
):
    """
    Live real-time WebSocket connection delivering personal caller notifications
    (e.g. 'N new calls assigned') to connected CREs via Redis pub/sub.
    """
    await websocket.accept()
    from app.core.security import decode_token
    from app.core.redis import get_redis
    import asyncio

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    r = await get_redis()
    pubsub = r.pubsub()
    channel = f"psf:notifications:user:{user_id}"
    await pubsub.subscribe(channel)

    receive_task = asyncio.create_task(websocket.receive_text())
    try:
        while True:
            # If client disconnects or sent anything, receive_task resolves or raises
            if receive_task.done():
                break

            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if msg and msg.get("data"):
                data = msg["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                await websocket.send_text(data)

            # Wait briefly allowing ASGI events and receive_task to be serviced
            done, _ = await asyncio.wait([receive_task], timeout=0.1)
            if done:
                break
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as e:
        logger.debug(f"Notification WebSocket error/disconnect: {e}")
    finally:
        receive_task.cancel()
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception:
            pass
