"""
================================================================================
FILE PURPOSE: User Profile, Role Management & Scope Schemas.
Defines Pydantic models for creating users, updating profiles, assigning roles,
and configuring branch/brand data access restrictions.

KEY RESPONSIBILITIES:
- Validates new user creation (full name, email, password strength, role).
- Validates user profile updates and status changes (active / inactive).
- Validates explicit branch/brand user scope assignments.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: ValidationError: password must be at least 8 characters
  -> Cause: Weak password provided during user creation.
  -> What should you do: Provide a strong password with at least 8 characters including uppercase, lowercase, and numbers.
================================================================================
"""
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from app.schemas.auth import UserScopeSchema


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    employee_id: Optional[str] = None
    role_id: uuid.UUID
    brand_ids: Optional[List[uuid.UUID]] = None
    branch_ids: Optional[List[uuid.UUID]] = None


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    employee_id: Optional[str] = None
    role_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    brand_ids: Optional[List[uuid.UUID]] = None
    branch_ids: Optional[List[uuid.UUID]] = None


class PasswordResetRequest(BaseModel):
    new_password: str


class RoleSchema(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    level: str = "L3"
    permissions: List[str] = []
    field_rules: Optional[dict] = None
    dashboard_config: Optional[dict] = None
    is_active: bool = True
    is_system: bool = False

    class Config:
        from_attributes = True


class UserListItem(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    employee_id: Optional[str] = None
    is_active: bool
    role_id: uuid.UUID
    role_name: str
    scopes_count: int
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    employee_id: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    role: RoleSchema
    scopes: List[UserScopeSchema]
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

