"""
================================================================================
FILE PURPOSE: Enterprise Admin Console Data Validation Schemas.
Defines Pydantic models for the Super Admin RBAC Role Matrix,
system-wide configuration toggles, and supervisor data correction workflows.

KEY RESPONSIBILITIES:
- Validates Role Matrix grid payload (roles, permissions, data scopes).
- Validates supervisor data corrections (mandatory reason, field updates, audit tracking).
- Validates tenant allocation and security parameters.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: ValidationError: reason field required for data correction
  -> Cause: A supervisor attempted to correct a database record without providing an explanatory audit reason.
  -> What should you do: Prompt the user in the UI to enter a non-empty audit explanation before submitting.
================================================================================
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# -------------------------------------------------------------------------
# Role & Permission Matrix Schemas
# -------------------------------------------------------------------------
class RolePermissionItem(BaseModel):
    permission: str
    data_scope: str = "ALL" # ALL | DEALERSHIP | ASSIGNED_BRANCHES | OWN


class RoleMatrixItem(BaseModel):
    id: uuid.UUID
    name: str
    level: str # L1 | L2 | L3
    description: Optional[str] = None
    is_system: bool
    is_active: bool
    permissions: Dict[str, str] # {permission_key: data_scope}
    field_rules: Optional[Dict[str, Any]] = None
    dashboard_config: Optional[Dict[str, Any]] = None
    user_count: int = 0


class RoleMatrixResponse(BaseModel):
    catalogue: List[Dict[str, Any]]
    roles: List[RoleMatrixItem]


class RoleCreateRequest(BaseModel):
    name: str
    level: str = "L3" # L1 | L2 | L3
    description: Optional[str] = None
    permissions: Dict[str, str] = Field(default_factory=dict) # {permission_key: data_scope}
    field_rules: Optional[Dict[str, Any]] = None
    dashboard_config: Optional[Dict[str, Any]] = None


class RoleUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None
    is_active: Optional[bool] = None
    permissions: Optional[Dict[str, str]] = None
    field_rules: Optional[Dict[str, Any]] = None
    dashboard_config: Optional[Dict[str, Any]] = None


class RoleCloneRequest(BaseModel):
    new_name: str
    description: Optional[str] = None


# -------------------------------------------------------------------------
# Custom Field Schemas
# -------------------------------------------------------------------------
class CustomFieldCreate(BaseModel):
    brand_id: Optional[uuid.UUID] = None
    entity_type: str # JOB_CARD | CALL | COMPLAINT
    field_key: str
    field_label: str
    field_type: str = "TEXT" # TEXT | NUMBER | SELECT | DATE | BOOLEAN
    options: Optional[Dict[str, Any]] = None
    is_required: bool = False
    display_order: int = 0


class CustomFieldUpdate(BaseModel):
    field_label: Optional[str] = None
    field_type: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    is_required: Optional[bool] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class CustomFieldResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    brand_id: Optional[uuid.UUID] = None
    entity_type: str
    field_key: str
    field_label: str
    field_type: str
    options: Optional[Dict[str, Any]] = None
    is_required: bool
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# Import Template Schemas
# -------------------------------------------------------------------------
class ImportTemplateCreate(BaseModel):
    brand_id: Optional[uuid.UUID] = None
    name: str
    column_mapping: Dict[str, str]
    is_default: bool = False


class ImportTemplateUpdate(BaseModel):
    name: Optional[str] = None
    column_mapping: Optional[Dict[str, str]] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class ImportTemplateResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    brand_id: Optional[uuid.UUID] = None
    name: str
    column_mapping: Dict[str, str]
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# Service Type Schemas
# -------------------------------------------------------------------------
class ServiceTypeCreate(BaseModel):
    name: str
    code: str
    color: Optional[str] = "#2563EB"
    icon: Optional[str] = "Wrench"
    display_order: int = 0
    behaviour_flags: Optional[Dict[str, Any]] = None


class ServiceTypeUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None
    behaviour_flags: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ServiceTypeResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code: str
    color: Optional[str] = None
    icon: Optional[str] = None
    display_order: int
    behaviour_flags: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# Config Change History & Rollback Schemas
# -------------------------------------------------------------------------
class ConfigHistoryResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    config_type: str
    entity_id: Optional[str] = None
    version: int
    status: str
    config_payload: Dict[str, Any]
    reason: Optional[str] = None
    changed_by_id: uuid.UUID
    changed_by_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConfigRollbackRequest(BaseModel):
    reason: str


# -------------------------------------------------------------------------
# Super Admin Data Correction Schemas
# -------------------------------------------------------------------------
class DataCorrectionRequest(BaseModel):
    entity_type: str # JOB_CARD | CALL | COMPLAINT | USER | CUSTOMER
    entity_id: str
    field_updates: Dict[str, Any]
    reason: str # Mandatory audit justification


class DataCorrectionResponse(BaseModel):
    success: bool
    entity_type: str
    entity_id: str
    old_values: Dict[str, Any]
    new_values: Dict[str, Any]
    audit_id: uuid.UUID
    message: str


# -------------------------------------------------------------------------
# Impersonation ("View As User") Schemas
# -------------------------------------------------------------------------
class ImpersonationRequest(BaseModel):
    target_user_id: uuid.UUID
    reason: str = "Administrator simulation"


class ImpersonationResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    impersonated_user: Dict[str, Any]
    real_admin_user_id: uuid.UUID
    message: str

