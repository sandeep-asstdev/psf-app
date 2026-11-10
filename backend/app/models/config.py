"""
================================================================================
FILE PURPOSE: Multi-Tenant Config Versions & Dynamic Follow-up Programs Models.
Defines version-controlled configuration payloads (programs, rules, scales, labels)
and configurable FollowUpProgram definitions per brand / dealership.
================================================================================
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.crypto import uuid7


class ConfigVersion(Base):
    __tablename__ = "config_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="DEALERSHIP") # DEALERSHIP | BRAND
    scope_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True) # brand_id or tenant_id
    config_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # PROGRAMS | RULES | QUESTIONS | SCALES | LABELS | SETTINGS
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", index=True) # DRAFT | PUBLISHED | ARCHIVED
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    creator = relationship("User", foreign_keys=[created_by])
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_config_versions_lookup", "tenant_id", "scope", "scope_id", "config_type", "status"),
        Index("uq_config_versions_ver", "tenant_id", "scope", "scope_id", "config_type", "version", unique=True),
    )


class FollowUpProgram(Base):
    __tablename__ = "follow_up_programs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False) # PSF | TNPS | HAPPINESS
    label: Mapped[str] = mapped_column(String(100), nullable=False) # UI Program Label
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    trigger: Mapped[str] = mapped_column(String(50), nullable=False, default="ON_IMPORT") # ON_IMPORT | AFTER_DAYS(n) | AFTER_COMPLAINT_CLOSURE
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="PHONE") # PHONE | WHATSAPP | BOTH
    questionnaire_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("questionnaires.id", ondelete="SET NULL"), nullable=True)
    rating_scale_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("rating_scales.id", ondelete="SET NULL"), nullable=True)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    retry_gap_hours: Mapped[int] = mapped_column(Integer, default=24)
    sla_hours: Mapped[int] = mapped_column(Integer, default=48)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    brand = relationship("Brand", foreign_keys=[brand_id])
    questionnaire = relationship("Questionnaire", foreign_keys=[questionnaire_id])
    rating_scale = relationship("RatingScale", foreign_keys=[rating_scale_id])

    __table_args__ = (
        Index("ix_follow_up_programs_tenant_brand_order", "tenant_id", "brand_id", "sort_order"),
    )
