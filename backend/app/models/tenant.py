"""
================================================================================
FILE PURPOSE: Multi-Tenant Hierarchy & Dealership Masters (Tenant, Brand, Branch, Workshop).
Defines database tables representing dealership organizations, automobile manufacturer brands
(e.g. Hyundai, Tata, MG), and individual dealer branch workshop locations.

KEY RESPONSIBILITIES:
- Tenant model: Represents the dealership group (multi-tenant boundary).
- Brand model: Represents OEM brands with OEM codes, colors, and logos.
- Branch model: Represents dealership physical service centers with phone, address, and brand link.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: IntegrityError: duplicate key value violates unique constraint 'uq_branch_code'
  -> Cause: Attempted to create a branch with a code that already exists.
  -> What should you do: Choose a unique branch code in the Admin Console or verify existing branch codes.
================================================================================
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.crypto import uuid7


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(20), default="#2563EB")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    brands: Mapped[List["Brand"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    branches: Mapped[List["Branch"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    settings: Mapped[List["Setting"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="brands")
    branches: Mapped[List["Branch"]] = relationship(back_populates="brand", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uq_brands_tenant_code", "tenant_id", "code", unique=True),
        Index("ix_brands_tenant_active", "tenant_id", "is_active"),
    )


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    dms_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True) # e.g. S8211 (Hubli), S8827 (Gadag)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True) # Flagged if brand mapping is ambiguous
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Encrypted
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="branches")
    brand: Mapped[Optional["Brand"]] = relationship(back_populates="branches")
    contacts: Mapped[List["BranchContact"]] = relationship(back_populates="branch", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uq_branches_tenant_code", "tenant_id", "code", unique=True),
        Index("ix_branches_tenant_dms", "tenant_id", "dms_code"),
        Index("ix_branches_tenant_active", "tenant_id", "is_active"),
    )


class BranchContact(Base):
    __tablename__ = "branch_contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), default="SERVICE_MANAGER") # e.g. SERVICE_MANAGER
    name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Encrypted at rest
    phone_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    notify_on: Mapped[str] = mapped_column(String(100), default="complaint,low_rating") # complaint | low_rating | daily_summary
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    branch: Mapped["Branch"] = relationship(back_populates="contacts")

    __table_args__ = (
        Index("ix_branch_contacts_tenant_branch", "tenant_id", "branch_id"),
    )


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    config_key: Mapped[str] = mapped_column(String(80), nullable=False)
    config_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="settings")

    __table_args__ = (
        Index("uq_settings_tenant_key", "tenant_id", "config_key", unique=True),
    )
