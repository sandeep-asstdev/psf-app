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
    permissions: List[str]
    is_system: bool

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
