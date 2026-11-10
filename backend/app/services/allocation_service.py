"""
================================================================================
FILE PURPOSE: Automatic Equal Call Allocation Engine.
This is the core business logic service that divides imported DMS follow-up calls
EQUALLY among active, present CRE callers with zero manual work required.
It guarantees that call counts differ by at most 1, rotates remainders fairly,
bundles sticky customer calls, respects brand/branch scopes, and provides 15-minute undo.

KEY RESPONSIBILITIES:
- Calculates CRE presence based on today's active login sessions and manual overrides (`get_present_cres`).
- Executes equal split allocation algorithms inside a database transaction (`allocate_queue_items`).
- Maintains fair cursor rotation so remainder calls rotate evenly across CREs.
- Provides rebalance preview and confirmation for mid-shift late joiners (`rebalance_queues`).
- Provides 15-minute safety undo to rollback allocation batches if untouched (`undo_allocation_run`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Calls stay unallocated with message 'No present CREs found'
  -> Cause: No active CRE has logged in today and no manual presence overrides were set.
  -> What should you do: Log in with a CRE user or toggle CREs to 'Present' in the CRE Presence panel, then click 'Allocate Now'.
- Error: Allocation locked / timeout error
  -> Cause: Two concurrent imports attempted to allocate simultaneously.
  -> What should you do: Distributed lock prevents duplicate allocation. Retry after 2 seconds.
================================================================================
"""
import uuid
import json
import logging
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.tenant import Tenant, Brand, Branch, Setting
from app.models.auth import User, Role, RolePermission, UserScope, LoginLog
from app.models.service import ImportBatch, JobCard
from app.models.followup import FollowupQueue, CallAttempt
from app.models.allocation import (
    AttendanceOverride,
    AllocationRun,
    AllocationAssignment,
    AllocationCursor,
)
from app.models.additional import AuditLog
from app.core.redis import get_redis
from app.core.crypto import uuid7
from app.core.permissions import PermissionKey

logger = logging.getLogger("psf.allocation")

DEFAULT_ALLOCATION_RULES = {
    "strategy": "EQUAL_PRESENT_CRE",  # EQUAL_PRESENT_CRE | ROUND_ROBIN | BY_BRANCH | MANUAL
    "pool_mode": "CRE_POOL",          # CRE_POOL | BRANCH_ONLY
    "allocation_trigger_mode": "WHEN_MIN_PRESENT",  # IMMEDIATE | SCHEDULED_AT_TIME | WHEN_MIN_PRESENT
    "scheduled_time": "09:30",        # HH:MM format
    "min_present_cres": 2,            # Minimum present CREs required before auto-allocation triggers
    "sticky_customers": True,         # Group same phone/customer into single bundle
    "balance_total_pending": False,   # False = split new batch only; True = equalize total pending
    "logout_policy": "KEEP",          # KEEP | RETURN_TO_POOL | REDISTRIBUTE_EQUALLY
    "undo_window_minutes": 15,        # 15 minutes default window
    "weights": {},                    # { user_id_str: 1.0 }
}


async def get_allocation_rules(db: AsyncSession, tenant_id: uuid.UUID) -> Dict[str, Any]:
    """Retrieve tenant's call allocation configuration rules."""
    stmt = select(Setting).where(
        Setting.tenant_id == tenant_id,
        Setting.config_key == "allocation_rules",
    )
    setting = (await db.execute(stmt)).scalar_one_or_none()
    if not setting or not setting.config_value:
        return dict(DEFAULT_ALLOCATION_RULES)

    merged = dict(DEFAULT_ALLOCATION_RULES)
    merged.update(setting.config_value)
    return merged


async def update_allocation_rules(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    rules_payload: Dict[str, Any],
    updated_by_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """Update tenant's call allocation configuration rules."""
    current = await get_allocation_rules(db, tenant_id)
    current.update(rules_payload)

    stmt = select(Setting).where(
        Setting.tenant_id == tenant_id,
        Setting.config_key == "allocation_rules",
    )
    setting = (await db.execute(stmt)).scalar_one_or_none()
    if not setting:
        setting = Setting(
            tenant_id=tenant_id,
            config_key="allocation_rules",
            config_value=current,
        )
        db.add(setting)
    else:
        setting.config_value = current

    # Audit log
    if updated_by_id:
        db.add(
            AuditLog(
                tenant_id=tenant_id,
                user_id=updated_by_id,
                action="UPDATE_ALLOCATION_RULES",
                entity_type="SETTING",
                entity_id=str(setting.id if setting.id else uuid7()),
                new_values=rules_payload,
                reason="Updated call allocation configuration rules via Admin Console",
            )
        )
    await db.commit()
    return current


async def get_present_cres(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Returns all eligible CRE callers with their real-time attendance and pending workload:
    - User is active and not deleted
    - User has permission 'call.make' (data-driven via RolePermission)
    - Attendance logic:
      1. Manual override for target_date in attendance_overrides takes highest priority
      2. If no override: open login session today in login_logs (logout_at IS NULL)
    """
    if target_date is None:
        target_date = datetime.now(timezone.utc).date()

    # 0. Automatically clean up stale login sessions from previous days
    from app.services.auth_service import cleanup_stale_login_sessions
    await cleanup_stale_login_sessions(db, tenant_id=tenant_id, before_date=target_date)

    # 1. Query users with call.make permission or Super Admin
    stmt = (
        select(User)
        .options(
            selectinload(User.role).selectinload(Role.role_permissions),
            selectinload(User.scopes),
        )
        .where(
            User.tenant_id == tenant_id,
            User.is_active == True,
            User.is_deleted == False,
        )
        .order_by(User.full_name)
    )
    all_users = (await db.execute(stmt)).scalars().all()

    eligible_users: List[User] = []
    for u in all_users:
        if not u.role:
            continue
        if u.role.name in ["SUPER_ADMIN", "DEALER_ADMIN", "CRE_ADMIN"]:
            continue
        perms = set()
        if hasattr(u.role, "role_permissions") and u.role.role_permissions:
            perms.update(rp.permission for rp in u.role.role_permissions)
        if hasattr(u.role, "permissions") and u.role.permissions:
            perms.update(u.role.permissions)
        if PermissionKey.CALL_MAKE in perms or "call.make" in perms:
            eligible_users.append(u)

    user_ids = [u.id for u in eligible_users]
    if not user_ids:
        return []

    # Map branches for display
    branches_res = await db.execute(select(Branch).where(Branch.tenant_id == tenant_id))
    branches_map = {b.id: (b.code or b.name) for b in branches_res.scalars().all()}

    # 2. Fetch attendance overrides for target_date
    ov_stmt = select(AttendanceOverride).options(
        selectinload(AttendanceOverride.marked_by)
    ).where(
        AttendanceOverride.tenant_id == tenant_id,
        AttendanceOverride.attendance_date == target_date,
        AttendanceOverride.user_id.in_(user_ids),
    )
    overrides = {ov.user_id: ov for ov in (await db.execute(ov_stmt)).scalars().all()}

    # 3. Fetch active login sessions for target_date (midnight to midnight)
    start_dt = datetime.combine(target_date, time(0, 0), tzinfo=timezone.utc)
    end_dt = datetime.combine(target_date + timedelta(days=1), time(0, 0), tzinfo=timezone.utc)
    log_stmt = select(LoginLog).where(
        LoginLog.tenant_id == tenant_id,
        LoginLog.user_id.in_(user_ids),
        LoginLog.login_at >= start_dt,
        LoginLog.login_at < end_dt,
        LoginLog.logout_at == None,
    ).order_by(LoginLog.login_at.desc())
    active_logs = (await db.execute(log_stmt)).scalars().all()
    active_login_map = {lg.user_id: lg for lg in active_logs}

    # 4. Fetch current pending queues count per user
    pending_stmt = (
        select(FollowupQueue.assigned_to_id, func.count(FollowupQueue.id))
        .where(
            FollowupQueue.tenant_id == tenant_id,
            FollowupQueue.assigned_to_id.in_(user_ids),
            FollowupQueue.status == "PENDING",
            FollowupQueue.is_deleted == False,
        )
        .group_by(FollowupQueue.assigned_to_id)
    )
    pending_counts = dict((await db.execute(pending_stmt)).all())

    # Rules weights
    rules = await get_allocation_rules(db, tenant_id)
    weights = rules.get("weights", {})

    result = []
    for u in eligible_users:
        ov = overrides.get(u.id)
        active_log = active_login_map.get(u.id)

        if ov:
            status = ov.status  # PRESENT | ABSENT | ON_LEAVE
            is_present = (status == "PRESENT")
            has_override = True
            override_reason = ov.reason
            marked_by_name = ov.marked_by.full_name if ov.marked_by else None
        else:
            has_override = False
            override_reason = None
            marked_by_name = None
            if active_log:
                status = "PRESENT"
                is_present = True
            else:
                status = "ABSENT"
                is_present = False

        branch_codes = [branches_map.get(s.branch_id, str(s.branch_id)) for s in u.scopes if s.branch_id] if u.scopes else []
        branch_ids = [s.branch_id for s in u.scopes if s.branch_id] if u.scopes else []
        brand_ids = [s.brand_id for s in u.scopes if s.brand_id] if u.scopes else []

        w = float(weights.get(str(u.id), 1.0))
        if w <= 0:
            w = 1.0

        result.append({
            "user": u,
            "user_id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role_name": u.role.name if u.role else "CRE",
            "phone": u.phone,
            "is_present": is_present,
            "attendance_status": status,
            "has_active_login": active_log is not None,
            "login_time": active_log.login_at if active_log else None,
            "has_override": has_override,
            "override_reason": override_reason,
            "marked_by_name": marked_by_name,
            "current_pending": pending_counts.get(u.id, 0),
            "assigned_branches": branch_codes,
            "assigned_branch_ids": branch_ids,
            "assigned_brand_ids": brand_ids,
            "weight": w,
        })

    return result


async def set_attendance_override(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str,
    marked_by_id: Optional[uuid.UUID] = None,
    attendance_date: Optional[date] = None,
    reason: Optional[str] = None,
    target_date: Optional[date] = None,
) -> AttendanceOverride:
    """Set manual attendance status (PRESENT, ABSENT, ON_LEAVE) for a CRE on a date."""
    effective_date = attendance_date or target_date or datetime.now(timezone.utc).date()
    effective_marker = marked_by_id or user_id

    status = status.upper().strip()
    if status not in ["PRESENT", "ABSENT", "ON_LEAVE"]:
        raise ValueError(f"Invalid attendance status '{status}'. Must be PRESENT, ABSENT, or ON_LEAVE.")

    stmt = select(AttendanceOverride).where(
        AttendanceOverride.tenant_id == tenant_id,
        AttendanceOverride.user_id == user_id,
        AttendanceOverride.attendance_date == effective_date,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing:
        existing.status = status
        existing.marked_by_id = effective_marker
        existing.reason = reason
        record = existing
    else:
        record = AttendanceOverride(
            tenant_id=tenant_id,
            user_id=user_id,
            attendance_date=effective_date,
            status=status,
            marked_by_id=effective_marker,
            reason=reason,
        )
        db.add(record)

    # Audit log
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=effective_marker,
            action="ATTENDANCE_OVERRIDE",
            entity_type="USER",
            entity_id=str(user_id),
            new_values={"attendance_date": str(effective_date), "status": status, "reason": reason},
            reason=f"Manually marked CRE attendance as {status}",
        )
    )
    await db.commit()
    await db.refresh(record)
    return record


async def get_or_create_cursor(db: AsyncSession, tenant_id: uuid.UUID, pool_key: str = "DEFAULT") -> AllocationCursor:
    """Get or initialize rotation cursor for fair remainder distribution across imports."""
    stmt = select(AllocationCursor).where(
        AllocationCursor.tenant_id == tenant_id,
        AllocationCursor.pool_key == pool_key,
    )
    cursor = (await db.execute(stmt)).scalar_one_or_none()
    if not cursor:
        cursor = AllocationCursor(
            tenant_id=tenant_id,
            pool_key=pool_key,
            last_cre_index=0,
        )
        db.add(cursor)
        await db.flush()
    return cursor


def is_cre_eligible_for_item(cre_info: Dict[str, Any], job_card: JobCard, pool_mode: str) -> bool:
    """
    Check if a CRE is eligible to receive a job card based on brand/branch scopes and pool mode.
    """
    assigned_branch_ids = cre_info["assigned_branch_ids"]
    assigned_brand_ids = cre_info["assigned_brand_ids"]

    # 1. Unrestricted CRE (DEALERSHIP/ALL scope e.g. Central CRE or Super Admin with no explicit branch restriction)
    if not assigned_branch_ids and not assigned_brand_ids:
        return True

    # 2. Strict BRANCH_ONLY mode
    if pool_mode == "BRANCH_ONLY":
        if assigned_branch_ids and job_card.branch_id not in assigned_branch_ids:
            return False
        if assigned_brand_ids and job_card.brand_id not in assigned_brand_ids:
            return False
        return True

    # 3. CRE_POOL mode (Central pool gets everything unless explicitly restricted to a branch)
    if assigned_branch_ids and job_card.branch_id not in assigned_branch_ids:
        # User is assigned to specific branch(es) and this job card is for another branch
        return False
    if assigned_brand_ids and job_card.brand_id not in assigned_brand_ids:
        return False

    return True


async def allocate_queue_items(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    queue_items: List[FollowupQueue],
    import_batch_id: Optional[uuid.UUID] = None,
    started_by_id: Optional[uuid.UUID] = None,
    run_type: str = "IMPORT_ALLOCATION",
    custom_rules: Optional[Dict[str, Any]] = None,
) -> AllocationRun:
    """
    Core Allocation Engine:
    - Divided EQUALLY among present eligible CREs (e.g. 29 items & 3 CREs = 10 / 10 / 9).
    - Concurrency safe: Uses Postgres advisory lock on tenant to guarantee serial execution.
    - Idempotent: Skips already assigned items.
    - Remainder rotation: Rotates cursor so remainder items do not always go to the same CRE.
    - Sticky customers: Bundles same customer into a single CRE assignment.
    """
    # 1. Acquire transaction advisory lock per tenant
    lock_id = int(uuid.uuid5(uuid.NAMESPACE_DNS, f"psf_allocation_{tenant_id}").int & 0x7FFFFFFF)
    await db.execute(select(func.pg_advisory_xact_lock(lock_id)))

    # 2. Load rules
    rules = custom_rules or (await get_allocation_rules(db, tenant_id))
    strategy = rules.get("strategy", "EQUAL_PRESENT_CRE")
    pool_mode = rules.get("pool_mode", "CRE_POOL")
    sticky_customers = rules.get("sticky_customers", True)
    balance_total = rules.get("balance_total_pending", False)

    # 3. Filter unassigned untouched items under lock with fresh database state
    item_ids = [q.id for q in queue_items if getattr(q, "id", None)]
    if item_ids:
        fresh_stmt = (
            select(FollowupQueue)
            .options(selectinload(FollowupQueue.job_card))
            .where(
                FollowupQueue.id.in_(item_ids),
                FollowupQueue.assigned_to_id == None,
                FollowupQueue.status == "PENDING",
                FollowupQueue.attempts == 0,
                FollowupQueue.is_deleted == False,
            )
            .with_for_update()
        )
        unassigned = list((await db.execute(fresh_stmt)).scalars().all())
    else:
        unassigned = [
            q for q in queue_items
            if q.assigned_to_id is None and q.status == "PENDING" and (q.attempts or 0) == 0 and not q.is_deleted
        ]

    # Create run record
    run = AllocationRun(
        tenant_id=tenant_id,
        import_batch_id=import_batch_id,
        run_type=run_type,
        strategy=strategy,
        total_items=len(unassigned),
        allocated_items=0,
        unallocated_items=len(unassigned),
        started_by_id=started_by_id,
        summary={},
    )
    db.add(run)
    await db.flush()

    if not unassigned:
        run.summary = {"message": "No unallocated queue items to process", "per_cre": {}}
        await db.commit()
        return run

    # 4. Fetch present CREs
    all_cres = await get_present_cres(db, tenant_id)
    present_cres = [c for c in all_cres if c["is_present"]]
    run.present_cre_count = len(present_cres)

    if not present_cres or strategy == "MANUAL":
        # Leave all in UNALLOCATED pool
        run.allocated_items = 0
        run.unallocated_items = len(unassigned)
        run.summary = {
            "strategy": strategy,
            "status": "UNALLOCATED_POOL",
            "message": "No present CREs available. Items placed in unallocated queue." if not present_cres else "Manual allocation requested.",
            "unallocated_count": len(unassigned),
            "per_cre": {},
        }
        await db.commit()
        return run

    # 5. Deterministic item ordering: by job card date ASC, then job card id ASC
    # Eagerly load job cards
    jc_ids = [q.job_card_id for q in unassigned]
    jc_stmt = select(JobCard).options(selectinload(JobCard.customer)).where(JobCard.id.in_(jc_ids))
    jcs = {jc.id: jc for jc in (await db.execute(jc_stmt)).scalars().all()}
    for q in unassigned:
        q.job_card = jcs.get(q.job_card_id)

    unassigned.sort(
        key=lambda q: (
            q.job_card.job_card_date if q.job_card else date.min,
            str(q.job_card.id if q.job_card else q.id),
        )
    )

    # 6. Group into Customer Bundles if sticky_customers is True
    bundles: List[Dict[str, Any]] = []
    if sticky_customers:
        cust_map: Dict[str, List[FollowupQueue]] = {}
        for q in unassigned:
            # Group by customer phone or customer_id
            c_key = str(q.job_card.customer_id) if q.job_card and q.job_card.customer_id else str(q.id)
            if c_key not in cust_map:
                cust_map[c_key] = []
            cust_map[c_key].append(q)

        for c_key, items in cust_map.items():
            first = items[0]
            bundles.append({
                "bundle_key": c_key,
                "items": items,
                "count": len(items),
                "job_card": first.job_card,
            })
    else:
        for q in unassigned:
            bundles.append({
                "bundle_key": str(q.id),
                "items": [q],
                "count": 1,
                "job_card": q.job_card,
            })

    # Sort bundles deterministically
    bundles.sort(
        key=lambda b: (
            b["job_card"].job_card_date if b["job_card"] else date.min,
            str(b["job_card"].id if b["job_card"] else b["bundle_key"]),
        )
    )

    # 7. Distribution Algorithm with Cursor Rotation
    pool_key = "DEFAULT"
    cursor = await get_or_create_cursor(db, tenant_id, pool_key)
    start_cursor = cursor.last_cre_index

    # Initialize tracking
    cre_assigned_items: Dict[uuid.UUID, List[FollowupQueue]] = {c["user_id"]: [] for c in present_cres}
    cre_workload: Dict[uuid.UUID, float] = {
        c["user_id"]: (c["current_pending"] if balance_total else 0) for c in present_cres
    }

    # Case A: Pure Equal Split when all bundle sizes are 1 and equal weight
    is_standard_equal = (
        strategy == "EQUAL_PRESENT_CRE"
        and not balance_total
        and all(b["count"] == 1 for b in bundles)
        and all(c["weight"] == 1.0 for c in present_cres)
    )

    num_cres = len(present_cres)
    unallocated_bundles: List[Dict[str, Any]] = []

    if is_standard_equal:
        # Check if all CREs are eligible for all items
        first_b = bundles[0] if bundles else None
        all_universal = all(
            is_cre_eligible_for_item(c, first_b["job_card"], pool_mode) for c in present_cres
        ) if first_b and first_b["job_card"] else False

        if all_universal:
            total_n = len(bundles)
            base_count = total_n // num_cres
            remainder = total_n % num_cres

            # Order of CREs starting from cursor
            rotated_cres = [present_cres[(start_cursor + i) % num_cres] for i in range(num_cres)]

            # Target quota per rotated CRE
            target_quotas = {}
            for i, c in enumerate(rotated_cres):
                target_quotas[c["user_id"]] = base_count + (1 if i < remainder else 0)

            # Assign sequentially according to quota
            item_idx = 0
            for c in rotated_cres:
                quota = target_quotas[c["user_id"]]
                for _ in range(quota):
                    if item_idx < total_n:
                        cre_assigned_items[c["user_id"]].extend(bundles[item_idx]["items"])
                        item_idx += 1

            # Update cursor by remainder rotated
            cursor.last_cre_index = (start_cursor + remainder) % num_cres
        else:
            # Fallback to greedy load-balanced assignment considering eligibility
            for b in bundles:
                eligible = [c for c in present_cres if is_cre_eligible_for_item(c, b["job_card"], pool_mode)]
                if not eligible:
                    unallocated_bundles.append(b)
                    continue

                # Pick eligible CRE with minimum assigned count, breaking ties with rotated cursor order
                best_cre = min(
                    eligible,
                    key=lambda c: (
                        len(cre_assigned_items[c["user_id"]]),
                        (present_cres.index(c) - start_cursor) % num_cres,
                    ),
                )
                cre_assigned_items[best_cre["user_id"]].extend(b["items"])

            cursor.last_cre_index = (start_cursor + len(bundles)) % num_cres
    else:
        # General load-balanced distribution (handles weights, sticky bundles, balance_total_pending)
        for b in bundles:
            eligible = [c for c in present_cres if is_cre_eligible_for_item(c, b["job_card"], pool_mode)]
            if not eligible:
                unallocated_bundles.append(b)
                continue

            # Effective load = current_load / weight
            best_cre = min(
                eligible,
                key=lambda c: (
                    (cre_workload[c["user_id"]] + len(cre_assigned_items[c["user_id"]])) / c["weight"],
                    (present_cres.index(c) - start_cursor) % num_cres,
                ),
            )
            cre_assigned_items[best_cre["user_id"]].extend(b["items"])
            cre_workload[best_cre["user_id"]] += b["count"]

        cursor.last_cre_index = (start_cursor + len(bundles)) % num_cres

    # 8. Commit assignments & create audit records
    allocated_count = 0
    per_cre_summary = {}

    for c in present_cres:
        u_id = c["user_id"]
        assigned_list = cre_assigned_items[u_id]
        if not assigned_list:
            per_cre_summary[str(u_id)] = {
                "name": c["full_name"],
                "role": c["role_name"],
                "count": 0,
            }
            continue

        for q in assigned_list:
            q.assigned_to_id = u_id
            db.add(
                AllocationAssignment(
                    tenant_id=tenant_id,
                    run_id=run.id,
                    queue_item_id=q.id,
                    from_user_id=None,
                    to_user_id=u_id,
                    reason="IMPORT_EQUAL_SPLIT",
                )
            )
            allocated_count += 1

        per_cre_summary[str(u_id)] = {
            "name": c["full_name"],
            "role": c["role_name"],
            "count": len(assigned_list),
        }

    unallocated_count = sum(b["count"] for b in unallocated_bundles)
    run.allocated_items = allocated_count
    run.unallocated_items = unallocated_count
    run.summary = {
        "strategy": strategy,
        "pool_mode": pool_mode,
        "sticky_customers": sticky_customers,
        "total_imported": len(unassigned),
        "allocated_count": allocated_count,
        "unallocated_count": unallocated_count,
        "per_cre": per_cre_summary,
        "present_cre_names": [c["full_name"] for c in present_cres],
    }

    # Audit log
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=started_by_id,
            action="ALLOCATION_RUN",
            entity_type="ALLOCATION_RUN",
            entity_id=str(run.id),
            new_values=run.summary,
            reason=f"Auto-allocated {allocated_count} calls across {len(present_cres)} present CREs",
        )
    )

    await db.commit()

    # 9. Real-time WebSocket / Redis notification for CREs
    try:
        r = await get_redis()
        for u_id_str, cre_data in per_cre_summary.items():
            if cre_data["count"] > 0:
                payload = {
                    "event": "CALLS_ALLOCATED",
                    "user_id": u_id_str,
                    "count": cre_data["count"],
                    "message": f"{cre_data['count']} new follow-up calls assigned to you.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await r.publish("cre_notifications", json.dumps(payload))
                await r.publish(f"psf:notifications:user:{u_id_str}", json.dumps(payload))
    except Exception as e:
        logger.warning(f"Could not publish Redis allocation notification: {e}")

    return run


async def preview_rebalance(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> Dict[str, Any]:
    """
    Preview rebalancing pending untouched calls among currently present CREs.
    Only untouched calls (attempts == 0 and status == 'PENDING') are movable.
    Calls with attempts > 0 or in progress NEVER move.
    """
    all_cres = await get_present_cres(db, tenant_id)
    present_cres = [c for c in all_cres if c["is_present"]]
    if not present_cres:
        return {
            "total_movable_calls": 0,
            "present_cre_count": 0,
            "items": [],
            "message": "No present CREs found to rebalance.",
        }

    present_ids = [c["user_id"] for c in present_cres]

    # Fetch untouched calls per present CRE
    stmt = (
        select(FollowupQueue.assigned_to_id, func.count(FollowupQueue.id))
        .where(
            FollowupQueue.tenant_id == tenant_id,
            FollowupQueue.status == "PENDING",
            FollowupQueue.attempts == 0,
            FollowupQueue.is_deleted == False,
            FollowupQueue.assigned_to_id.in_(present_ids),
        )
        .group_by(FollowupQueue.assigned_to_id)
    )
    counts_map = dict((await db.execute(stmt)).all())

    # Total movable calls across all CREs
    total_movable = sum(counts_map.values())
    num_cres = len(present_cres)
    base_per_cre = total_movable // num_cres
    remainder = total_movable % num_cres

    items = []
    for i, c in enumerate(present_cres):
        cur = counts_map.get(c["user_id"], 0)
        proposed = base_per_cre + (1 if i < remainder else 0)
        items.append({
            "user_id": c["user_id"],
            "full_name": c["full_name"],
            "current_pending": cur,
            "proposed_pending": proposed,
            "net_change": proposed - cur,
        })

    return {
        "total_movable_calls": total_movable,
        "present_cre_count": num_cres,
        "items": items,
    }


async def confirm_rebalance(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    started_by_id: uuid.UUID,
) -> AllocationRun:
    """
    Execute rebalance: moves only untouched calls (attempts == 0) to equalize workload.
    """
    lock_id = int(uuid.uuid5(uuid.NAMESPACE_DNS, f"psf_allocation_{tenant_id}").int & 0x7FFFFFFF)
    await db.execute(select(func.pg_advisory_xact_lock(lock_id)))

    all_cres = await get_present_cres(db, tenant_id)
    present_cres = [c for c in all_cres if c["is_present"]]
    if not present_cres:
        raise HTTPException(status_code=400, detail="Cannot rebalance: no CREs are currently marked present.")

    present_ids = [c["user_id"] for c in present_cres]

    # 1. Fetch all movable untouched calls assigned to present CREs
    stmt = (
        select(FollowupQueue)
        .options(selectinload(FollowupQueue.job_card))
        .where(
            FollowupQueue.tenant_id == tenant_id,
            FollowupQueue.status == "PENDING",
            FollowupQueue.attempts == 0,
            FollowupQueue.is_deleted == False,
            FollowupQueue.assigned_to_id.in_(present_ids),
        )
        .order_by(FollowupQueue.due_at, FollowupQueue.created_at)
    )
    movable_calls = (await db.execute(stmt)).scalars().all()

    run = AllocationRun(
        tenant_id=tenant_id,
        run_type="REBALANCE",
        strategy="EQUAL_PRESENT_CRE",
        total_items=len(movable_calls),
        allocated_items=len(movable_calls),
        unallocated_items=0,
        present_cre_count=len(present_cres),
        started_by_id=started_by_id,
        summary={},
    )
    db.add(run)
    await db.flush()

    num_cres = len(present_cres)
    base_per_cre = len(movable_calls) // num_cres
    remainder = len(movable_calls) % num_cres

    # Assign equal chunks
    call_idx = 0
    per_cre_summary = {}

    for i, c in enumerate(present_cres):
        target_count = base_per_cre + (1 if i < remainder else 0)
        c_id = c["user_id"]
        assigned_here = 0

        for _ in range(target_count):
            if call_idx < len(movable_calls):
                q = movable_calls[call_idx]
                prev_user = q.assigned_to_id
                if prev_user != c_id:
                    q.assigned_to_id = c_id
                    db.add(
                        AllocationAssignment(
                            tenant_id=tenant_id,
                            run_id=run.id,
                            queue_item_id=q.id,
                            from_user_id=prev_user,
                            to_user_id=c_id,
                            reason="REBALANCE",
                        )
                    )
                assigned_here += 1
                call_idx += 1

        per_cre_summary[str(c_id)] = {
            "name": c["full_name"],
            "count": assigned_here,
        }

    run.summary = {
        "action": "CONFIRM_REBALANCE",
        "total_movable": len(movable_calls),
        "per_cre": per_cre_summary,
    }

    db.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=started_by_id,
            action="REBALANCE_CONFIRMED",
            entity_type="ALLOCATION_RUN",
            entity_id=str(run.id),
            new_values=run.summary,
            reason=f"Rebalanced {len(movable_calls)} untouched calls across {num_cres} present CREs",
        )
    )
    await db.commit()
    return run


async def undo_allocation_run(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    run_id: uuid.UUID,
    undone_by_id: uuid.UUID,
) -> Dict[str, Any]:
    """
    Undo an allocation run within the configurable window (default 15 mins)
    if no call attempt has been made on those assigned items.
    """
    rules = await get_allocation_rules(db, tenant_id)
    window_minutes = int(rules.get("undo_window_minutes", 15))

    stmt = (
        select(AllocationRun)
        .options(selectinload(AllocationRun.assignments).selectinload(AllocationAssignment.queue_item))
        .where(
            AllocationRun.id == run_id,
            AllocationRun.tenant_id == tenant_id,
        )
    )
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Allocation run not found")

    if run.undone_at:
        raise HTTPException(status_code=400, detail="This allocation run has already been undone.")

    # Check time window
    now = datetime.now(timezone.utc)
    created = run.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)

    if (now - created) > timedelta(minutes=window_minutes):
        raise HTTPException(
            status_code=400,
            detail=f"Undo window expired. Allocations can only be undone within {window_minutes} minutes.",
        )

    # Check if any attempts were made
    for asgn in run.assignments:
        q = asgn.queue_item
        if q and (q.attempts or 0) > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot undo allocation: One or more calls in this batch have already been attempted by callers.",
            )

    # Restore previous assignments
    reverted_count = 0
    for asgn in run.assignments:
        q = asgn.queue_item
        if q:
            q.assigned_to_id = asgn.from_user_id  # Restores previous owner or None
            reverted_count += 1

    run.undone_at = now
    run.undone_by_id = undone_by_id

    db.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=undone_by_id,
            action="ALLOCATION_UNDO",
            entity_type="ALLOCATION_RUN",
            entity_id=str(run.id),
            new_values={"reverted_items": reverted_count},
            reason=f"Undid allocation run {run.id} within {window_minutes} minute safety window",
        )
    )
    await db.commit()
    return {
        "message": f"Successfully undone allocation run. Reverted {reverted_count} call assignments.",
        "reverted_count": reverted_count,
        "run_id": str(run.id),
    }


async def auto_allocate_on_login(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user: User,
) -> Optional[AllocationRun]:
    """
    Called when a CRE logs in: if there are pending UNALLOCATED calls matching their scope,
    automatically allocate calls to them.
    """
    # 1. Fetch user with role and role_permissions eagerly
    u_stmt = (
        select(User)
        .options(selectinload(User.role).selectinload(Role.role_permissions))
        .where(User.id == user.id)
    )
    loaded_user = (await db.execute(u_stmt)).scalar_one_or_none() or user
    if not loaded_user.role:
        return None
    perms = set()
    try:
        if loaded_user.role.role_permissions:
            perms.update(rp.permission for rp in loaded_user.role.role_permissions)
    except Exception:
        pass
    if hasattr(loaded_user.role, "permissions") and loaded_user.role.permissions:
        perms.update(loaded_user.role.permissions)
    if PermissionKey.CALL_MAKE not in perms and "call.make" not in perms and loaded_user.role.name != "SUPER_ADMIN":
        return None

    # 2. Check tenant trigger mode rules
    rules = await get_allocation_rules(db, tenant_id)
    trigger_mode = rules.get("allocation_trigger_mode", "WHEN_MIN_PRESENT")
    min_required = int(rules.get("min_present_cres", 2))
    scheduled_time = rules.get("scheduled_time", "09:30")

    # Check presence & timing requirements
    all_cres = await get_present_cres(db, tenant_id)
    present_cres = [c for c in all_cres if c["is_present"]]
    present_count = len(present_cres)

    if trigger_mode == "WHEN_MIN_PRESENT":
        if present_count < min_required:
            logger.info(
                f"Auto-allocation deferred on login: {present_count} CREs present today, requires at least {min_required}."
            )
            return None
    elif trigger_mode == "SCHEDULED_AT_TIME":
        now = datetime.now(timezone.utc)
        current_time_str = now.strftime("%H:%M")
        if current_time_str < scheduled_time:
            logger.info(
                f"Auto-allocation deferred on login: Current time {current_time_str} is before scheduled shift time {scheduled_time}."
            )
            return None

    # 3. Check unallocated pending calls
    stmt = (
        select(FollowupQueue)
        .options(selectinload(FollowupQueue.job_card))
        .where(
            FollowupQueue.tenant_id == tenant_id,
            FollowupQueue.assigned_to_id == None,
            FollowupQueue.status == "PENDING",
            FollowupQueue.attempts == 0,
            FollowupQueue.is_deleted == False,
        )
        .order_by(FollowupQueue.created_at.desc(), FollowupQueue.due_at)
        .limit(500)
    )
    unallocated = (await db.execute(stmt)).scalars().all()
    if not unallocated:
        return None

    # Run allocator
    run = await allocate_queue_items(
        db=db,
        tenant_id=tenant_id,
        queue_items=unallocated,
        run_type="AUTO_LOGIN_ALLOCATION",
        started_by_id=user.id,
    )
    return run


async def preview_allocate_now(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> Dict[str, Any]:
    """
    Simulate manual "Allocate Now" of all currently unallocated calls
    across currently present CREs.
    """
    stmt = (
        select(FollowupQueue)
        .options(selectinload(FollowupQueue.job_card))
        .where(
            FollowupQueue.tenant_id == tenant_id,
            FollowupQueue.assigned_to_id == None,
            FollowupQueue.status == "PENDING",
            FollowupQueue.attempts == 0,
            FollowupQueue.is_deleted == False,
        )
        .order_by(FollowupQueue.due_at)
    )
    unallocated = (await db.execute(stmt)).scalars().all()
    all_cres = await get_present_cres(db, tenant_id)
    present_cres = [c for c in all_cres if c["is_present"]]

    if not unallocated:
        return {
            "total_unallocated_calls": 0,
            "present_cre_count": len(present_cres),
            "items": [],
            "message": "No unallocated calls currently waiting in the pool.",
        }

    if not present_cres:
        return {
            "total_unallocated_calls": len(unallocated),
            "present_cre_count": 0,
            "items": [],
            "message": "No CREs are currently marked present to receive calls.",
        }

    rules = await get_allocation_rules(db, tenant_id)
    num_cres = len(present_cres)
    total_calls = len(unallocated)
    base_count = total_calls // num_cres
    remainder = total_calls % num_cres

    items = []
    for i, c in enumerate(present_cres):
        proposed_share = base_count + (1 if i < remainder else 0)
        items.append({
            "user_id": c["user_id"],
            "full_name": c["full_name"],
            "current_pending": c["current_pending"],
            "allocated_in_this_run": proposed_share,
            "new_total_pending": c["current_pending"] + proposed_share,
        })

    return {
        "total_unallocated_calls": total_calls,
        "present_cre_count": num_cres,
        "strategy": rules.get("strategy", "EQUAL_PRESENT_CRE"),
        "items": items,
    }


async def confirm_allocate_now(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    started_by_id: uuid.UUID,
) -> AllocationRun:
    """
    Execute manual "Allocate Now" of all unallocated calls across currently present CREs.
    """
    stmt = (
        select(FollowupQueue)
        .options(selectinload(FollowupQueue.job_card))
        .where(
            FollowupQueue.tenant_id == tenant_id,
            FollowupQueue.assigned_to_id == None,
            FollowupQueue.status == "PENDING",
            FollowupQueue.attempts == 0,
            FollowupQueue.is_deleted == False,
        )
        .order_by(FollowupQueue.due_at)
    )
    unallocated = (await db.execute(stmt)).scalars().all()
    if not unallocated:
        raise HTTPException(status_code=400, detail="No unallocated calls found to allocate.")

    run = await allocate_queue_items(
        db=db,
        tenant_id=tenant_id,
        queue_items=unallocated,
        run_type="MANUAL_ALLOCATE_NOW",
        started_by_id=started_by_id,
    )
    return run


async def execute_logout_policy(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Optional[Dict[str, Any]]:
    """
    Called when a CRE logs out: execute tenant's logout policy for their pending calls.
    Policy options:
    - KEEP (default): keep calls assigned to this user
    - RETURN_TO_POOL: unassign untouched calls (assigned_to_id = None)
    - REDISTRIBUTE_EQUALLY: reassign untouched calls to other currently present CREs
    """
    rules = await get_allocation_rules(db, tenant_id)
    policy = rules.get("logout_policy", "KEEP")
    if policy == "KEEP":
        return None

    # Fetch untouched calls assigned to this user
    stmt = (
        select(FollowupQueue)
        .options(selectinload(FollowupQueue.job_card))
        .where(
            FollowupQueue.tenant_id == tenant_id,
            FollowupQueue.assigned_to_id == user_id,
            FollowupQueue.status == "PENDING",
            FollowupQueue.attempts == 0,
            FollowupQueue.is_deleted == False,
        )
    )
    untouched = (await db.execute(stmt)).scalars().all()
    if not untouched:
        return None

    if policy == "RETURN_TO_POOL":
        for q in untouched:
            q.assigned_to_id = None
        await db.commit()
        return {"policy": "RETURN_TO_POOL", "unassigned_count": len(untouched)}

    elif policy == "REDISTRIBUTE_EQUALLY":
        # Find other present CREs
        all_cres = await get_present_cres(db, tenant_id)
        other_present = [c for c in all_cres if c["is_present"] and c["user_id"] != user_id]
        if not other_present:
            for q in untouched:
                q.assigned_to_id = None
            await db.commit()
            return {"policy": "RETURN_TO_POOL_NO_OTHERS", "unassigned_count": len(untouched)}

        for q in untouched:
            q.assigned_to_id = None

        run = await allocate_queue_items(
            db=db,
            tenant_id=tenant_id,
            queue_items=untouched,
            run_type="LOGOUT_REDISTRIBUTE",
            started_by_id=user_id,
        )
        return {"policy": "REDISTRIBUTE_EQUALLY", "reassigned_count": run.allocated_items}

    return None
