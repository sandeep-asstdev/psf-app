"""
================================================================================
FILE PURPOSE: Authentication, Roles, Shift Attendance & User Scopes.
Defines database tables for User accounts, security Roles (Super Admin, CRE Admin, CRE),
RolePermissions (action + data scope), LoginLogs (attendance shift tracking), and UserScopes.

KEY RESPONSIBILITIES:
- User: personnel details, email, hashed password, role link, active shift status.
- Role & RolePermission: granular permission definitions and max scopes.
- LoginLog: daily punch-in / punch-out attendance records with duration tracking.
- UserScope: explicit brand or branch restrictions assigned to specific users.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: User not showing as 'Present' on attendance screen
  -> Cause: The user does not have an open LoginLog session for today (logout_at is not NULL or session is from previous day).
  -> What should you do: Log in with that user to start an active shift session, or manually mark them Present in the CRE Presence panel.
================================================================================
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.crypto import uuid7


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    level: Mapped[str] = mapped_column(String(20), default="L3") # L1: SUPER ADMIN, L2: CRE ADMIN, L3: BRANCH LEVEL
    permissions: Mapped[list] = mapped_column(JSONB, default=list) # Legacy permission list for backward compatibility
    dashboard_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True) # Role dashboard widget & menu config
    field_rules: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True) # Field-level visibility/masking rules
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users: Mapped[List["User"]] = relationship(back_populates="role")
    role_permissions: Mapped[List["RolePermission"]] = relationship(back_populates="role", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uq_roles_tenant_name", "tenant_id", "name", unique=True),
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(80), nullable=False, index=True) # e.g. brand.manage, call.allocate, etc.
    data_scope: Mapped[str] = mapped_column(String(40), default="ALL") # ALL | DEALERSHIP | ASSIGNED_BRANCHES | OWN
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    role: Mapped["Role"] = relationship(back_populates="role_permissions")

    __table_args__ = (
        Index("uq_role_permissions_tenant_role_perm", "tenant_id", "role_id", "permission", unique=True),
        Index("ix_role_permissions_role_perm", "role_id", "permission"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(150), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Encrypted
    phone_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True) # HMAC-SHA256 for lookup
    employee_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    role: Mapped["Role"] = relationship(back_populates="users")
    tenant: Mapped["Tenant"] = relationship()
    scopes: Mapped[List["UserScope"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    login_logs: Mapped[List["LoginLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uq_users_tenant_email", "tenant_id", "email", unique=True),
        Index("ix_users_tenant_active", "tenant_id", "is_active"),
    )


class UserScope(Base):
    __tablename__ = "user_scopes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=True)
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="scopes")

    __table_args__ = (
        Index("uq_user_scopes_unique", "user_id", "brand_id", "branch_id", unique=True),
    )


class LoginLog(Base):
    __tablename__ = "login_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    logout_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    device_info: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="SUCCESS")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="login_logs")

    __table_args__ = (
        Index("ix_login_logs_tenant_user_login", "tenant_id", "user_id", "login_at"),
        Index("ix_login_logs_tenant_login", "tenant_id", "login_at"),
    )
