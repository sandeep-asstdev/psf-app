"""
================================================================================
FILE PURPOSE: Role-Based Access Control (RBAC) & Data Scoping Engine.
This file defines all system permission keys (like `call.view`, `jobcard.import`, `complaint.close`)
and handles multi-level data scoping (ALL, BRAND, BRANCH, OWN).
It controls which rows a user is allowed to see in SQL queries (e.g., CRE only sees OWN calls).

KEY RESPONSIBILITIES:
- Declares PermissionKey constants for all system actions.
- Declares DataScope levels: ALL (L1/Super Admin), BRAND (L2/Brand Manager), BRANCH (L3/Branch Manager), OWN (L4/CRE).
- Computes effective permissions for a user including tenant roles and custom user scopes.
- Provides `apply_data_scope()` which dynamically filters SQLAlchemy queries based on the user's role.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: HTTP 403 Forbidden: 'Insufficient permissions'
  -> Cause: The logged-in user's role lacks the required permission key for that endpoint.
  -> What should you do: Check the user's role in the Enterprise Admin Console (Role Matrix) or log in with an account having appropriate privileges (e.g. Super Admin or CRE Admin).
- Error: A CRE user sees other CREs' calls or an Admin sees zero calls
  -> Cause: Data scoping logic filter was incorrectly applied or user scopes are missing.
  -> What should you do: Inspect `apply_data_scope` and confirm the user's role_name in `get_user_effective_permissions`.
================================================================================
"""
import uuid
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from fastapi import HTTPException, Request, Depends, status
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.database import get_db
from app.models.auth import User, Role, RolePermission, UserScope

logger = logging.getLogger("psf.permissions")


class DataScope:
    ALL = "ALL"
    DEALERSHIP = "DEALERSHIP"
    ASSIGNED_BRANCHES = "ASSIGNED_BRANCHES"
    OWN = "OWN"


class PermissionKey:
    # 1. Brands & Branches
    BRAND_MANAGE = "brand.manage"
    BRANCH_MANAGE = "branch.manage"

    # 2. Users & Roles
    USER_CREATE = "user.create"
    USER_EDIT = "user.edit"
    USER_DELETE = "user.delete"
    ROLE_MANAGE = "role.manage"
    PERMISSION_MANAGE = "permission.manage"

    # 3. Job Cards & Imports
    JOBCARD_VIEW = "jobcard.view"
    JOBCARD_EDIT = "jobcard.edit"
    JOBCARD_IMPORT = "jobcard.import"

    # 4. PSF Calling & Survey
    CALL_VIEW = "call.view"
    CALL_MAKE = "call.make"
    CALL_EDIT = "call.edit"
    CALL_REASSIGN = "call.reassign"
    CALL_ALLOCATE = "call.allocate"
    SURVEY_FILL = "survey.fill"
    TNPS_MAKE = "tnps.make"
    RECONFIRMATION_MAKE = "reconfirmation.make"
    ADVISOR_ACTION = "advisor.action"

    # 5. Complaints
    COMPLAINT_VIEW = "complaint.view"
    COMPLAINT_CREATE = "complaint.create"
    COMPLAINT_EDIT = "complaint.edit"
    COMPLAINT_RESPOND = "complaint.respond"
    COMPLAINT_CLOSE = "complaint.close"

    # 6. Reports & Audit
    REPORT_VIEW = "report.view"
    REPORT_EXPORT = "report.export"
    AUDIT_VIEW = "audit.view"

    # 7. Configuration & Masters
    CONFIG_VIEW = "config.view"
    CONFIG_MANAGE = "config.manage"
    QUESTIONNAIRE_VIEW = "questionnaire.view"
    QUESTIONNAIRE_MANAGE = "questionnaire.manage"
    DROPDOWN_VIEW = "dropdown.view"
    DROPDOWN_MANAGE = "dropdown.manage"
    STATUS_VIEW = "status.view"
    STATUS_MANAGE = "status.manage"
    SETTINGS_MANAGE = "settings.manage"
    ALLOCATION_CONFIGURE = "allocation.configure"

    # 8. Security & Data Correction
    DATA_CORRECT = "data.correct"
    CONTACT_UNMASK = "contact.unmask"


# Catalogue metadata for UI matrix rendering
PERMISSION_CATALOGUE = [
    {"category": "Brands & Branches", "key": PermissionKey.BRAND_MANAGE, "label": "Manage Brands (Add/Edit/Deactivate)", "description": "Create, edit, and deactivate OEM brand entries and DMS mappings."},
    {"category": "Brands & Branches", "key": PermissionKey.BRANCH_MANAGE, "label": "Manage Branches (Add/Edit/Deactivate)", "description": "Configure dealership branches, DMS codes, and service manager contacts."},
    {"category": "Users & Roles", "key": PermissionKey.USER_CREATE, "label": "Create Users", "description": "Create new employee login accounts within assigned scope."},
    {"category": "Users & Roles", "key": PermissionKey.USER_EDIT, "label": "Edit Users", "description": "Edit employee profiles, scope assignments, and passwords."},
    {"category": "Users & Roles", "key": PermissionKey.USER_DELETE, "label": "Deactivate Users", "description": "Soft-delete or deactivate staff accounts."},
    {"category": "Users & Roles", "key": PermissionKey.ROLE_MANAGE, "label": "Manage Roles", "description": "Add, clone, and configure system and custom roles."},
    {"category": "Users & Roles", "key": PermissionKey.PERMISSION_MANAGE, "label": "Manage Permissions Matrix", "description": "Adjust role permissions and data scopes."},
    {"category": "Job Cards & DMS", "key": PermissionKey.JOBCARD_VIEW, "label": "View Job Cards", "description": "View job cards and customer vehicle service history."},
    {"category": "Job Cards & DMS", "key": PermissionKey.JOBCARD_EDIT, "label": "Edit Job Cards", "description": "Edit vehicle details, service amounts, and advisors."},
    {"category": "Job Cards & DMS", "key": PermissionKey.JOBCARD_IMPORT, "label": "Import Job Cards", "description": "Upload CSV/Excel sheets or receive real-time webhook feeds."},
    {"category": "PSF Follow-up Calling", "key": PermissionKey.CALL_VIEW, "label": "View Calling Queue", "description": "Access PSF and survey queue lists."},
    {"category": "PSF Follow-up Calling", "key": PermissionKey.CALL_MAKE, "label": "Make Calls & Enter VOC", "description": "Conduct calls via Call Console and log responses."},
    {"category": "PSF Follow-up Calling", "key": PermissionKey.CALL_EDIT, "label": "Edit Call Log", "description": "Modify recorded call notes or attempt records."},
    {"category": "PSF Follow-up Calling", "key": PermissionKey.CALL_ALLOCATE, "label": "Allocate Calls", "description": "Assign pending follow-ups to specific CRE callers."},
    {"category": "PSF Follow-up Calling", "key": PermissionKey.CALL_REASSIGN, "label": "Reassign Calls", "description": "Transfer calls between callers or branches."},
    {"category": "PSF Follow-up Calling", "key": PermissionKey.SURVEY_FILL, "label": "Submit Survey Responses", "description": "Answer CSAT/NPS questionnaire items during follow-up."},
    {"category": "PSF Follow-up Calling", "key": PermissionKey.TNPS_MAKE, "label": "Conduct TNPS Calls", "description": "Conduct Ather Energy TNPS follow-up calls."},
    {"category": "PSF Follow-up Calling", "key": PermissionKey.RECONFIRMATION_MAKE, "label": "Conduct Post-Complaint Reconfirmations", "description": "Verify customer resolution satisfaction."},
    {"category": "PSF Follow-up Calling", "key": PermissionKey.ADVISOR_ACTION, "label": "Service Advisor Action", "description": "Review and action assigned advisor feedback tasks."},
    {"category": "Complaints & SLAs", "key": PermissionKey.COMPLAINT_VIEW, "label": "View Complaints", "description": "Access complaint tickets and timeline history."},
    {"category": "Complaints & SLAs", "key": PermissionKey.COMPLAINT_CREATE, "label": "Create Complaints", "description": "Escalate dissatisfaction to complaint tickets."},
    {"category": "Complaints & SLAs", "key": PermissionKey.COMPLAINT_EDIT, "label": "Edit Complaint Details", "description": "Update category, severity, and root cause notes."},
    {"category": "Complaints & SLAs", "key": PermissionKey.COMPLAINT_RESPOND, "label": "Submit Complaint Resolution Remarks", "description": "Provide investigation and corrective action remarks."},
    {"category": "Complaints & SLAs", "key": PermissionKey.COMPLAINT_CLOSE, "label": "Close Complaints", "description": "Mark complaints resolved / closed in time."},
    {"category": "Reports & Auditing", "key": PermissionKey.REPORT_VIEW, "label": "View Analytics & Reports", "description": "Access CSAT, PSF, and workshop KPI dashboards."},
    {"category": "Reports & Auditing", "key": PermissionKey.REPORT_EXPORT, "label": "Export Reports & Raw Data", "description": "Download Excel, CSV, and summary reports."},
    {"category": "Reports & Auditing", "key": PermissionKey.AUDIT_VIEW, "label": "View Audit Logs", "description": "Inspect system audit trail and user action history."},
    {"category": "Configuration & Masters", "key": PermissionKey.CONFIG_VIEW, "label": "View Configuration", "description": "Read-only access to system masters and questionnaires."},
    {"category": "Configuration & Masters", "key": PermissionKey.CONFIG_MANAGE, "label": "Manage Full System Config", "description": "Full access to settings, templates, and custom fields."},
    {"category": "Configuration & Masters", "key": PermissionKey.QUESTIONNAIRE_VIEW, "label": "View Questionnaires", "description": "Inspect questionnaire templates and question versions."},
    {"category": "Configuration & Masters", "key": PermissionKey.QUESTIONNAIRE_MANAGE, "label": "Manage Questionnaires", "description": "Create, edit, publish, and rollback questionnaires."},
    {"category": "Configuration & Masters", "key": PermissionKey.DROPDOWN_VIEW, "label": "View Dropdown Masters", "description": "Inspect service types and complaint categories."},
    {"category": "Configuration & Masters", "key": PermissionKey.DROPDOWN_MANAGE, "label": "Manage Dropdown Masters", "description": "Configure categories, service types, and behavior flags."},
    {"category": "Configuration & Masters", "key": PermissionKey.STATUS_VIEW, "label": "View Statuses", "description": "View call and case status dictionary."},
    {"category": "Configuration & Masters", "key": PermissionKey.STATUS_MANAGE, "label": "Manage Statuses & Rating Scales", "description": "Configure sentiment scales, retry rules, and bands."},
    {"category": "Configuration & Masters", "key": PermissionKey.SETTINGS_MANAGE, "label": "Manage App Settings & Branding", "description": "Configure white-label themes and SMS/WhatsApp templates."},
    {"category": "Configuration & Masters", "key": PermissionKey.ALLOCATION_CONFIGURE, "label": "Configure Call Allocation Rules", "description": "Super Admin configuration of automatic call allocation strategies and rules."},
    {"category": "Security & Governance", "key": PermissionKey.DATA_CORRECT, "label": "Super Admin Data Correction", "description": "Correct any record in the system with mandatory logged reason."},
    {"category": "Security & Governance", "key": PermissionKey.CONTACT_UNMASK, "label": "Unmask Customer Phone & PII", "description": "View unmasked real phone numbers and sensitive PII."},
]


async def invalidate_permission_cache(role_id: Optional[uuid.UUID] = None, user_id: Optional[uuid.UUID] = None) -> None:
    """Invalidate permissions cached in Redis."""
    try:
        r = await get_redis()
        if user_id:
            await r.delete(f"user_perms:{user_id}")
        elif role_id:
            # Delete role cache and pattern match all user perms
            await r.delete(f"role_perms:{role_id}")
            keys = await r.keys("user_perms:*")
            if keys:
                await r.delete(*keys)
        else:
            keys = await r.keys("user_perms:*") + await r.keys("role_perms:*")
            if keys:
                await r.delete(*keys)
    except Exception as e:
        logger.warning(f"Redis cache invalidation error: {e}")


async def get_user_effective_permissions(db: AsyncSession, user: User) -> Dict[str, Any]:
    """
    Retrieve user's effective permissions, scopes, and field rules.
    Cached in Redis for performance.
    """
    cache_key = f"user_perms:{user.id}"
    try:
        r = await get_redis()
        cached = await r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    # Load role and permissions
    stmt = (
        select(Role)
        .options(selectinload(Role.role_permissions))
        .where(Role.id == user.role_id)
    )
    role_obj = (await db.execute(stmt)).scalar_one_or_none()
    level = role_obj.level if role_obj else "L3"
    role_name = role_obj.name.upper() if role_obj else "USER"
    is_super_admin = (level == "L1" or role_name == "SUPER_ADMIN")

    permissions_map: Dict[str, str] = {}
    if is_super_admin:
        # Super admin has all permissions with ALL scope
        for p in PERMISSION_CATALOGUE:
            permissions_map[p["key"]] = DataScope.ALL
    elif role_obj and role_obj.role_permissions:
        for rp in role_obj.role_permissions:
            permissions_map[rp.permission] = rp.data_scope
    elif role_obj and role_obj.permissions:
        # Fallback to legacy permissions JSONB list if role_permissions not yet populated
        for p_str in role_obj.permissions:
            permissions_map[p_str] = DataScope.ALL

    # User assigned branch & brand IDs from scopes
    scope_stmt = select(UserScope).where(UserScope.user_id == user.id, UserScope.is_deleted == False)
    scopes = (await db.execute(scope_stmt)).scalars().all()
    assigned_branches = [str(s.branch_id) for s in scopes if s.branch_id]
    assigned_brands = [str(s.brand_id) for s in scopes if s.brand_id]

    field_rules = (role_obj.field_rules if role_obj and role_obj.field_rules else {})
    dashboard_config = (role_obj.dashboard_config if role_obj and role_obj.dashboard_config else {})

    res = {
        "user_id": str(user.id),
        "role_id": str(user.role_id),
        "role_name": role_name,
        "level": level,
        "is_super_admin": is_super_admin,
        "permissions": permissions_map, # e.g. {"jobcard.view": "ASSIGNED_BRANCHES"}
        "assigned_branches": assigned_branches,
        "assigned_brands": assigned_brands,
        "field_rules": field_rules,
        "dashboard_config": dashboard_config,
    }

    try:
        r = await get_redis()
        await r.setex(cache_key, 3600, json.dumps(res))
    except Exception:
        pass

    return res


def require(permission_key: str) -> Callable:
    """
    Central dependency checking if the user has the required permission.
    No hard-coded role names. Pure data-driven permission check.
    """
    from app.api.deps import get_current_active_user

    async def dependency(
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        effective = await get_user_effective_permissions(db, current_user)
        is_super = effective.get("is_super_admin", False)

        # Allow if Super Admin (L1) or has the specific permission
        perms = effective.get("permissions", {})
        if not is_super and permission_key not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission_key}' is required to perform this action.",
            )

        # Instate effective scope in request.state for downstream data query scoping
        request.state.effective_scope = perms.get(permission_key, DataScope.ALL if is_super else DataScope.OWN)
        request.state.assigned_branches = effective.get("assigned_branches", [])
        request.state.assigned_brands = effective.get("assigned_brands", [])
        request.state.user_permissions = perms
        request.state.is_super_admin = is_super

        return current_user

    return dependency


def require_any(*permission_keys: str) -> Callable:
    """Check if the user has AT LEAST ONE of the listed permissions."""
    from app.api.deps import get_current_active_user

    async def dependency(
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        effective = await get_user_effective_permissions(db, current_user)
        is_super = effective.get("is_super_admin", False)

        perms = effective.get("permissions", {})
        if not is_super and not any(k in perms for k in permission_keys):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: At least one of {permission_keys} is required.",
            )

        matched_key = next((k for k in permission_keys if k in perms), permission_keys[0])
        request.state.effective_scope = perms.get(matched_key, DataScope.ALL if is_super else DataScope.OWN)
        request.state.assigned_branches = effective.get("assigned_branches", [])
        request.state.assigned_brands = effective.get("assigned_brands", [])
        request.state.user_permissions = perms
        request.state.is_super_admin = is_super

        return current_user

    return dependency


def apply_data_scope(
    query: Any,
    model: Any,
    current_user: User,
    permission_key: str,
    effective_permissions: Dict[str, Any],
) -> Any:
    """
    ONE central place applying data-driven scope filtering to any SQLAlchemy query.
    DataScope options:
      - ALL / DEALERSHIP: Tenant-wide access
      - ASSIGNED_BRANCHES: Restricted to user's assigned branch IDs
      - OWN: Restricted to user's own records (assigned_to_id == me or service_advisor_id == me)
    """
    is_super = effective_permissions.get("is_super_admin", False)
    if is_super:
        return query

    perms = effective_permissions.get("permissions", {})
    scope = perms.get(permission_key, DataScope.ALL)

    if scope in [DataScope.ALL, DataScope.DEALERSHIP]:
        return query

    assigned_branches = [uuid.UUID(b) for b in effective_permissions.get("assigned_branches", []) if b]

    if scope == DataScope.ASSIGNED_BRANCHES:
        if not assigned_branches:
            # User has no branch scopes assigned -> return empty set condition
            return query.where(model.id == None)
        if hasattr(model, "branch_id"):
            return query.where(model.branch_id.in_(assigned_branches))
        elif hasattr(model, "job_card_id"):
            from app.models.service import JobCard
            return query.join(JobCard, model.job_card_id == JobCard.id).where(JobCard.branch_id.in_(assigned_branches))
        return query

    if scope == DataScope.OWN:
        # Own assigned calls, complaints, or advisor tasks
        if hasattr(model, "assigned_to_id"):
            return query.where(model.assigned_to_id == current_user.id)
        elif hasattr(model, "service_advisor_id"):
            return query.where(model.service_advisor_id == current_user.id)
        elif hasattr(model, "called_by_id"):
            return query.where(model.called_by_id == current_user.id)
        elif hasattr(model, "job_card_id"):
            from app.models.service import JobCard
            return query.join(JobCard, model.job_card_id == JobCard.id).where(
                or_(
                    JobCard.service_advisor_id == current_user.id,
                    JobCard.uploaded_by_id == current_user.id,
                )
            )

    return query
