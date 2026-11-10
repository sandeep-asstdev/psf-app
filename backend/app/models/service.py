"""
================================================================================
FILE PURPOSE: Workshop Service Job Cards & Service Advisor Records.
Defines database tables representing real workshop service visits (JobCard),
assigned Service Advisors, and technicians who worked on the customer's vehicle.

KEY RESPONSIBILITIES:
- JobCard: job card number, service date, invoice amount, service type, advisor link, vehicle link.
- ServiceAdvisor: advisor name, employee code, active status, branch link.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Job card not linking to branch or brand
  -> Cause: The branch_id or brand_id foreign key in JobCard was passed as NULL.
  -> What should you do: Ensure the DMS import template correctly resolves Brand and Branch before creating the job card.
================================================================================
"""
import uuid
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, Date, Integer, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.crypto import uuid7


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True)
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0)
    success_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_log: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    job_cards: Mapped[List["JobCard"]] = relationship(back_populates="import_batch")
    uploader: Mapped["User"] = relationship(foreign_keys=[uploaded_by])
    brand: Mapped["Brand"] = relationship(foreign_keys=[brand_id])
    branch: Mapped[Optional["Branch"]] = relationship(foreign_keys=[branch_id])

    __table_args__ = (
        Index("ix_import_batches_tenant_status_created", "tenant_id", "status", "created_at"),
    )


class JobCard(Base):
    __tablename__ = "job_cards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    import_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("import_batches.id"), nullable=True)
    job_card_no: Mapped[str] = mapped_column(String(60), nullable=False)
    job_card_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    service_advisor_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    service_advisor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    technician_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    service_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0.00)
    odometer_reading: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    promised_delivery_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_delivery_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    legacy_tnps_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    uploaded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    import_batch: Mapped[Optional["ImportBatch"]] = relationship(back_populates="job_cards")
    brand: Mapped["Brand"] = relationship(foreign_keys=[brand_id])
    branch: Mapped["Branch"] = relationship(foreign_keys=[branch_id])
    customer: Mapped["Customer"] = relationship(foreign_keys=[customer_id])
    vehicle: Mapped["Vehicle"] = relationship(foreign_keys=[vehicle_id])
    service_advisor: Mapped[Optional["User"]] = relationship(foreign_keys=[service_advisor_id])
    followup_queues: Mapped[List["FollowupQueue"]] = relationship(back_populates="job_card", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uq_job_cards_tenant_branch_no", "tenant_id", "branch_id", "job_card_no", unique=True),
        Index("ix_job_cards_tenant_branch_date", "tenant_id", "branch_id", "job_card_date"),
        Index("ix_job_cards_tenant_advisor", "tenant_id", "service_advisor_id"),
        Index("ix_job_cards_tenant_customer", "tenant_id", "customer_id"),
    )


class ServiceType(Base):
    __tablename__ = "service_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    behaviour_flags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("uq_service_types_tenant_code", "tenant_id", "code", unique=True),
    )

