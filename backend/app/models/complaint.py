"""
================================================================================
FILE PURPOSE: Customer Complaints, Escalations & SLA Tracking.
Defines database tables for customer grievances (Complaint), complaint categories,
and resolution action history (ComplaintAction). Enforces dealership SLA deadlines.

KEY RESPONSIBILITIES:
- Complaint: ticket number, description, category, severity, status (OPEN, IN_PROGRESS, RESOLVED, CLOSED).
- ComplaintAction: audit history of comments, status changes, and root causes added by managers.
- ComplaintCategory: category taxonomy (e.g. Wash Quality, Overcharging, Delay, Advisor Rude).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Complaint status stuck on SLA Breached
  -> Cause: The complaint was not resolved before target_resolution_at timestamp.
  -> What should you do: Assign the complaint to a Service Advisor or Service Manager and record a resolution action in the Complaints tab.
================================================================================
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.crypto import uuid7


class ComplaintCategory(Base):
    __tablename__ = "complaint_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    legacy_label: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(20), nullable=True) # separate emoji icon from name
    default_sla_hours: Mapped[int] = mapped_column(Integer, default=24)
    severity_level: Mapped[str] = mapped_column(String(30), default="MEDIUM")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    complaints: Mapped[List["Complaint"]] = relationship(back_populates="category")

    __table_args__ = (
        Index("uq_complaint_cat_tenant_name", "tenant_id", "name", unique=True),
    )


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    job_card_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    call_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complaint_categories.id"), nullable=False, index=True)
    complaint_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(30), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(40), default="Open", index=True) # Open | Closed in Time | Closed Late | Assigned | In Progress | Resolved | Reopened
    description: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    sla_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_sla_breached: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolution_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    category: Mapped["ComplaintCategory"] = relationship(back_populates="complaints")
    branch: Mapped["Branch"] = relationship(foreign_keys=[branch_id])
    job_card: Mapped["JobCard"] = relationship(foreign_keys=[job_card_id])
    assigned_to: Mapped[Optional["User"]] = relationship(foreign_keys=[assigned_to_id])
    events: Mapped[List["ComplaintEvent"]] = relationship(back_populates="complaint", cascade="all, delete-orphan")
    reconfirmations: Mapped[List["Reconfirmation"]] = relationship(back_populates="complaint", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_complaints_tenant_branch_status_sla", "tenant_id", "branch_id", "status", "sla_due_at"),
        Index("ix_complaints_tenant_assigned_status", "tenant_id", "assigned_to_id", "status"),
    )


class ComplaintEvent(Base):
    __tablename__ = "complaint_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    complaint_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    performed_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False) # CREATED | ASSIGNED | STATUS_CHANGE | COMMENT_ADDED | SLA_ESCALATED | RESOLVED | REOPENED | CLOSED
    from_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    to_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    complaint: Mapped["Complaint"] = relationship(back_populates="events")

    __table_args__ = (
        Index("ix_complaint_events_complaint_created", "complaint_id", "created_at"),
    )


class Reconfirmation(Base):
    __tablename__ = "reconfirmations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    complaint_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    conducted_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reconfirmation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="SATISFIED_CLOSED") # SATISFIED_CLOSED | UNSATISFIED_REOPENED
    call_status: Mapped[str] = mapped_column(String(50), default="Connected")
    customer_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    closure_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    complaint: Mapped["Complaint"] = relationship(back_populates="reconfirmations")
    conducted_by: Mapped["User"] = relationship(foreign_keys=[conducted_by_id])

    __table_args__ = (
        Index("ix_reconfirmations_tenant_complaint", "tenant_id", "complaint_id"),
    )
