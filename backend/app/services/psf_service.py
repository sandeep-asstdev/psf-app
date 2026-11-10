"""
================================================================================
FILE PURPOSE: PSF Follow-up Calling Workspace & Dossier Service.
Powers the PSF calling operations: calculates dashboard counters,
retrieves calling queue line items with role scoping, builds complete customer dossiers
for the calling dialer modal, and records submitted customer call logs.

KEY RESPONSIBILITIES:
- Calculates high-level metrics (pending, contacted, connect rate, open complaints) (`get_dashboard_stats`).
- Retrieves paginated calling queue records with masked phone numbers (`list_followup_queues`).
- Enforces CRE role scoping so CREs only see their assigned customers.
- Builds full customer dossier for Call Console dialer (`get_call_console_data`).
- Processes submitted call logs, updating sentiments, CSAT scores, and queue statuses (`submit_call_log`).
- Handles bulk reassignment of calls between CREs (`bulk_assign_queues`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Line items table showing 0 records or spinning
  -> Cause: Network request failed or user scope filtered out all records.
  -> What should you do: Check browser DevTools console for API status. If logged in as CRE, verify calls have been assigned to your user ID.
================================================================================
"""
import uuid
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import JobCard
from app.models.customer import Customer, Vehicle
from app.models.followup import FollowupQueue, Call, CallAttempt, SurveyResponse, Reminder
from app.models.complaint import Complaint, ComplaintCategory, ComplaintEvent
from app.models.questionnaire import Questionnaire, Question
from app.models.tenant import Brand, Branch
from app.models.auth import User
from app.core.crypto import decrypt_phone, mask_phone, encrypt_phone, hash_phone
from app.schemas.psf import (
    PsfDashboardStats,
    FollowupQueueListItem,
    CallConsoleDetails,
    SubmitCallRequest,
    SubmitCallResponse,
)
from app.schemas.questionnaire import QuestionnaireDetailResponse, QuestionResponse
from app.services.questionnaire_service import calculate_survey_score, get_questionnaire_by_id


async def get_dashboard_stats(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    brand_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
    cre_id: Optional[uuid.UUID] = None,
) -> PsfDashboardStats:
    """Aggregates multi-tenant follow-up metrics and grouped widget summaries."""
    queue_filters = [FollowupQueue.tenant_id == tenant_id, FollowupQueue.is_deleted == False]
    jc_filters = [JobCard.tenant_id == tenant_id, JobCard.is_deleted == False]

    if brand_id:
        jc_filters.append(JobCard.brand_id == brand_id)
    if branch_id:
        jc_filters.append(JobCard.branch_id == branch_id)
    if cre_id:
        queue_filters.append(FollowupQueue.assigned_to_id == cre_id)

    # 1. Total Pending & Contacted
    pending_statuses = ["PENDING", "NOT_CONTACTED", "CALLBACK_REQUESTED", "IN_PROGRESS"]
    contacted_statuses = ["CONTACTED", "CONNECTED", "SATISFIED", "COMPLAINT_REGISTERED", "CLOSED", "CLOSED_MAX_ATTEMPTS"]

    pending_stmt = (
        select(func.count(FollowupQueue.id))
        .join(JobCard, FollowupQueue.job_card_id == JobCard.id)
        .where(and_(*queue_filters, *jc_filters, FollowupQueue.status.in_(pending_statuses)))
    )
    total_pending = (await db.execute(pending_stmt)).scalar() or 0

    contacted_stmt = (
        select(func.count(FollowupQueue.id))
        .join(JobCard, FollowupQueue.job_card_id == JobCard.id)
        .where(and_(*queue_filters, *jc_filters, FollowupQueue.status.in_(contacted_statuses)))
    )
    total_contacted = (await db.execute(contacted_stmt)).scalar() or 0

    total_pool = total_pending + total_contacted
    connect_rate = round((total_contacted / total_pool) * 100, 1) if total_pool > 0 else 0.0

    # 2. Open Complaints Count
    comp_filters = [Complaint.tenant_id == tenant_id, Complaint.is_deleted == False]
    if branch_id:
        comp_filters.append(Complaint.branch_id == branch_id)
    open_comp_stmt = select(func.count(Complaint.id)).where(
        and_(*comp_filters, Complaint.status.in_(["OPEN", "ASSIGNED", "IN_PROGRESS", "REOPENED"]))
    )
    open_complaints_count = (await db.execute(open_comp_stmt)).scalar() or 0

    # 3. Reminders Today Count
    today_start = datetime.combine(date.today(), time.min)
    today_end = datetime.combine(date.today(), time.max)
    rem_stmt = select(func.count(Reminder.id)).where(
        Reminder.tenant_id == tenant_id,
        Reminder.is_acknowledged == False,
        Reminder.remind_at <= today_end,
    )
    reminders_today_count = (await db.execute(rem_stmt)).scalar() or 0

    # 4. Grouped: PSF by Brand -> Branch
    brand_branch_stmt = (
        select(
            Brand.id.label("brand_id"),
            Brand.name.label("brand_name"),
            Brand.code.label("brand_code"),
            Branch.id.label("branch_id"),
            Branch.name.label("branch_name"),
            func.count(FollowupQueue.id).label("count"),
        )
        .join(JobCard, FollowupQueue.job_card_id == JobCard.id)
        .join(Brand, JobCard.brand_id == Brand.id)
        .join(Branch, JobCard.branch_id == Branch.id)
        .where(and_(*queue_filters, *jc_filters, FollowupQueue.status.in_(pending_statuses)))
        .group_by(Brand.id, Brand.name, Brand.code, Branch.id, Branch.name)
        .order_by(Brand.name, Branch.name)
    )
    brand_branch_rows = (await db.execute(brand_branch_stmt)).all()
    by_brand_branch = [
        {
            "brand_id": str(r.brand_id),
            "brand_name": r.brand_name,
            "brand_code": r.brand_code,
            "branch_id": str(r.branch_id),
            "branch_name": r.branch_name,
            "count": r.count,
        }
        for r in brand_branch_rows
    ]

    # 5. Grouped: Follow-up History by Call Status
    call_status_stmt = (
        select(Call.call_status, func.count(Call.id).label("count"))
        .where(Call.tenant_id == tenant_id, Call.is_deleted == False)
        .group_by(Call.call_status)
        .order_by(desc("count"))
    )
    call_status_rows = (await db.execute(call_status_stmt)).all()
    by_call_status = [{"status": r.call_status, "count": r.count} for r in call_status_rows]

    # 6. Grouped: Open Complaints by Branch
    open_comp_branch_stmt = (
        select(
            Branch.id.label("branch_id"),
            Branch.name.label("branch_name"),
            func.count(Complaint.id).label("count"),
            func.count(Complaint.id).filter(Complaint.is_sla_breached == True).label("breached_count"),
        )
        .join(Branch, Complaint.branch_id == Branch.id)
        .where(and_(*comp_filters, Complaint.status.in_(["OPEN", "ASSIGNED", "IN_PROGRESS"])))
        .group_by(Branch.id, Branch.name)
        .order_by(desc("count"))
    )
    open_comp_branch_rows = (await db.execute(open_comp_branch_stmt)).all()
    open_complaints_by_branch = [
        {
            "branch_id": str(r.branch_id),
            "branch_name": r.branch_name,
            "count": r.count,
            "sla_breached_count": r.breached_count,
        }
        for r in open_comp_branch_rows
    ]

    # 7. Grouped: Closed Complaints by Branch
    closed_comp_branch_stmt = (
        select(Branch.id.label("branch_id"), Branch.name.label("branch_name"), func.count(Complaint.id).label("count"))
        .join(Branch, Complaint.branch_id == Branch.id)
        .where(and_(*comp_filters, Complaint.status.in_(["RESOLVED", "CLOSED"])))
        .group_by(Branch.id, Branch.name)
        .order_by(desc("count"))
    )
    closed_comp_branch_rows = (await db.execute(closed_comp_branch_stmt)).all()
    closed_complaints_by_branch = [
        {"branch_id": str(r.branch_id), "branch_name": r.branch_name, "count": r.count}
        for r in closed_comp_branch_rows
    ]

    # 8. Grouped: Calls by Service Advisor
    advisor_stmt = (
        select(JobCard.service_advisor_name, func.count(FollowupQueue.id).label("count"))
        .join(JobCard, FollowupQueue.job_card_id == JobCard.id)
        .where(and_(*queue_filters, *jc_filters, JobCard.service_advisor_name != None))
        .group_by(JobCard.service_advisor_name)
        .order_by(desc("count"))
        .limit(10)
    )
    advisor_rows = (await db.execute(advisor_stmt)).all()
    by_advisor = [{"advisor_name": r.service_advisor_name, "count": r.count} for r in advisor_rows]

    # 9. Grouped: Calls by Assigned CRE
    assigned_cre_stmt = (
        select(
            User.id.label("user_id"),
            User.full_name.label("user_name"),
            User.email.label("user_email"),
            func.count(FollowupQueue.id).label("total_assigned"),
            func.count(FollowupQueue.id).filter(FollowupQueue.status.in_(pending_statuses)).label("pending_count"),
            func.count(FollowupQueue.id).filter(FollowupQueue.status.in_(contacted_statuses)).label("contacted_count"),
        )
        .join(FollowupQueue, FollowupQueue.assigned_to_id == User.id)
        .join(JobCard, FollowupQueue.job_card_id == JobCard.id)
        .where(and_(*queue_filters, *jc_filters))
        .group_by(User.id, User.full_name, User.email)
        .order_by(desc("pending_count"))
    )
    assigned_cre_rows = (await db.execute(assigned_cre_stmt)).all()
    by_assigned_cre = [
        {
            "user_id": str(r.user_id),
            "user_name": r.user_name,
            "user_email": r.user_email,
            "total_assigned": r.total_assigned,
            "pending_count": r.pending_count,
            "contacted_count": r.contacted_count,
        }
        for r in assigned_cre_rows
    ]

    # Unassigned calls count
    unassigned_stmt = (
        select(func.count(FollowupQueue.id))
        .join(JobCard, FollowupQueue.job_card_id == JobCard.id)
        .where(and_(*queue_filters, *jc_filters, FollowupQueue.assigned_to_id == None, FollowupQueue.status.in_(pending_statuses)))
    )
    unassigned_count = (await db.execute(unassigned_stmt)).scalar() or 0

    return PsfDashboardStats(
        total_pending=total_pending,
        total_contacted=total_contacted,
        connect_rate_pct=connect_rate,
        open_complaints_count=open_complaints_count,
        reminders_today_count=reminders_today_count,
        by_brand_branch=by_brand_branch,
        by_call_status=by_call_status,
        open_complaints_by_branch=open_complaints_by_branch,
        closed_complaints_by_branch=closed_complaints_by_branch,
        by_advisor=by_advisor,
        by_assigned_cre=by_assigned_cre,
        unassigned_count=unassigned_count,
    )


async def list_followup_queues(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    queue_type: str = "PSF",
    status_filter: Optional[str] = None,
    brand_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
    assigned_to_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: Optional[User] = None,
) -> Tuple[List[FollowupQueueListItem], int]:
    """Retrieves paginated queue records with masked customer contact snapshot."""
    filters = [
        FollowupQueue.tenant_id == tenant_id,
        FollowupQueue.is_deleted == False,
    ]
    if queue_type and queue_type != "ALL":
        filters.append(FollowupQueue.queue_type == queue_type.upper())
    if status_filter and status_filter != "ALL":
        sf = status_filter.upper()
        if sf in ("ACTIVE", "DUE"):
            filters.append(FollowupQueue.status.in_(["PENDING", "NOT_CONTACTED", "CALLBACK_REQUESTED", "IN_PROGRESS"]))
        elif sf in ("CONTACTED", "CONNECTED"):
            filters.append(FollowupQueue.status.in_(["CONTACTED", "CONNECTED"]))
        elif sf in ("NOT_CONTACTED", "RETRY"):
            filters.append(FollowupQueue.status.in_(["NOT_CONTACTED", "CLOSED_MAX_ATTEMPTS"]))
        elif sf in ("CALLBACK", "CALLBACK_REQUESTED"):
            filters.append(FollowupQueue.status == "CALLBACK_REQUESTED")
        elif sf == "COMPLAINT_REGISTERED":
            filters.append(FollowupQueue.status == "COMPLAINT_REGISTERED")
        else:
            filters.append(FollowupQueue.status == sf)
    if assigned_to_id:
        filters.append(FollowupQueue.assigned_to_id == assigned_to_id)

    jc_filters = [JobCard.tenant_id == tenant_id, JobCard.is_deleted == False]
    if brand_id:
        jc_filters.append(JobCard.brand_id == brand_id)
    if branch_id:
        jc_filters.append(JobCard.branch_id == branch_id)

    base_query = (
        select(FollowupQueue)
        .join(JobCard, FollowupQueue.job_card_id == JobCard.id)
        .join(Customer, JobCard.customer_id == Customer.id)
        .join(Vehicle, JobCard.vehicle_id == Vehicle.id)
        .join(Brand, JobCard.brand_id == Brand.id)
        .join(Branch, JobCard.branch_id == Branch.id)
        .options(
            selectinload(FollowupQueue.job_card).selectinload(JobCard.customer),
            selectinload(FollowupQueue.job_card).selectinload(JobCard.vehicle),
            selectinload(FollowupQueue.job_card).selectinload(JobCard.brand),
            selectinload(FollowupQueue.job_card).selectinload(JobCard.branch),
            selectinload(FollowupQueue.assigned_to),
            selectinload(FollowupQueue.calls),
        )
        .where(and_(*filters, *jc_filters))
    )

    if current_user:
        from app.core.permissions import get_user_effective_permissions, apply_data_scope, PermissionKey, DataScope
        eff = await get_user_effective_permissions(db, current_user)
        is_super = eff.get("is_super_admin", False)
        perms = eff.get("permissions", {})
        scope = perms.get(PermissionKey.CALL_VIEW, DataScope.ALL)
        user_role_name = eff.get("role_name", "").upper()

        if not is_super and (scope == DataScope.OWN or user_role_name in ["CRE", "BRANCH_CRE"]):
            # CREs must strictly only see their own assigned calls
            base_query = base_query.where(FollowupQueue.assigned_to_id == current_user.id)
        else:
            base_query = apply_data_scope(base_query, FollowupQueue, current_user, PermissionKey.CALL_VIEW, eff)

    if search:
        s_term = f"%{search.strip()}%"
        base_query = base_query.where(
            or_(
                JobCard.job_card_no.ilike(s_term),
                Customer.name.ilike(s_term),
                Vehicle.reg_no.ilike(s_term),
                Vehicle.model.ilike(s_term),
            )
        )

    # Count total
    count_stmt = select(func.count()).select_from(base_query.subquery())
    total_count = (await db.execute(count_stmt)).scalar() or 0

    # Execute paginated
    items_stmt = base_query.order_by(FollowupQueue.last_attempt_at.desc().nulls_last(), FollowupQueue.due_at.asc(), FollowupQueue.created_at.desc()).offset(skip).limit(limit)
    queues = (await db.execute(items_stmt)).scalars().all()

    results = []
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

        last_call = max(q.calls, key=lambda c: c.called_at) if q.calls else None

        results.append(
            FollowupQueueListItem(
                id=q.id,
                job_card_id=q.job_card_id,
                job_card_no=jc.job_card_no if jc else "N/A",
                job_card_date=jc.job_card_date if jc else date.today(),
                total_amount=jc.total_amount if jc else Decimal("0.0"),
                customer_id=cust.id if cust else uuid.uuid4(),
                customer_name=cust.name if cust else "Customer",
                customer_phone_masked=masked_phone,
                customer_phone_raw=raw_phone,
                vehicle_reg_no=veh.reg_no if veh else "N/A",
                vehicle_model=veh.model if veh else "Car",
                brand_id=brand.id if brand else uuid.uuid4(),
                brand_name=brand.name if brand else "Brand",
                brand_code=brand.code if brand else "OEM",
                brand_color=brand.primary_color if brand else "#2563EB",
                brand_logo_url=brand.logo_url if brand else None,
                branch_id=branch.id if branch else uuid.uuid4(),
                branch_name=branch.name if branch else "Branch",
                service_advisor=jc.service_advisor_name if jc else None,
                technician_name=jc.technician_name if jc else None,
                service_type=jc.service_type if jc else None,
                vin_no=veh.vin if veh else None,
                queue_type=q.queue_type,
                status=q.status,
                attempts=q.attempts,
                contacted_count=q.contacted_count or 0,
                last_attempt_at=q.last_attempt_at,
                followup_timestamp=last_call.called_at if last_call else q.last_attempt_at,
                due_at=q.due_at,
                assigned_to_id=q.assigned_to_id,
                assigned_to_name=q.assigned_to.full_name if q.assigned_to else None,
                last_call_status=last_call.call_status if last_call else None,
                last_case_status=last_call.case_status if last_call else None,
                voc=last_call.voc if last_call and last_call.voc else None,
            )
        )

    return results, total_count


async def get_call_console_data(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    queue_id: uuid.UUID,
    current_user: User,
) -> CallConsoleDetails:
    """Loads all data required by the split-layout Call Console screen."""
    stmt = (
        select(FollowupQueue)
        .options(
            selectinload(FollowupQueue.job_card).selectinload(JobCard.customer),
            selectinload(FollowupQueue.job_card).selectinload(JobCard.vehicle),
            selectinload(FollowupQueue.job_card).selectinload(JobCard.brand),
            selectinload(FollowupQueue.job_card).selectinload(JobCard.branch),
            selectinload(FollowupQueue.assigned_to),
            selectinload(FollowupQueue.calls).selectinload(Call.caller),
        )
        .where(
            FollowupQueue.id == queue_id,
            FollowupQueue.tenant_id == tenant_id,
            FollowupQueue.is_deleted == False,
        )
    )
    queue = (await db.execute(stmt)).scalar_one_or_none()
    if not queue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue record not found")

    jc = queue.job_card
    cust = jc.customer
    veh = jc.vehicle
    brand = jc.brand
    branch = jc.branch

    # Decrypt customer phone
    decrypted_phone = None
    masked_phone = "+91 ********"
    decrypted_alt_phone = None
    if cust.phone:
        try:
            decrypted_phone = decrypt_phone(cust.phone)
            masked_phone = mask_phone(decrypted_phone)
        except Exception:
            pass
    if cust.alt_phone:
        try:
            decrypted_alt_phone = decrypt_phone(cust.alt_phone)
        except Exception:
            pass

    # Previous call history
    call_history = []
    for c in sorted(queue.calls or [], key=lambda x: x.called_at, reverse=True):
        call_history.append(
            {
                "id": str(c.id),
                "called_at": c.called_at.isoformat(),
                "called_by": c.caller.full_name if c.caller else "CRE",
                "duration_seconds": c.duration_seconds,
                "call_status": c.call_status,
                "case_status": c.case_status,
                "voc": c.voc,
            }
        )

    # Find matching dynamic questionnaire for this brand and queue type
    q_stmt = (
        select(Questionnaire)
        .where(
            Questionnaire.tenant_id == tenant_id,
            Questionnaire.brand_id == brand.id,
            Questionnaire.type == queue.queue_type,
            Questionnaire.is_active == True,
            Questionnaire.is_deleted == False,
        )
        .order_by(Questionnaire.version.desc())
    )
    questionnaire_model = (await db.execute(q_stmt)).scalars().first()
    questionnaire_dto = None
    if questionnaire_model:
        q_full = await get_questionnaire_by_id(db, tenant_id, questionnaire_model.id)
        if q_full:
            questionnaire_dto = QuestionnaireDetailResponse(
                id=q_full.id,
                tenant_id=q_full.tenant_id,
                brand_id=q_full.brand_id,
                brand_name=brand.name,
                brand_code=brand.code,
                type=q_full.type,
                title=q_full.title,
                version=q_full.version,
                is_active=q_full.is_active,
                questions=[
                    QuestionResponse(
                        id=q.id,
                        tenant_id=q.tenant_id,
                        questionnaire_id=q.questionnaire_id,
                        key=q.key,
                        label=q.label,
                        type=q.type,
                        section=q.section,
                        options=q.options,
                        show_if=q.show_if,
                        weight=q.weight,
                        display_order=q.display_order,
                        is_required=q.is_required,
                        created_at=q.created_at,
                        updated_at=q.updated_at,
                    )
                    for q in (q_full.questions or [])
                ],
                created_at=q_full.created_at,
                updated_at=q_full.updated_at,
            )

    # Next queue item in caller's queue (for "Save & Next" one-click workflow)
    next_stmt = (
        select(FollowupQueue.id)
        .where(
            FollowupQueue.tenant_id == tenant_id,
            FollowupQueue.id != queue_id,
            FollowupQueue.queue_type == queue.queue_type,
            FollowupQueue.status.in_(["PENDING", "NOT_CONTACTED", "CALLBACK_REQUESTED"]),
            FollowupQueue.is_deleted == False,
        )
        .order_by(FollowupQueue.due_at.asc())
        .limit(1)
    )
    next_queue_id = (await db.execute(next_stmt)).scalar_one_or_none()

    queue_dto = FollowupQueueListItem(
        id=queue.id,
        job_card_id=queue.job_card_id,
        job_card_no=jc.job_card_no,
        job_card_date=jc.job_card_date,
        total_amount=jc.total_amount,
        customer_id=cust.id,
        customer_name=cust.name,
        customer_phone_masked=masked_phone,
        customer_phone_raw=decrypted_phone,
        vehicle_reg_no=veh.reg_no,
        vehicle_model=veh.model,
        brand_id=brand.id,
        brand_name=brand.name,
        brand_code=brand.code,
        brand_color=brand.primary_color or "#2563EB",
        branch_id=branch.id,
        branch_name=branch.name,
        service_advisor=jc.service_advisor_name,
        queue_type=queue.queue_type,
        status=queue.status,
        attempts=queue.attempts,
        last_attempt_at=queue.last_attempt_at,
        due_at=queue.due_at,
        assigned_to_id=queue.assigned_to_id,
        assigned_to_name=queue.assigned_to.full_name if queue.assigned_to else None,
    )

    return CallConsoleDetails(
        queue=queue_dto,
        customer={
            "id": str(cust.id),
            "name": cust.name,
            "phone_masked": masked_phone,
            "phone_raw": decrypted_phone,
            "alt_phone_raw": decrypted_alt_phone,
            "email": cust.email,
            "city": cust.city or branch.city,
            "address": cust.address,
            "dnd": cust.do_not_disturb,
        },
        vehicle={
            "id": str(veh.id),
            "reg_no": veh.reg_no,
            "vin": veh.vin or "Not Recorded",
            "model": veh.model,
            "variant": veh.variant,
            "fuel_type": veh.fuel_type or "Petrol",
            "delivery_date": str(veh.delivery_date) if veh.delivery_date else None,
        },
        job_card={
            "id": str(jc.id),
            "job_card_no": jc.job_card_no,
            "job_card_date": str(jc.job_card_date),
            "total_amount": float(jc.total_amount),
            "service_advisor": jc.service_advisor_name or "General",
            "technician": jc.technician_name or "Workshop Team",
            "service_type": jc.service_type or "Periodic Service",
            "branch_name": branch.name,
            "brand_name": brand.name,
            "brand_color": brand.primary_color or "#2563EB",
            "odometer": jc.odometer_reading,
        },
        call_history=call_history,
        questionnaire=questionnaire_dto,
        next_queue_id=next_queue_id,
    )


async def submit_call_log(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    current_user: User,
    payload: SubmitCallRequest,
) -> SubmitCallResponse:
    """
    Submits a call attempt, records CSAT/NPS scores, creates complaints with SLA timers,
    updates queue status, and returns the next queue candidate.
    """
    stmt = (
        select(FollowupQueue)
        .options(
            selectinload(FollowupQueue.job_card).selectinload(JobCard.customer),
            selectinload(FollowupQueue.job_card).selectinload(JobCard.branch),
            selectinload(FollowupQueue.job_card).selectinload(JobCard.brand),
        )
        .where(
            FollowupQueue.id == payload.followup_queue_id,
            FollowupQueue.tenant_id == tenant_id,
            FollowupQueue.is_deleted == False,
        )
    )
    queue = (await db.execute(stmt)).scalar_one_or_none()
    if not queue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Followup queue record not found")

    jc = queue.job_card
    cust = jc.customer

    # 1. Create Call Record
    call = Call(
        tenant_id=tenant_id,
        followup_queue_id=queue.id,
        job_card_id=jc.id,
        called_by_id=current_user.id,
        duration_seconds=payload.duration_seconds,
        phone_dialed=cust.phone,
        call_status=payload.call_status,
        case_status=payload.case_status,
        voc=payload.voc,
    )
    db.add(call)
    await db.flush()

    # 2. Score questionnaire answers if submitted
    csat = None
    nps_val = None
    nps_cat = None

    if payload.survey_answers:
        # Fetch active questionnaire questions
        q_stmt = (
            select(Questionnaire)
            .where(
                Questionnaire.tenant_id == tenant_id,
                Questionnaire.brand_id == jc.brand_id,
                Questionnaire.type == queue.queue_type,
                Questionnaire.is_active == True,
            )
            .order_by(Questionnaire.version.desc())
        )
        q_model = (await db.execute(q_stmt)).scalars().first()
        if q_model:
            q_full = await get_questionnaire_by_id(db, tenant_id, q_model.id)
            if q_full and q_full.questions:
                # Normalize survey answers (e.g. Yes/No)
                normalized_answers = {}
                for k, v in payload.survey_answers.items():
                    if isinstance(v, str):
                        if v.lower() in ("yes", "y", "true"):
                            normalized_answers[k] = "Yes"
                        elif v.lower() in ("no", "n", "false"):
                            normalized_answers[k] = "No"
                        else:
                            normalized_answers[k] = v
                    else:
                        normalized_answers[k] = v

                csat, nps_val, nps_cat = calculate_survey_score(normalized_answers, q_full.questions)

                survey_resp = SurveyResponse(
                    tenant_id=tenant_id,
                    call_id=call.id,
                    job_card_id=jc.id,
                    questionnaire_id=q_full.id,
                    answers=normalized_answers,
                    csat_score=csat,
                    nps_score=nps_val,
                    nps_category=nps_cat,
                )
                db.add(survey_resp)

    # 3. Handle Complaint creation if checked
    complaint_ticket = None
    if payload.has_complaint:
        category_id = payload.complaint_category_id
        if not category_id:
            # Find default category
            cat_stmt = select(ComplaintCategory).where(
                ComplaintCategory.tenant_id == tenant_id,
                ComplaintCategory.is_active == True,
            )
            cat_obj = (await db.execute(cat_stmt)).scalars().first()
            category_id = cat_obj.id if cat_obj else None

        # Calculate SLA Due Date
        sla_hours = 24
        if category_id:
            cat_res = await db.execute(select(ComplaintCategory).where(ComplaintCategory.id == category_id))
            cat_found = cat_res.scalar_one_or_none()
            if cat_found:
                sla_hours = cat_found.default_sla_hours

        sla_due_at = datetime.now() + timedelta(hours=sla_hours)
        ticket_no = f"CMP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        complaint = Complaint(
            tenant_id=tenant_id,
            branch_id=jc.branch_id,
            job_card_id=jc.id,
            call_id=call.id,
            category_id=category_id,
            complaint_no=ticket_no,
            severity=payload.complaint_severity or "MEDIUM",
            status="OPEN",
            description=payload.complaint_description or payload.voc or "Customer expressed dissatisfaction",
            assigned_to_id=payload.complaint_assigned_to_id or current_user.id,
            sla_due_at=sla_due_at,
        )
        db.add(complaint)
        await db.flush()

        # Add Complaint Event
        comp_event = ComplaintEvent(
            tenant_id=tenant_id,
            complaint_id=complaint.id,
            performed_by_id=current_user.id,
            event_type="CREATED",
            from_status=None,
            to_status="OPEN",
            remarks=f"Registered during PSF call by {current_user.full_name}",
        )
        db.add(comp_event)
        complaint_ticket = ticket_no

    # 4. Update Queue Counters & Status
    queue.attempts += 1
    now = datetime.now(timezone.utc)
    queue.last_attempt_at = now

    is_callback = (
        payload.call_status == "Callback Requested"
        or payload.case_status == "Callback Requested"
        or payload.callback_at is not None
    )

    if is_callback:
        # Callback Requested
        cb_time = payload.callback_at or (now + timedelta(days=1, hours=2))
        reminder = Reminder(
            tenant_id=tenant_id,
            followup_queue_id=queue.id,
            assigned_to_id=current_user.id,
            remind_at=cb_time,
            note=payload.callback_note or payload.voc or "Customer requested callback",
        )
        db.add(reminder)
        queue.status = "CALLBACK_REQUESTED"
        queue.next_followup_at = cb_time
        queue.completed_at = None

    elif payload.call_status == "Connected":
        queue.contacted_count += 1
        if payload.has_complaint or payload.case_status == "Complaint Registered":
            queue.status = "COMPLAINT_REGISTERED"
            queue.completed_at = None
        elif payload.case_status in ["Satisfied", "Closed", "Delight"]:
            queue.status = "CONTACTED"
            queue.completed_at = now
        elif payload.case_status in ["Dissatisfied", "Non-Delight"]:
            queue.status = "IN_PROGRESS"
            queue.completed_at = None
        else:
            queue.status = "CONTACTED"
            queue.completed_at = now

    else:
        # Not Connected, Busy, Switched Off, Wrong Number, etc.
        if queue.attempts >= 3:
            queue.status = "CLOSED_MAX_ATTEMPTS"
            queue.completed_at = now
        else:
            queue.status = "NOT_CONTACTED"
            queue.next_followup_at = now + timedelta(hours=4)
            queue.completed_at = None

    # Log a CallAttempt in call_attempts table
    attempt = CallAttempt(
        tenant_id=tenant_id,
        followup_queue_id=queue.id,
        attempt_number=queue.attempts,
        call_status=payload.call_status,
        case_status=payload.case_status,
        voc=payload.voc,
        rating=int(csat / 10) if csat else None,
        called_by_id=current_user.id,
        called_at=now,
        duration_seconds=payload.duration_seconds,
    )
    db.add(attempt)

    # 6. Find next queue item in user's queue for "Save & Next"
    next_stmt = (
        select(FollowupQueue.id)
        .where(
            FollowupQueue.tenant_id == tenant_id,
            FollowupQueue.id != queue.id,
            FollowupQueue.queue_type == queue.queue_type,
            FollowupQueue.status.in_(["PENDING", "NOT_CONTACTED", "CALLBACK_REQUESTED"]),
            FollowupQueue.is_deleted == False,
        )
        .order_by(FollowupQueue.due_at.asc())
        .limit(1)
    )
    next_queue_id = (await db.execute(next_stmt)).scalar_one_or_none()

    await db.commit()

    return SubmitCallResponse(
        call_id=call.id,
        queue_id=queue.id,
        queue_status=queue.status,
        csat_score=csat,
        nps_score=nps_val,
        nps_category=nps_cat,
        complaint_ticket_no=complaint_ticket,
        next_queue_id=next_queue_id,
    )


async def bulk_assign_queues(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    queue_ids: List[uuid.UUID],
    assigned_to_id: Optional[uuid.UUID],
) -> int:
    """Bulk allocates selected queue records to a specific CRE user."""
    stmt = (
        select(FollowupQueue)
        .where(
            FollowupQueue.tenant_id == tenant_id,
            FollowupQueue.id.in_(queue_ids),
            FollowupQueue.is_deleted == False,
        )
    )
    queues = (await db.execute(stmt)).scalars().all()
    for q in queues:
        q.assigned_to_id = assigned_to_id
    await db.commit()
    return len(queues)

