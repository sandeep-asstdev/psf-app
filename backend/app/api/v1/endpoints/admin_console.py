"""
================================================================================
FILE PURPOSE: Enterprise Admin Console Endpoints (Super Admin Only).
Provides restricted endpoints for managing the RBAC Role Permission Matrix,
system-wide configuration parameters, and supervisor data corrections with mandatory audit reasons.

KEY RESPONSIBILITIES:
- Returns role permissions matrix (`GET /admin/matrix`).
- Updates permissions for specific roles (`PUT /admin/matrix`).
- Performs supervisor data corrections with mandatory audit trail (`POST /admin/correct-data`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: HTTP 403 Forbidden: 'Super Admin privileges required'
  -> Cause: A non-Super Admin user attempted to modify system security roles.
  -> What should you do: Log in as Super Admin (`admin@apexauto.com`). Other roles cannot access the Admin Console.
================================================================================
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, and_, or_, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_active_user, require, require_any
from app.core.permissions import (
    PermissionKey,
    DataScope,
    PERMISSION_CATALOGUE,
    invalidate_permission_cache,
)
from app.models.auth import User, Role, RolePermission
from app.models.service import ServiceType, JobCard
from app.models.followup import FollowupQueue, CallAttempt
from app.models.complaint import Complaint
from app.models.customer import Customer
from app.models.additional import (
    CustomFieldDefinition,
    ImportMappingTemplate,
    ConfigChangeHistory,
    AuditLog,
)
from app.schemas.admin_console import (
    RoleMatrixResponse,
    RoleMatrixItem,
    RoleCreateRequest,
    RoleUpdateRequest,
    RoleCloneRequest,
    CustomFieldCreate,
    CustomFieldUpdate,
    CustomFieldResponse,
    ImportTemplateCreate,
    ImportTemplateUpdate,
    ImportTemplateResponse,
    ServiceTypeCreate,
    ServiceTypeUpdate,
    ServiceTypeResponse,
    ConfigHistoryResponse,
    ConfigRollbackRequest,
    DataCorrectionRequest,
    DataCorrectionResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin Console & Dynamic Governance"])


# -----------------------------------------------------------------------------
# 1. Role & Permission Matrix Endpoints
# -----------------------------------------------------------------------------
@router.get("/matrix", response_model=RoleMatrixResponse)
async def get_role_permission_matrix(
    current_user: User = Depends(require_any(PermissionKey.PERMISSION_MANAGE, PermissionKey.ROLE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full matrix grid of Roles x Permissions with active data scopes."""
    roles_stmt = (
        select(Role)
        .options(selectinload(Role.role_permissions), selectinload(Role.users))
        .where(
            (Role.tenant_id == current_user.tenant_id) | (Role.tenant_id == None),
            Role.is_deleted == False,
        )
        .order_by(Role.level, Role.name)
    )
    roles = (await db.execute(roles_stmt)).scalars().all()

    role_items = []
    for r in roles:
        perms_map = {rp.permission: rp.data_scope for rp in r.role_permissions}
        role_items.append(
            RoleMatrixItem(
                id=r.id,
                name=r.name,
                level=r.level or "L3",
                description=r.description,
                is_system=r.is_system,
                is_active=r.is_active,
                permissions=perms_map,
                field_rules=r.field_rules or {},
                dashboard_config=r.dashboard_config or {},
                user_count=len([u for u in r.users if not u.is_deleted]),
            )
        )

    return RoleMatrixResponse(
        catalogue=PERMISSION_CATALOGUE,
        roles=role_items,
    )


@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_new_role(
    payload: RoleCreateRequest,
    request: Request,
    current_user: User = Depends(require(PermissionKey.ROLE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new configurable database role and seed its matrix permissions."""
    # Check duplicate name
    existing_stmt = select(Role).where(
        Role.tenant_id == current_user.tenant_id,
        Role.name == payload.name.strip(),
        Role.is_deleted == False,
    )
    if (await db.execute(existing_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Role with name '{payload.name}' already exists.")

    new_role = Role(
        tenant_id=current_user.tenant_id,
        name=payload.name.strip(),
        level=payload.level,
        description=payload.description,
        field_rules=payload.field_rules or {"phone": "masked"},
        dashboard_config=payload.dashboard_config or {},
        is_system=False,
        is_active=True,
    )
    db.add(new_role)
    await db.flush()

    # Add permissions
    for perm_key, scope in (payload.permissions or {}).items():
        rp = RolePermission(
            tenant_id=current_user.tenant_id,
            role_id=new_role.id,
            permission=perm_key,
            data_scope=scope,
        )
        db.add(rp)

    # Record config change history
    history = ConfigChangeHistory(
        tenant_id=current_user.tenant_id,
        config_type="ROLE_MATRIX",
        entity_id=str(new_role.id),
        status="PUBLISHED",
        config_payload={"role_name": new_role.name, "level": new_role.level, "permissions": payload.permissions},
        reason=f"Created new role {new_role.name}",
        changed_by_id=current_user.id,
    )
    db.add(history)
    await db.commit()

    await invalidate_permission_cache(role_id=new_role.id)
    return {"message": f"Role '{new_role.name}' created successfully", "role_id": str(new_role.id)}


@router.put("/roles/{role_id}/permissions")
async def update_role_permissions(
    role_id: uuid.UUID,
    payload: Dict[str, Any], # {permissions: {key: scope}, field_rules: {}, dashboard_config: {}}
    request: Request,
    current_user: User = Depends(require(PermissionKey.PERMISSION_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Update permissions, data scopes, and field rules for an existing role."""
    r_stmt = (
        select(Role)
        .options(selectinload(Role.role_permissions))
        .where(Role.id == role_id, Role.is_deleted == False)
    )
    role = (await db.execute(r_stmt)).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Lockout protection: cannot remove permission.manage from Super Admin
    if role.name == "SUPER_ADMIN":
        new_perms = payload.get("permissions", {})
        if PermissionKey.PERMISSION_MANAGE not in new_perms:
            raise HTTPException(
                status_code=400,
                detail="Lockout Protection: You cannot remove 'permission.manage' from SUPER_ADMIN.",
            )

    # Update role metadata
    if "field_rules" in payload:
        role.field_rules = payload["field_rules"]
    if "dashboard_config" in payload:
        role.dashboard_config = payload["dashboard_config"]

    # Replace role_permissions
    new_perms = payload.get("permissions", {})
    existing_map = {rp.permission: rp for rp in role.role_permissions}

    # Delete removed
    for p_key, rp in list(existing_map.items()):
        if p_key not in new_perms:
            await db.delete(rp)

    # Update or insert
    for p_key, scope in new_perms.items():
        if p_key in existing_map:
            existing_map[p_key].data_scope = scope
        else:
            db.add(
                RolePermission(
                    tenant_id=current_user.tenant_id,
                    role_id=role.id,
                    permission=p_key,
                    data_scope=scope,
                )
            )

    # Versioned config history
    history = ConfigChangeHistory(
        tenant_id=current_user.tenant_id,
        config_type="ROLE_MATRIX",
        entity_id=str(role.id),
        status="PUBLISHED",
        config_payload={"role_id": str(role.id), "permissions": new_perms},
        reason=payload.get("reason", f"Updated permissions for role {role.name}"),
        changed_by_id=current_user.id,
    )
    db.add(history)
    await db.commit()

    await invalidate_permission_cache(role_id=role.id)
    return {"message": f"Permissions for role '{role.name}' updated and cache invalidated."}


@router.post("/roles/{role_id}/clone")
async def clone_role(
    role_id: uuid.UUID,
    payload: RoleCloneRequest,
    current_user: User = Depends(require(PermissionKey.ROLE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Clone an existing role with all its permissions and field rules."""
    src_stmt = (
        select(Role)
        .options(selectinload(Role.role_permissions))
        .where(Role.id == role_id, Role.is_deleted == False)
    )
    source_role = (await db.execute(src_stmt)).scalar_one_or_none()
    if not source_role:
        raise HTTPException(status_code=404, detail="Source role not found")

    new_role = Role(
        tenant_id=current_user.tenant_id,
        name=payload.new_name.strip(),
        level=source_role.level,
        description=payload.description or f"Cloned from {source_role.name}",
        field_rules=source_role.field_rules or {},
        dashboard_config=source_role.dashboard_config or {},
        is_system=False,
        is_active=True,
    )
    db.add(new_role)
    await db.flush()

    for rp in source_role.role_permissions:
        db.add(
            RolePermission(
                tenant_id=current_user.tenant_id,
                role_id=new_role.id,
                permission=rp.permission,
                data_scope=rp.data_scope,
            )
        )

    await db.commit()
    await invalidate_permission_cache(role_id=new_role.id)
    return {"message": f"Successfully cloned '{source_role.name}' to '{new_role.name}'", "role_id": str(new_role.id)}


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: uuid.UUID,
    current_user: User = Depends(require(PermissionKey.ROLE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate or soft-delete a role with lockout protection."""
    r_stmt = select(Role).options(selectinload(Role.users)).where(Role.id == role_id)
    role = (await db.execute(r_stmt)).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.is_system or role.name == "SUPER_ADMIN":
        raise HTTPException(status_code=400, detail="Lockout Protection: System core roles cannot be deleted.")

    assigned_users = [u for u in role.users if not u.is_deleted]
    if assigned_users:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete role: {len(assigned_users)} active user(s) currently assigned. Reassign users first.",
        )

    role.is_deleted = True
    role.is_active = False
    role.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    await invalidate_permission_cache(role_id=role.id)
    return {"message": f"Role '{role.name}' deleted successfully."}


# -----------------------------------------------------------------------------
# 2. Custom Field Definitions Endpoints
# -----------------------------------------------------------------------------
@router.get("/custom-fields", response_model=List[CustomFieldResponse])
async def list_custom_fields(
    entity_type: Optional[str] = None,
    current_user: User = Depends(require(PermissionKey.CONFIG_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """List configured custom fields for Job Cards, Calls, or Complaints."""
    query = select(CustomFieldDefinition).where(
        CustomFieldDefinition.tenant_id == current_user.tenant_id,
        CustomFieldDefinition.is_deleted == False,
    )
    if entity_type:
        query = query.where(CustomFieldDefinition.entity_type == entity_type.upper())
    query = query.order_by(CustomFieldDefinition.display_order, CustomFieldDefinition.field_label)
    res = await db.execute(query)
    return res.scalars().all()


@router.post("/custom-fields", response_model=CustomFieldResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_field(
    payload: CustomFieldCreate,
    current_user: User = Depends(require(PermissionKey.CONFIG_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new dynamic custom field."""
    clean_key = payload.field_key.strip().lower().replace(" ", "_")
    field = CustomFieldDefinition(
        tenant_id=current_user.tenant_id,
        brand_id=payload.brand_id,
        entity_type=payload.entity_type.upper(),
        field_key=clean_key,
        field_label=payload.field_label.strip(),
        field_type=payload.field_type.upper(),
        options=payload.options,
        is_required=payload.is_required,
        display_order=payload.display_order,
        is_active=True,
    )
    db.add(field)
    await db.commit()
    await db.refresh(field)
    return field


@router.put("/custom-fields/{field_id}", response_model=CustomFieldResponse)
async def update_custom_field(
    field_id: uuid.UUID,
    payload: CustomFieldUpdate,
    current_user: User = Depends(require(PermissionKey.CONFIG_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Update custom field definition."""
    stmt = select(CustomFieldDefinition).where(
        CustomFieldDefinition.id == field_id,
        CustomFieldDefinition.tenant_id == current_user.tenant_id,
        CustomFieldDefinition.is_deleted == False,
    )
    field = (await db.execute(stmt)).scalar_one_or_none()
    if not field:
        raise HTTPException(status_code=404, detail="Custom field definition not found")

    if payload.field_label is not None:
        field.field_label = payload.field_label.strip()
    if payload.field_type is not None:
        field.field_type = payload.field_type.upper()
    if payload.options is not None:
        field.options = payload.options
    if payload.is_required is not None:
        field.is_required = payload.is_required
    if payload.display_order is not None:
        field.display_order = payload.display_order
    if payload.is_active is not None:
        field.is_active = payload.is_active

    await db.commit()
    await db.refresh(field)
    return field


@router.delete("/custom-fields/{field_id}")
async def delete_custom_field(
    field_id: uuid.UUID,
    current_user: User = Depends(require(PermissionKey.CONFIG_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete custom field definition."""
    stmt = select(CustomFieldDefinition).where(
        CustomFieldDefinition.id == field_id,
        CustomFieldDefinition.tenant_id == current_user.tenant_id,
    )
    field = (await db.execute(stmt)).scalar_one_or_none()
    if not field:
        raise HTTPException(status_code=404, detail="Custom field not found")

    field.is_deleted = True
    field.is_active = False
    field.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Custom field deleted successfully"}


# -----------------------------------------------------------------------------
# 3. Import Mapping Templates Endpoints
# -----------------------------------------------------------------------------
@router.get("/import-templates", response_model=List[ImportTemplateResponse])
async def list_import_templates(
    current_user: User = Depends(require(PermissionKey.CONFIG_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """List saved DMS import mapping templates."""
    stmt = (
        select(ImportMappingTemplate)
        .where(
            ImportMappingTemplate.tenant_id == current_user.tenant_id,
            ImportMappingTemplate.is_deleted == False,
        )
        .order_by(ImportMappingTemplate.name)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/import-templates", response_model=ImportTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_import_template(
    payload: ImportTemplateCreate,
    current_user: User = Depends(require(PermissionKey.CONFIG_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new brand import column mapping template."""
    tpl = ImportMappingTemplate(
        tenant_id=current_user.tenant_id,
        brand_id=payload.brand_id,
        name=payload.name.strip(),
        column_mapping=payload.column_mapping,
        is_default=payload.is_default,
        is_active=True,
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.put("/import-templates/{template_id}", response_model=ImportTemplateResponse)
async def update_import_template(
    template_id: uuid.UUID,
    payload: ImportTemplateUpdate,
    current_user: User = Depends(require(PermissionKey.CONFIG_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Update an import mapping template."""
    stmt = select(ImportMappingTemplate).where(
        ImportMappingTemplate.id == template_id,
        ImportMappingTemplate.tenant_id == current_user.tenant_id,
        ImportMappingTemplate.is_deleted == False,
    )
    tpl = (await db.execute(stmt)).scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    if payload.name is not None:
        tpl.name = payload.name.strip()
    if payload.column_mapping is not None:
        tpl.column_mapping = payload.column_mapping
    if payload.is_default is not None:
        tpl.is_default = payload.is_default
    if payload.is_active is not None:
        tpl.is_active = payload.is_active

    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.delete("/import-templates/{template_id}")
async def delete_import_template(
    template_id: uuid.UUID,
    current_user: User = Depends(require(PermissionKey.CONFIG_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete import template."""
    stmt = select(ImportMappingTemplate).where(
        ImportMappingTemplate.id == template_id,
        ImportMappingTemplate.tenant_id == current_user.tenant_id,
    )
    tpl = (await db.execute(stmt)).scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    tpl.is_deleted = True
    tpl.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Import template deleted successfully"}


# -----------------------------------------------------------------------------
# 4. Service Types (Dropdown Masters) Endpoints
# -----------------------------------------------------------------------------
@router.get("/service-types", response_model=List[ServiceTypeResponse])
async def list_service_types(
    current_user: User = Depends(require(PermissionKey.DROPDOWN_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """List service types (PMS, Running Repair, Bodyshop, etc.)."""
    stmt = (
        select(ServiceType)
        .where(
            ServiceType.tenant_id == current_user.tenant_id,
            ServiceType.is_deleted == False,
        )
        .order_by(ServiceType.display_order, ServiceType.name)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/service-types", response_model=ServiceTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_service_type(
    payload: ServiceTypeCreate,
    current_user: User = Depends(require(PermissionKey.DROPDOWN_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Create service type master record."""
    st = ServiceType(
        tenant_id=current_user.tenant_id,
        name=payload.name.strip(),
        code=payload.code.strip().upper(),
        color=payload.color,
        icon=payload.icon,
        display_order=payload.display_order,
        behaviour_flags=payload.behaviour_flags or {},
        is_active=True,
    )
    db.add(st)
    await db.commit()
    await db.refresh(st)
    return st


@router.put("/service-types/{type_id}", response_model=ServiceTypeResponse)
async def update_service_type(
    type_id: uuid.UUID,
    payload: ServiceTypeUpdate,
    current_user: User = Depends(require(PermissionKey.DROPDOWN_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Update service type master."""
    stmt = select(ServiceType).where(
        ServiceType.id == type_id,
        ServiceType.tenant_id == current_user.tenant_id,
        ServiceType.is_deleted == False,
    )
    st = (await db.execute(stmt)).scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Service type not found")

    if payload.name is not None:
        st.name = payload.name.strip()
    if payload.code is not None:
        st.code = payload.code.strip().upper()
    if payload.color is not None:
        st.color = payload.color
    if payload.icon is not None:
        st.icon = payload.icon
    if payload.display_order is not None:
        st.display_order = payload.display_order
    if payload.behaviour_flags is not None:
        st.behaviour_flags = payload.behaviour_flags
    if payload.is_active is not None:
        st.is_active = payload.is_active

    await db.commit()
    await db.refresh(st)
    return st


# -----------------------------------------------------------------------------
# 5. Audit Logs & Config Change History with 1-Click Rollback
# -----------------------------------------------------------------------------
@router.get("/audit-logs")
async def list_audit_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    skip: int = 0,
    current_user: User = Depends(require(PermissionKey.AUDIT_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """List system audit trail with before/after snapshots and mandatory reasons."""
    stmt = select(AuditLog).where(AuditLog.tenant_id == current_user.tenant_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)

    logs = (await db.execute(stmt)).scalars().all()
    return logs


@router.get("/config-history", response_model=List[ConfigHistoryResponse])
async def list_config_history(
    config_type: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(require(PermissionKey.CONFIG_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """List versioned configuration changes (draft, published, rolled back)."""
    stmt = (
        select(ConfigChangeHistory)
        .options(selectinload(ConfigChangeHistory.changed_by))
        .where(ConfigChangeHistory.tenant_id == current_user.tenant_id)
    )
    if config_type:
        stmt = stmt.where(ConfigChangeHistory.config_type == config_type.upper())
    stmt = stmt.order_by(ConfigChangeHistory.created_at.desc()).limit(limit)
    histories = (await db.execute(stmt)).scalars().all()

    items = []
    for h in histories:
        items.append(
            ConfigHistoryResponse(
                id=h.id,
                tenant_id=h.tenant_id,
                config_type=h.config_type,
                entity_id=h.entity_id,
                version=h.version,
                status=h.status,
                config_payload=h.config_payload,
                reason=h.reason,
                changed_by_id=h.changed_by_id,
                changed_by_name=h.changed_by.full_name if h.changed_by else None,
                created_at=h.created_at,
            )
        )
    return items


@router.post("/config-history/{history_id}/rollback")
async def rollback_config_change(
    history_id: uuid.UUID,
    payload: ConfigRollbackRequest,
    request: Request,
    current_user: User = Depends(require(PermissionKey.CONFIG_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """One-click rollback of configuration to a previous version with audit reason."""
    stmt = select(ConfigChangeHistory).where(
        ConfigChangeHistory.id == history_id,
        ConfigChangeHistory.tenant_id == current_user.tenant_id,
    )
    history = (await db.execute(stmt)).scalar_one_or_none()
    if not history:
        raise HTTPException(status_code=404, detail="Config history record not found")

    if not payload.reason.strip():
        raise HTTPException(status_code=400, detail="Mandatory reason required for configuration rollback.")

    # Apply rollback based on config_type
    if history.config_type == "ROLE_MATRIX" and history.entity_id:
        role_stmt = (
            select(Role)
            .options(selectinload(Role.role_permissions))
            .where(Role.id == uuid.UUID(history.entity_id))
        )
        role = (await db.execute(role_stmt)).scalar_one_or_none()
        if role:
            saved_perms = history.config_payload.get("permissions", {})
            for rp in list(role.role_permissions):
                await db.delete(rp)
            for pk, sc in saved_perms.items():
                db.add(RolePermission(tenant_id=role.tenant_id, role_id=role.id, permission=pk, data_scope=sc))
            await invalidate_permission_cache(role_id=role.id)

    # Record new rollback event
    rb_record = ConfigChangeHistory(
        tenant_id=current_user.tenant_id,
        config_type=history.config_type,
        entity_id=history.entity_id,
        version=history.version + 1,
        status="ROLLED_BACK",
        config_payload=history.config_payload,
        reason=f"Rollback to v{history.version}: {payload.reason.strip()}",
        changed_by_id=current_user.id,
    )
    db.add(rb_record)
    await db.commit()

    return {"message": f"Successfully rolled back {history.config_type} to version {history.version}"}


# -----------------------------------------------------------------------------
# 6. Super Admin Data Correction Screen Endpoint
# -----------------------------------------------------------------------------
@router.post("/data-correction", response_model=DataCorrectionResponse)
async def perform_data_correction(
    payload: DataCorrectionRequest,
    request: Request,
    current_user: User = Depends(require(PermissionKey.DATA_CORRECT)),
    db: AsyncSession = Depends(get_db),
):
    """
    Super Admin master data correction screen:
    Finds any record, applies updates, records mandatory logged reason and audit before/after.
    """
    if not payload.reason.strip():
        raise HTTPException(status_code=400, detail="Mandatory audit justification reason is required for data correction.")

    entity_type = payload.entity_type.upper()
    entity_id_str = payload.entity_id.strip()

    target_obj = None
    old_values = {}
    new_values = {}

    try:
        target_uuid = uuid.UUID(entity_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity UUID format")

    if entity_type == "JOB_CARD":
        stmt = select(JobCard).where(JobCard.id == target_uuid, JobCard.tenant_id == current_user.tenant_id)
        target_obj = (await db.execute(stmt)).scalar_one_or_none()
    elif entity_type == "CALL":
        stmt = select(FollowupQueue).where(FollowupQueue.id == target_uuid, FollowupQueue.tenant_id == current_user.tenant_id)
        target_obj = (await db.execute(stmt)).scalar_one_or_none()
    elif entity_type == "COMPLAINT":
        stmt = select(Complaint).where(Complaint.id == target_uuid, Complaint.tenant_id == current_user.tenant_id)
        target_obj = (await db.execute(stmt)).scalar_one_or_none()
    elif entity_type == "USER":
        stmt = select(User).where(User.id == target_uuid, User.tenant_id == current_user.tenant_id)
        target_obj = (await db.execute(stmt)).scalar_one_or_none()
    elif entity_type == "CUSTOMER":
        stmt = select(Customer).where(Customer.id == target_uuid, Customer.tenant_id == current_user.tenant_id)
        target_obj = (await db.execute(stmt)).scalar_one_or_none()
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported entity type '{entity_type}'")

    if not target_obj:
        raise HTTPException(status_code=404, detail=f"Record of type '{entity_type}' with ID '{entity_id_str}' not found.")

    # Apply updates and track diff
    for field_name, new_val in payload.field_updates.items():
        if hasattr(target_obj, field_name):
            old_val = getattr(target_obj, field_name)
            old_values[field_name] = str(old_val) if isinstance(old_val, (uuid.UUID, datetime)) else old_val
            new_values[field_name] = new_val
            setattr(target_obj, field_name, new_val)

    # Write audit log
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="SUPER_ADMIN_DATA_CORRECTION",
        entity_type=entity_type,
        entity_id=entity_id_str,
        old_values=old_values,
        new_values=new_values,
        reason=payload.reason.strip(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    return DataCorrectionResponse(
        success=True,
        entity_type=entity_type,
        entity_id=entity_id_str,
        old_values=old_values,
        new_values=new_values,
        audit_id=audit.id,
        message=f"Data correction applied successfully. Audit ID: {audit.id}",
    )

