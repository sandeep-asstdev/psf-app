"""
================================================================================
FILE PURPOSE: System Audit Logs & Enterprise Data Correction Records.
Defines database tables for tracking every sensitive action taken in the system (AuditLog),
such as user role changes, supervisor data corrections, and allocation modifications.

KEY RESPONSIBILITIES:
- AuditLog: captures actor_id, IP address, action name, before_state JSON, and after_state JSON.
- Ensures tamper-evident compliance for dealership audits and Super Admin security reviews.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: AuditLog table growing large in production
  -> Cause: High transaction volume creating thousands of audit entries.
  -> What should you do: Set up automated archival for audit records older than 180 days.
================================================================================
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Integer, BigInteger, SmallInteger, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.crypto import uuid7


class RatingScale(Base):
    __tablename__ = "rating_scales"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. "Hyundai Rating Scale", "Tata Rating Scale", "MG Rating Scale"
    max_rating: Mapped[int] = mapped_column(SmallInteger, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    brand = relationship("Brand")
    bands: Mapped[List["RatingScaleBand"]] = relationship(back_populates="scale", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uq_rating_scales_tenant_brand", "tenant_id", "brand_id", unique=True),
    )


class RatingScaleBand(Base):
    __tablename__ = "rating_scale_bands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    scale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rating_scales.id", ondelete="CASCADE"), nullable=False, index=True)
    min_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    max_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "Delight", "Satisfied", "Average", "Poor", "Dissatisfied"
    derived_case_status: Mapped[str] = mapped_column(String(50), nullable=False) # Delight, Satisfied, Non-Delight, Dissatisfied
    is_delight: Mapped[bool] = mapped_column(Boolean, default=False)
    is_complaint_trigger: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scale: Mapped["RatingScale"] = relationship(back_populates="bands")

    __table_args__ = (
        Index("ix_scale_bands_scale_scores", "scale_id", "min_score", "max_score"),
    )


class TNPSCall(Base):
    __tablename__ = "tnps_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)
    job_card_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    conducted_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    brand_recommend_score: Mapped[int] = mapped_column(SmallInteger, nullable=False) # 0 to 10
    workshop_recommend_score: Mapped[int] = mapped_column(SmallInteger, nullable=False) # 0 to 10
    voc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    document_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    call: Mapped["Call"] = relationship(foreign_keys=[call_id])
    job_card: Mapped["JobCard"] = relationship(foreign_keys=[job_card_id])
    conducted_by: Mapped["User"] = relationship(foreign_keys=[conducted_by_id])

    __table_args__ = (
        Index("ix_tnps_calls_tenant_job", "tenant_id", "job_card_id"),
    )


class AdvisorCall(Base):
    __tablename__ = "advisor_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)
    job_card_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    advisor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    adv_call_status: Mapped[str] = mapped_column(String(50), nullable=False)
    adv_case_status: Mapped[str] = mapped_column(String(50), nullable=False)
    adv_voc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    adv_status: Mapped[str] = mapped_column(String(40), default="PENDING")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    call: Mapped["Call"] = relationship(foreign_keys=[call_id])
    job_card: Mapped["JobCard"] = relationship(foreign_keys=[job_card_id])
    advisor: Mapped["User"] = relationship(foreign_keys=[advisor_id])

    __table_args__ = (
        Index("ix_advisor_calls_tenant_advisor", "tenant_id", "advisor_id"),
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False) # COMPLAINT | JOB_CARD | CALL | RECONFIRMATION
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    uploaded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_documents_tenant_entity", "tenant_id", "entity_type", "entity_id"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Mandatory for data correction and config adjustments
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User")

    __table_args__ = (
        Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),
    )


class CustomFieldDefinition(Base):
    __tablename__ = "custom_field_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False) # JOB_CARD | CALL | COMPLAINT
    field_key: Mapped[str] = mapped_column(String(60), nullable=False)
    field_label: Mapped[str] = mapped_column(String(100), nullable=False)
    field_type: Mapped[str] = mapped_column(String(30), default="TEXT") # TEXT | NUMBER | SELECT | DATE | BOOLEAN
    options: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("uq_custom_fields_tenant_entity_key", "tenant_id", "entity_type", "field_key", unique=True),
    )


class ImportMappingTemplate(Base):
    __tablename__ = "import_mapping_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    column_mapping: Mapped[dict] = mapped_column(JSONB, nullable=False) # e.g. {"Job Card No": "job_card_no"}
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("uq_import_templates_tenant_name", "tenant_id", "name", unique=True),
    )


class ConfigChangeHistory(Base):
    __tablename__ = "config_change_histories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    config_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True) # QUESTIONNAIRE | ROLE_MATRIX | DROPDOWN_MASTERS | SETTINGS | CUSTOM_FIELDS
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="PUBLISHED", index=True) # DRAFT | PUBLISHED | ROLLED_BACK
    config_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    changed_by = relationship("User")

    __table_args__ = (
        Index("ix_config_history_tenant_type_ver", "tenant_id", "config_type", "version"),
    )
