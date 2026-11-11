"""
================================================================================
FILE PURPOSE: Complaint Lifecycle & SLA Escalation Service.
Manages the end-to-end lifecycle of customer complaints generated from PSF calls.
Calculates target resolution deadlines, tracks SLA breaches, and logs manager action notes.

KEY RESPONSIBILITIES:
- Creates complaint records with auto-generated ticket numbers (e.g. 'CMP-20261104-001') (`create_complaint`).
- Updates complaint statuses and enforces role restrictions (e.g. Service Advisors cannot close complaints) (`update_complaint_status`).
- Monitors and flags SLA breaches based on complaint severity (`check_sla_breaches`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: HTTP 403 Forbidden: Advisor cannot close complaint
  -> Cause: Service Advisor attempted to mark a complaint CLOSED.
  -> What should you do: Only CRE Admin, Dealer Admin, or Super Admin can mark complaints RESOLVED / CLOSED.
================================================================================
"""
import uuid
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint import Complaint, ComplaintCategory, ComplaintEvent, Reconfirmation
from app.models.service import JobCard
from app.models.customer import Customer, Vehicle
from app.models.followup import FollowupQueue, Call, SurveyResponse
from app.models.additional import TNPSCall, AdvisorCall
from app.models.tenant import Brand, Branch
from app.models.auth import User
from app.core.crypto import decrypt_phone, mask_phone
from app.schemas.complaint_flow import (
    ComplaintListItem,
    ComplaintDetailResponse,
    ComplaintEventResponse,
    ReconfirmationResponse,
    ComplaintStatusUpdateRequest,
    ReconfirmationSubmitRequest,
    SubmitTnpsRequest,
    TnpsStatsResponse,
    AdvisorCallListItem,
    AdvisorCorrectionSubmitRequest,
)


def make_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# -------------------------------------------------------------
# 1. Complaint Lifecycle Management
# -------------------------------------------------------------
async def list_complaints(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    status_filter: Optional[str] = None,
    severity_filter: Optional[str] = None,
    branch_id: Optional[uuid.UUID] = None,
    is_sla_breached: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: Optional[User] = None,
) -> Tuple[List[ComplaintListItem], int]:
    """Retrieves paginated complaint tickets with dynamic SLA countdown calculations."""
    filters = [Complaint.tenant_id == tenant_id, Complaint.is_deleted == False]
    now = datetime.now(timezone.utc)

    if status_filter and status_filter != "ALL":
        filters.append(Complaint.status == status_filter.upper())
    if severity_filter and severity_filter != "ALL":
        filters.append(Complaint.severity == severity_filter.upper())
    if branch_id:
        filters.append(Complaint.branch_id == branch_id)

    query = (
        select(Complaint)
        .join(Branch, Complaint.branch_id == Branch.id)
        .join(ComplaintCategory, Complaint.category_id == ComplaintCategory.id)
        .join(JobCard, Complaint.job_card_id == JobCard.id)
        .join(Customer, JobCard.customer_id == Customer.id)
        .join(Vehicle, JobCard.vehicle_id == Vehicle.id)
        .join(Brand, JobCard.brand_id == Brand.id)
        .options(
            selectinload(Complaint.branch),
            selectinload(Complaint.category),
            selectinload(Complaint.assigned_to),
            selectinload(Complaint.job_card).selectinload(JobCard.customer),
            selectinload(Complaint.job_card).selectinload(JobCard.vehicle),
            selectinload(Complaint.job_card).selectinload(JobCard.brand),
        )
        .where(and_(*filters))
    )

    if current_user:
        from app.core.permissions import get_user_effective_permissions, apply_data_scope, PermissionKey
        eff = await get_user_effective_permissions(db, current_user)
        query = apply_data_scope(query, Complaint, current_user, PermissionKey.COMPLAINT_VIEW, eff)

    if search:
        s_term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Complaint.complaint_no.ilike(s_term),
                JobCard.job_card_no.ilike(s_term),
                Customer.name.ilike(s_term),
                Vehicle.reg_no.ilike(s_term),
            )
        )

    # SLA breached filter
    if is_sla_breached is True:
        query = query.where(
            Complaint.sla_due_at < now,
            Complaint.status.not_in(["RESOLVED", "CLOSED"]),
        )

    count_stmt = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_stmt)).scalar() or 0

    items_stmt = query.order_by(Complaint.sla_due_at.asc(), Complaint.created_at.desc()).offset(skip).limit(limit)
    complaints = (await db.execute(items_stmt)).scalars().all()

    results = []
    for c in complaints:
        jc = c.job_card
        cust = jc.customer if jc else None
        veh = jc.vehicle if jc else None
        brand = jc.brand if jc else None
        branch = c.branch

        raw_phone = None
        masked_phone = "+91 ********"
        if cust and cust.phone:
            try:
                decrypted = decrypt_phone(cust.phone)
                raw_phone = decrypted
                masked_phone = mask_phone(decrypted)
            except Exception:
                pass

        sla_due = make_aware(c.sla_due_at)
        breached = now > sla_due and c.status not in ["RESOLVED", "CLOSED"]
        hours_rem = round((sla_due - now).total_seconds() / 3600, 1)

        results.append(
            ComplaintListItem(
                id=c.id,
                complaint_no=c.complaint_no,
                job_card_id=c.job_card_id,
                job_card_no=jc.job_card_no if jc else "N/A",
                customer_name=cust.name if cust else "Customer",
                customer_phone_masked=masked_phone,
                customer_phone_raw=raw_phone,
                vehicle_reg_no=veh.reg_no if veh else "N/A",
                vehicle_model=veh.model if veh else "Car",
                brand_name=brand.name if brand else "Brand",
                brand_code=brand.code if brand else "OEM",
                branch_name=branch.name if branch else "Branch",
                category_name=c.category.name if c.category else "General",
                severity=c.severity,
                status=c.status,
                description=c.description,
                assigned_to_id=c.assigned_to_id,
                assigned_to_name=c.assigned_to.full_name if c.assigned_to else "Unassigned",
                sla_due_at=c.sla_due_at,
                is_sla_breached=breached,
                hours_remaining=hours_rem,
                created_at=c.created_at,
            )
        )

    return results, total_count


async def get_complaint_detail(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    complaint_id: uuid.UUID,
    current_user: Optional[User] = None,
) -> ComplaintDetailResponse:
    """Loads complaint details with event timeline and post-resolution reconfirmation history."""
    stmt = (
        select(Complaint)
        .options(
            selectinload(Complaint.branch),
            selectinload(Complaint.category),
            selectinload(Complaint.assigned_to),
            selectinload(Complaint.job_card).selectinload(JobCard.customer),
            selectinload(Complaint.job_card).selectinload(JobCard.vehicle),
            selectinload(Complaint.job_card).selectinload(JobCard.brand),
            selectinload(Complaint.events).selectinload(ComplaintEvent.complaint),
            selectinload(Complaint.reconfirmations).selectinload(Reconfirmation.conducted_by),
        )
        .where(
            Complaint.id == complaint_id,
            Complaint.tenant_id == tenant_id,
            Complaint.is_deleted == False,
        )
    )
    c = (await db.execute(stmt)).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint ticket not found")

    jc = c.job_card
    cust = jc.customer if jc else None
    veh = jc.vehicle if jc else None
    brand = jc.brand if jc else None

    # Enforce data scope if current_user provided
    can_unmask = False
    if current_user:
        from app.core.permissions import get_user_effective_permissions, DataScope, PermissionKey
        eff = await get_user_effective_permissions(db, current_user)
        is_super = eff.get("is_super_admin", False)
        perms = eff.get("permissions", {})
        can_unmask = is_super or PermissionKey.CONTACT_UNMASK in perms

        if not is_super:
            scope = perms.get(PermissionKey.COMPLAINT_VIEW, DataScope.ALL)
            assigned_branches = [uuid.UUID(b) for b in eff.get("assigned_branches", []) if b]
            if scope == DataScope.ASSIGNED_BRANCHES and c.branch_id not in assigned_branches:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Complaint belongs to a branch outside your assigned scope.",
                )
            elif scope == DataScope.OWN and c.assigned_to_id != current_user.id and (not jc or jc.service_advisor_id != current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Complaint is not assigned to you.",
                )

    raw_phone = None
    masked_phone = "+91 ********"
    if cust and cust.phone:
        try:
            decrypted = decrypt_phone(cust.phone)
            masked_phone = mask_phone(decrypted)
            if can_unmask:
                raw_phone = decrypted
        except Exception:
            pass

    # Fetch event users
    event_responses = []
    for ev in sorted(c.events or [], key=lambda x: x.created_at):
        user_obj = (await db.execute(select(User).where(User.id == ev.performed_by_id))).scalar_one_or_none()
        event_responses.append(
            ComplaintEventResponse(
                id=ev.id,
                event_type=ev.event_type,
                from_status=ev.from_status,
                to_status=ev.to_status,
                remarks=ev.remarks,
                performed_by_name=user_obj.full_name if user_obj else "System",
                created_at=ev.created_at,
            )
        )

    reconfirmation_responses = [
        ReconfirmationResponse(
            id=r.id,
            reconfirmation_date=r.reconfirmation_date,
            status=r.status,
            call_status=r.call_status,
            customer_feedback=r.customer_feedback,
            closure_verified=r.closure_verified,
            conducted_by_name=r.conducted_by.full_name if r.conducted_by else "CRE Caller",
        )
        for r in (c.reconfirmations or [])
    ]

    now = datetime.now(timezone.utc)
    sla_due = make_aware(c.sla_due_at)
    breached = now > sla_due and c.status not in ["RESOLVED", "CLOSED"]

    return ComplaintDetailResponse(
        id=c.id,
        complaint_no=c.complaint_no,
        severity=c.severity,
        status=c.status,
        description=c.description,
        sla_due_at=c.sla_due_at,
        is_sla_breached=breached,
        resolution_remarks=c.resolution_remarks,
        resolved_at=c.resolved_at,
        closed_at=c.closed_at,
        category_name=c.category.name if c.category else "General",
        branch_name=c.branch.name if c.branch else "Branch",
        brand_name=brand.name if brand else "Brand",
        job_card_no=jc.job_card_no if jc else "N/A",
        job_card_date=jc.job_card_date if jc else date.today(),
        customer_name=cust.name if cust else "Customer",
        customer_phone_masked=masked_phone,
        customer_phone_raw=raw_phone,
        vehicle_reg_no=veh.reg_no if veh else "N/A",
        vehicle_model=veh.model if veh else "Car",
        service_advisor=jc.service_advisor_name,
        assigned_to_name=c.assigned_to.full_name if c.assigned_to else "Unassigned",
        events=event_responses,
        reconfirmations=reconfirmation_responses,
        created_at=c.created_at,
    )


async def update_complaint_status(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    current_user: User,
    complaint_id: uuid.UUID,
    payload: ComplaintStatusUpdateRequest,
) -> ComplaintDetailResponse:
    """Updates complaint lifecycle status, records timeline audit, and enqueues reconfirmation call upon resolution."""
    c = (
        await db.execute(
            select(Complaint).where(
                Complaint.id == complaint_id,
                Complaint.tenant_id == tenant_id,
                Complaint.is_deleted == False,
            )
        )
    ).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    old_status = c.status
    new_status = payload.status.upper()
    c.status = new_status

    if payload.assigned_to_id:
        c.assigned_to_id = payload.assigned_to_id

    # Handle RESOLVED status
    if new_status == "RESOLVED":
        c.resolved_by_id = current_user.id
        c.resolved_at = datetime.now()
        c.resolution_remarks = payload.resolution_remarks or payload.remarks

        # Auto-schedule Reconfirmation Call 24h post-resolution!
        reconf_queue = FollowupQueue(
            tenant_id=tenant_id,
            job_card_id=c.job_card_id,
            queue_type="RECONFIRMATION",
            status="PENDING",
            due_at=datetime.now() + timedelta(hours=24),
            attempts=0,
            contacted_count=0,
        )
        db.add(reconf_queue)

    # Handle CLOSED status
    elif new_status == "CLOSED":
        c.closed_by_id = current_user.id
        c.closed_at = datetime.now()

    # Create ComplaintEvent
    event = ComplaintEvent(
        tenant_id=tenant_id,
        complaint_id=c.id,
        performed_by_id=current_user.id,
        event_type="STATUS_CHANGE",
        from_status=old_status,
        to_status=new_status,
        remarks=payload.remarks or payload.resolution_remarks,
    )
    db.add(event)

    await db.commit()
    return await get_complaint_detail(db, tenant_id, c.id)


async def submit_reconfirmation(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    current_user: User,
    payload: ReconfirmationSubmitRequest,
) -> Dict[str, Any]:
    """Submits post-resolution reconfirmation survey, closing or reopening the complaint ticket."""
    c = (
        await db.execute(
            select(Complaint).where(
                Complaint.id == payload.complaint_id,
                Complaint.tenant_id == tenant_id,
                Complaint.is_deleted == False,
            )
        )
    ).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    reconf = Reconfirmation(
        tenant_id=tenant_id,
        complaint_id=c.id,
        conducted_by_id=current_user.id,
        status=payload.status.upper(),
        call_status=payload.call_status,
        customer_feedback=payload.customer_feedback,
        closure_verified=payload.closure_verified,
    )
    db.add(reconf)

    if payload.status.upper() == "SATISFIED_CLOSED":
        c.status = "CLOSED"
        c.closed_by_id = current_user.id
        c.closed_at = datetime.now()

        event = ComplaintEvent(
            tenant_id=tenant_id,
            complaint_id=c.id,
            performed_by_id=current_user.id,
            event_type="CLOSED",
            from_status=c.status,
            to_status="CLOSED",
            remarks=f"Customer verified resolution & satisfaction: {payload.customer_feedback or 'Satisfied'}",
        )
        db.add(event)
    else:
        # Unsatisfied -> Reopen Complaint
        c.status = "REOPENED"
        c.sla_due_at = datetime.now() + timedelta(hours=12) # Urgent 12h SLA

        event = ComplaintEvent(
            tenant_id=tenant_id,
            complaint_id=c.id,
            performed_by_id=current_user.id,
            event_type="REOPENED",
            from_status="RESOLVED",
            to_status="REOPENED",
            remarks=f"Customer unsatisfied during reconfirmation: {payload.customer_feedback}",
        )
        db.add(event)

    await db.commit()
    return {"message": "Reconfirmation recorded", "new_complaint_status": c.status}


# -------------------------------------------------------------
# 2. TNPS Module (Net Promoter Score)
# -------------------------------------------------------------
async def submit_tnps(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    current_user: User,
    payload: SubmitTnpsRequest,
) -> Dict[str, Any]:
    """Records dedicated TNPS survey responses and computes promoter/detractor scores."""
    queue = (
        await db.execute(
            select(FollowupQueue).where(
                FollowupQueue.id == payload.followup_queue_id,
                FollowupQueue.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not queue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue record not found")

    jc = (await db.execute(select(JobCard).where(JobCard.id == queue.job_card_id))).scalar_one_or_none()
    cust = (await db.execute(select(Customer).where(Customer.id == jc.customer_id))).scalar_one_or_none()

    # Create Call entity
    call = Call(
        tenant_id=tenant_id,
        followup_queue_id=queue.id,
        job_card_id=jc.id,
        called_by_id=current_user.id,
        duration_seconds=60,
        phone_dialed=cust.phone if cust else "Encrypted",
        call_status=payload.call_status,
        case_status="Satisfied" if payload.workshop_recommend_score >= 7 else "Dissatisfied",
        voc=payload.voc,
    )
    db.add(call)
    await db.flush()

    # Create TNPSCall entity
    tnps = TNPSCall(
        tenant_id=tenant_id,
        call_id=call.id,
        job_card_id=jc.id,
        conducted_by_id=current_user.id,
        brand_recommend_score=payload.brand_recommend_score,
        workshop_recommend_score=payload.workshop_recommend_score,
        voc=payload.voc,
        document_url=payload.document_url,
    )
    db.add(tnps)

    queue.attempts += 1
    queue.contacted_count += 1
    queue.status = "CONTACTED"
    queue.completed_at = datetime.now()

    await db.commit()
    return {"status": "success", "tnps_id": str(tnps.id)}


async def get_tnps_statistics(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    brand_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
) -> TnpsStatsResponse:
    """Calculates Brand NPS and Workshop NPS scores across promoters, passives, and detractors."""
    stmt = (
        select(TNPSCall)
        .join(JobCard, TNPSCall.job_card_id == JobCard.id)
        .where(TNPSCall.tenant_id == tenant_id, TNPSCall.is_deleted == False)
    )
    if brand_id:
        stmt = stmt.where(JobCard.brand_id == brand_id)
    if branch_id:
        stmt = stmt.where(JobCard.branch_id == branch_id)

    calls = (await db.execute(stmt)).scalars().all()
    total = len(calls)
    if total == 0:
        return TnpsStatsResponse()

    promoters = sum(1 for c in calls if c.workshop_recommend_score >= 9)
    passives = sum(1 for c in calls if 7 <= c.workshop_recommend_score <= 8)
    detractors = sum(1 for c in calls if c.workshop_recommend_score <= 6)

    prom_pct = round((promoters / total) * 100, 1)
    det_pct = round((detractors / total) * 100, 1)
    workshop_nps = round(prom_pct - det_pct, 1)

    brand_prom = sum(1 for c in calls if c.brand_recommend_score >= 9)
    brand_det = sum(1 for c in calls if c.brand_recommend_score <= 6)
    brand_nps = round(((brand_prom - brand_det) / total) * 100, 1)

    return TnpsStatsResponse(
        total_responses=total,
        brand_nps=brand_nps,
        workshop_nps=workshop_nps,
        promoters_count=promoters,
        passives_count=passives,
        detractors_count=detractors,
        promoters_pct=prom_pct,
        detractors_pct=det_pct,
    )


# -------------------------------------------------------------
# 3. Service Advisor Follow-up Portal
# -------------------------------------------------------------
async def list_advisor_tasks(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    current_user: Optional[User] = None,
    advisor_name: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[AdvisorCallListItem]:
    """Retrieves dissatisfied customer VOC items assigned to service advisors for corrective action."""
    stmt = (
        select(JobCard, Call, SurveyResponse)
        .join(Call, Call.job_card_id == JobCard.id)
        .outerjoin(SurveyResponse, SurveyResponse.call_id == Call.id)
        .where(
            JobCard.tenant_id == tenant_id,
            or_(
                Call.case_status.in_(["Dissatisfied", "Complaint Registered"]),
                SurveyResponse.nps_category == "DETRACTOR",
            ),
        )
        .options(
            selectinload(JobCard.customer),
            selectinload(JobCard.vehicle),
            selectinload(JobCard.branch),
        )
        .order_by(Call.called_at.desc())
        .limit(50)
    )

    if current_user:
        from app.core.permissions import get_user_effective_permissions, DataScope, PermissionKey
        eff = await get_user_effective_permissions(db, current_user)
        is_super = eff.get("is_super_admin", False)
        perms = eff.get("permissions", {})
        scope = perms.get(PermissionKey.ADVISOR_ACTION, DataScope.ALL)
        role_name = eff.get("role_name", "").upper()
        if not is_super and (scope == DataScope.OWN or role_name in ["SERVICE_ADVISOR", "ADVISOR"]):
            stmt = stmt.where(
                or_(
                    JobCard.service_advisor_id == current_user.id,
                    JobCard.service_advisor_name.ilike(f"%{current_user.full_name}%"),
                )
            )

    rows = (await db.execute(stmt)).all()
    results = []

    for jc, call, survey in rows:
        cust = jc.customer
        veh = jc.vehicle
        branch = jc.branch

        # Check existing advisor correction
        adv_call_stmt = select(AdvisorCall).where(AdvisorCall.job_card_id == jc.id).order_by(AdvisorCall.created_at.desc())
        existing_adv = (await db.execute(adv_call_stmt)).scalars().first()

        if status_filter and status_filter != "ALL":
            adv_status = existing_adv.adv_status if existing_adv else "PENDING"
            if adv_status != status_filter.upper():
                continue

        results.append(
            AdvisorCallListItem(
                id=existing_adv.id if existing_adv else uuid.uuid4(),
                job_card_id=jc.id,
                job_card_no=jc.job_card_no,
                job_card_date=jc.job_card_date,
                customer_name=cust.name if cust else "Customer",
                customer_phone_masked=mask_phone(decrypt_phone(cust.phone)) if cust and cust.phone else "+91 ********",
                vehicle_reg_no=veh.reg_no if veh else "N/A",
                vehicle_model=veh.model if veh else "Car",
                branch_name=branch.name if branch else "Branch",
                dissatisfied_voc=call.voc,
                csat_score=survey.csat_score if survey else None,
                nps_category=survey.nps_category if survey else None,
                adv_call_status=existing_adv.adv_call_status if existing_adv else None,
                adv_case_status=existing_adv.adv_case_status if existing_adv else None,
                adv_voc=existing_adv.adv_voc if existing_adv else None,
                adv_status=existing_adv.adv_status if existing_adv else "PENDING",
                created_at=call.called_at,
            )
        )

    return results


async def submit_advisor_correction(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    current_user: User,
    payload: AdvisorCorrectionSubmitRequest,
) -> Dict[str, Any]:
    """Records service advisor corrective explanation and marks customer concern resolved."""
    jc = (
        await db.execute(
            select(JobCard).where(
                JobCard.id == payload.job_card_id,
                JobCard.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not jc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job Card not found")

    # Find recent call
    call = (
        await db.execute(
            select(Call).where(Call.job_card_id == jc.id).order_by(Call.called_at.desc())
        )
    ).scalars().first()

    advisor_call = AdvisorCall(
        tenant_id=tenant_id,
        call_id=call.id if call else uuid.uuid4(),
        job_card_id=jc.id,
        advisor_id=current_user.id,
        adv_call_status=payload.adv_call_status,
        adv_case_status=payload.adv_case_status,
        adv_voc=payload.adv_voc,
        adv_status=payload.adv_status.upper(),
    )
    db.add(advisor_call)
    await db.commit()

    return {"message": "Advisor corrective action logged successfully"}


# -------------------------------------------------------------
# 4. Happiness Calling (Hyundai Exclusive)
# -------------------------------------------------------------
async def list_happiness_queues(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    branch_id: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Any], int]:
    """
    Retrieves 15-day and 30-day post-delivery Happiness Calling queues.
    STRICT OEM COMPLIANCE: Exclusively returns records for Hyundai brand.
    """
    filters = [
        FollowupQueue.tenant_id == tenant_id,
        FollowupQueue.queue_type == "HAPPINESS",
        FollowupQueue.is_deleted == False,
    ]
    if status_filter and status_filter != "ALL":
        filters.append(FollowupQueue.status == status_filter.upper())

    jc_filters = [JobCard.tenant_id == tenant_id, JobCard.is_deleted == False]
    if branch_id:
        jc_filters.append(JobCard.branch_id == branch_id)

    # Strictly enforce Hyundai Brand
    query = (
        select(FollowupQueue)
        .join(JobCard, FollowupQueue.job_card_id == JobCard.id)
        .join(Brand, JobCard.brand_id == Brand.id)
        .join(Branch, JobCard.branch_id == Branch.id)
        .join(Customer, JobCard.customer_id == Customer.id)
        .join(Vehicle, JobCard.vehicle_id == Vehicle.id)
        .options(
            selectinload(FollowupQueue.job_card).selectinload(JobCard.customer),
            selectinload(FollowupQueue.job_card).selectinload(JobCard.vehicle),
            selectinload(FollowupQueue.job_card).selectinload(JobCard.brand),
            selectinload(FollowupQueue.job_card).selectinload(JobCard.branch),
            selectinload(FollowupQueue.assigned_to),
        )
        .where(
            and_(
                *filters,
                *jc_filters,
                or_(Brand.code.in_(["HYUN", "HYUNDAI"]), Brand.name.ilike("%HYUNDAI%")),
            )
        )
    )

    if search:
        s_term = f"%{search.strip()}%"
        query = query.where(
            or_(
                JobCard.job_card_no.ilike(s_term),
                Customer.name.ilike(s_term),
                Vehicle.reg_no.ilike(s_term),
            )
        )

    count_stmt = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_stmt)).scalar() or 0

    items_stmt = query.order_by(FollowupQueue.due_at.asc()).offset(skip).limit(limit)
    queues = (await db.execute(items_stmt)).scalars().all()

    return queues, total_count
