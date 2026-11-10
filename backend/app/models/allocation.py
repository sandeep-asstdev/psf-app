"""
================================================================================
FILE PURPOSE: Automatic Call Allocation Runs, Attendance Overrides & Audit Records.
Defines database tables tracking every automatic allocation batch (AllocationRun),
item-by-item caller assignments (AllocationAssignment), attendance overrides (AttendanceOverride),
and fair-rotation cursor pointers (AllocationCursor).

KEY RESPONSIBILITIES:
- AllocationRun: logs who triggered the allocation, strategy used, present CRE count, and total items.
- AllocationAssignment: maps each queue item to the CRE it was assigned to, enabling 15-minute undo.
- AttendanceOverride: stores manual 'Present' or 'On Leave' marks set by the CRE Admin.
- AllocationCursor: remembers the last CRE who received an extra remainder item to ensure long-term fairness.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Allocation undo button fails with 'Undo window expired' or 'Already attempted'
  -> Cause: Undo was clicked after the 15-minute grace window or a CRE already placed a call to one of the customers.
  -> What should you do: Untouched calls can still be manually reassigned in bulk using the bulk reassignment tool on the PSF table.
================================================================================
"""
import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Boolean, DateTime, Date, Integer, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.crypto import uuid7


class AttendanceOverride(Base):
    __tablename__ = "attendance_overrides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)  # PRESENT | ABSENT | ON_LEAVE
    marked_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    marked_by: Mapped["User"] = relationship("User", foreign_keys=[marked_by_id])

    __table_args__ = (
        Index("uq_attendance_overrides_tenant_user_date", "tenant_id", "user_id", "attendance_date", unique=True),
        Index("ix_attendance_overrides_date", "attendance_date"),
    )


class AllocationRun(Base):
    __tablename__ = "allocation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    import_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    run_type: Mapped[str] = mapped_column(String(40), default="IMPORT_ALLOCATION")  # IMPORT_ALLOCATION | REBALANCE | AUTO_LOGIN_ALLOCATION | LOGOUT_REDISTRIBUTE
    strategy: Mapped[str] = mapped_column(String(40), default="EQUAL_PRESENT_CRE")  # EQUAL_PRESENT_CRE | ROUND_ROBIN | BY_BRANCH | MANUAL
    present_cre_count: Mapped[int] = mapped_column(Integer, default=0)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    allocated_items: Mapped[int] = mapped_column(Integer, default=0)
    unallocated_items: Mapped[int] = mapped_column(Integer, default=0)
    started_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    undone_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    undone_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    started_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[started_by_id])
    undone_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[undone_by_id])
    assignments: Mapped[List["AllocationAssignment"]] = relationship("AllocationAssignment", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_allocation_runs_tenant_created", "tenant_id", "created_at"),
    )


class AllocationAssignment(Base):
    __tablename__ = "allocation_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("allocation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    queue_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("followup_queues.id", ondelete="CASCADE"), nullable=False, index=True)
    from_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reason: Mapped[str] = mapped_column(String(50), default="IMPORT_EQUAL_SPLIT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped["AllocationRun"] = relationship("AllocationRun", back_populates="assignments")
    queue_item: Mapped["FollowupQueue"] = relationship("FollowupQueue")
    from_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[from_user_id])
    to_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[to_user_id])


class AllocationCursor(Base):
    __tablename__ = "allocation_cursors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    pool_key: Mapped[str] = mapped_column(String(60), nullable=False)  # DEFAULT or BRANCH_<uuid>
    last_cre_index: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("uq_allocation_cursors_tenant_pool", "tenant_id", "pool_key", unique=True),
    )

