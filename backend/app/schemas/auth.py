import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_info: Optional[str] = "Web Browser"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    tenant_id: uuid.UUID
    tenant_name: str
    permissions: List[str]


class UserScopeSchema(BaseModel):
    id: uuid.UUID
    brand_id: Optional[uuid.UUID] = None
    brand_name: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None
    branch_name: Optional[str] = None

    class Config:
        from_attributes = True


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    employee_id: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    role_id: uuid.UUID
    role_name: str
    permissions: List[str]
    tenant_id: uuid.UUID
    tenant_name: str
    tenant_slug: str
    primary_color: str
    scopes: List[UserScopeSchema]
    active_shift_login: Optional[datetime] = None


class LoginLogSchema(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: Optional[str] = None
    role_name: Optional[str] = None
    login_at: datetime
    logout_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    status: str

    class Config:
        from_attributes = True
