"""
================================================================================
FILE PURPOSE: Customer Complaints & SLA Lifecycle Endpoints.
Provides endpoints for creating complaints from PSF calls, updating complaint statuses,
adding manager action notes, and tracking SLA resolution deadlines.

KEY RESPONSIBILITIES:
- Lists complaints with branch and status filters (`GET /complaints`).
- Creates a new customer complaint ticket (`POST /complaints`).
- Updates complaint status (OPEN, IN_PROGRESS, RESOLVED, CLOSED) (`PUT /complaints/{id}/status`).
- Adds manager action log entries to complaint timeline (`POST /complaints/{id}/actions`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: HTTP 403 Forbidden when closing complaint
  -> Cause: User lacks `complaint.close` permission (e.g. Service Advisor).
  -> What should you do: Only CRE Admin or Super Admin can mark complaints CLOSED.
================================================================================
"""
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_active_user, require, PermissionKey
from app.models.auth import User
from app.schemas.complaint_flow import (
    ComplaintListItem,
    ComplaintDetailResponse,
    ComplaintStatusUpdateRequest,
    ReconfirmationSubmitRequest,
    SubmitTnpsRequest,
    TnpsStatsResponse,
    AdvisorCallListItem,
    AdvisorCorrectionSubmitRequest,
)
from app.schemas.psf import FollowupQueueListItem
from app.services.complaint_flow_service import (
    list_complaints,
    get_complaint_detail,
    update_complaint_status,
    submit_reconfirmation,
    submit_tnps,
    get_tnps_statistics,
    list_advisor_tasks,
    submit_advisor_correction,
    list_happiness_queues,
)
from app.core.crypto import mask_phone, decrypt_phone

router = APIRouter(prefix="/complaints", tags=["Complaint Management, SLAs, Reconfirmations & TNPS"])


# -------------------------------------------------------------
# Complaint Lifecycle Endpoints
# -------------------------------------------------------------
@router.get("", response_model=Dict[str, Any])
async def get_complaints(
    status: Optional[str] = Query(None, description="OPEN | ASSIGNED | IN_PROGRESS | RESOLVED | CLOSED | REOPENED | ALL"),
    severity: Optional[str] = Query(None, description="HIGH | MEDIUM | LOW | ALL"),
    branch_id: Optional[uuid.UUID] = None,
    is_sla_breached: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require(PermissionKey.COMPLAINT_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Lists complaint tickets with dynamic SLA timers and urgency indicators."""
    items, total = await list_complaints(
        db=db,
        tenant_id=current_user.tenant_id,
        status_filter=status,
        severity_filter=severity,
        branch_id=branch_id,
        is_sla_breached=is_sla_breached,
        search=search,
        skip=skip,
        limit=limit,
        current_user=current_user,
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{complaint_id}", response_model=ComplaintDetailResponse)
async def get_complaint(
    complaint_id: uuid.UUID,
    current_user: User = Depends(require(PermissionKey.COMPLAINT_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves full complaint dossier with timeline audit events and reconfirmation records."""
    return await get_complaint_detail(db, current_user.tenant_id, complaint_id, current_user=current_user)


@router.put("/{complaint_id}/status", response_model=ComplaintDetailResponse)
async def change_complaint_status(
    complaint_id: uuid.UUID,
    payload: ComplaintStatusUpdateRequest,
    current_user: User = Depends(require(PermissionKey.COMPLAINT_CLOSE)),
    db: AsyncSession = Depends(get_db),
):
    """Updates complaint status, registers remarks, and schedules post-resolution reconfirmation calling."""
    return await update_complaint_status(db, current_user.tenant_id, current_user, complaint_id, payload)


@router.post("/reconfirmations")
async def post_reconfirmation_call(
    payload: ReconfirmationSubmitRequest,
    current_user: User = Depends(require(PermissionKey.RECONFIRMATION_MAKE)),
    db: AsyncSession = Depends(get_db),
):
    """Submits post-resolution customer reconfirmation: closes ticket if satisfied, reopens if unsatisfied."""
    return await submit_reconfirmation(db, current_user.tenant_id, current_user, payload)


# -------------------------------------------------------------
# TNPS Endpoints
# -------------------------------------------------------------
@router.post("/tnps/submit")
async def post_tnps_call(
    payload: SubmitTnpsRequest,
    current_user: User = Depends(require(PermissionKey.TNPS_MAKE)),
    db: AsyncSession = Depends(get_db),
):
    """Records brand and workshop recommend ratings and calculates NPS."""
    return await submit_tnps(db, current_user.tenant_id, current_user, payload)


@router.get("/tnps/stats", response_model=TnpsStatsResponse)
async def get_tnps_stats(
    brand_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(require(PermissionKey.REPORT_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Calculates Net Promoter Scores across promoters, passives, and detractors."""
    return await get_tnps_statistics(db, current_user.tenant_id, brand_id, branch_id)


# -------------------------------------------------------------
# Service Advisor Portal Endpoints
# -------------------------------------------------------------
@router.get("/advisors/tasks", response_model=List[AdvisorCallListItem])
async def get_advisor_tasks(
    status: Optional[str] = Query(None, description="PENDING | RESOLVED | ALL"),
    current_user: User = Depends(require(PermissionKey.ADVISOR_ACTION)),
    db: AsyncSession = Depends(get_db),
):
    """Lists customer dissatisfaction feedback allocated to service advisors for corrective action."""
    return await list_advisor_tasks(db, current_user.tenant_id, status_filter=status)


@router.post("/advisors/corrections")
async def post_advisor_correction(
    payload: AdvisorCorrectionSubmitRequest,
    current_user: User = Depends(require(PermissionKey.ADVISOR_ACTION)),
    db: AsyncSession = Depends(get_db),
):
    """Service Advisor submits corrective explanation and marks customer feedback addressed."""
    return await submit_advisor_correction(db, current_user.tenant_id, current_user, payload)


# -------------------------------------------------------------
# Happiness Calling (Hyundai Exclusive)
# -------------------------------------------------------------
@router.get("/happiness/queues")
async def get_happiness_queues(
    branch_id: Optional[uuid.UUID] = None,
    status: Optional[str] = Query(None, description="PENDING | CONTACTED | ALL"),
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require(PermissionKey.CALL_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves 15-day and 30-day post-delivery Happiness Calling queues.
    STRICT OEM COMPLIANCE: Exclusively returns Hyundai brand records.
    """
    queues, total = await list_happiness_queues(
        db=db,
        tenant_id=current_user.tenant_id,
        branch_id=branch_id,
        status_filter=status,
        search=search,
        skip=skip,
        limit=limit,
    )

    items = []
    for q in queues:
        jc = q.job_card
        cust = jc.customer if jc else None
        veh = jc.vehicle if jc else None
        brand = jc.brand if jc else None
        branch = jc.branch if jc else None

        raw_phone = None
        masked_phone = "+91 ********"
        if cust and cust.phone:
            try:
                decrypted = decrypt_phone(cust.phone)
                raw_phone = decrypted
                masked_phone = mask_phone(decrypted)
            except Exception:
                pass

        items.append(
            FollowupQueueListItem(
                id=q.id,
                job_card_id=q.job_card_id,
                job_card_no=jc.job_card_no if jc else "N/A",
                job_card_date=jc.job_card_date if jc else date.today(),
                total_amount=jc.total_amount if jc else 0,
                customer_id=cust.id if cust else uuid.uuid4(),
                customer_name=cust.name if cust else "Customer",
                customer_phone_masked=masked_phone,
                customer_phone_raw=raw_phone,
                vehicle_reg_no=veh.reg_no if veh else "N/A",
                vehicle_model=veh.model if veh else "Car",
                brand_id=brand.id if brand else uuid.uuid4(),
                brand_name=brand.name if brand else "Hyundai",
                brand_code=brand.code if brand else "HYUN",
                brand_color=brand.primary_color if brand else "#002C6C",
                branch_id=branch.id if branch else uuid.uuid4(),
                branch_name=branch.name if branch else "Workshop",
                service_advisor=jc.service_advisor_name if jc else None,
                queue_type=q.queue_type,
                status=q.status,
                attempts=q.attempts,
                last_attempt_at=q.last_attempt_at,
                due_at=q.due_at,
                assigned_to_id=q.assigned_to_id,
                assigned_to_name=q.assigned_to.full_name if q.assigned_to else None,
            )
        )

    return {"items": items, "total": total, "skip": skip, "limit": limit}

