"""
================================================================================
FILE PURPOSE: Follow-up Calling Queues, Call Records & Customer Sentiments.
Defines database tables for calling queue tasks (FollowupQueue), individual phone call records (Call),
call attempts history (CallAttempt), scheduled customer call-back reminders (Reminder),
and post-service sentiment logs.

KEY RESPONSIBILITIES:
- FollowupQueue: tracks calling status (PENDING, CONTACTED, CALLBACK_REQUESTED), assigned CRE caller, and due dates.
- Call & CallAttempt: logs each call timestamp, duration, sentiment (Delight, Satisfied, Dissatisfied), and VOC (Voice of Customer).
- Reminder: stores callback notifications requested by customers.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Call queue item stuck in PENDING status after submitting call
  -> Cause: The call submission did not update queue.status to CONTACTED or NOT_CONTACTED.
  -> What should you do: Check the call submission payload in the Call Console modal to ensure a valid call_status was provided.
================================================================================
"""
import uuid
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, Date, Integer, Numeric, SmallInteger, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.crypto import uuid7


class CallStatus(Base):
    __tablename__ = "call_statuses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. Connected, Not Connected
    category: Mapped[str] = mapped_column(String(40), default="SENTIMENT") # SENTIMENT | CONTACT_FAILED | INVALID | DEFERRED
    counts_as_contacted: Mapped[bool] = mapped_column(Boolean, default=False)
    closes_followup: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("uq_call_statuses_tenant_name", "tenant_id", "name", unique=True),
    )


class CaseStatus(Base):
    __tablename__ = "case_statuses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. Delight, Non-Delight, Satisfied, Dissatisfied, No Response...
    category: Mapped[str] = mapped_column(String(40), default="SENTIMENT") # SENTIMENT | CONTACT_FAILED | INVALID | DEFERRED
    counts_as_contacted: Mapped[bool] = mapped_column(Boolean, default=False)
    closes_followup: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("uq_case_statuses_tenant_name", "tenant_id", "name", unique=True),
    )


class FollowupQueue(Base):
    __tablename__ = "followup_queues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    job_card_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("follow_up_programs.id", ondelete="SET NULL"), nullable=True, index=True)
    queue_type: Mapped[str] = mapped_column(String(40), nullable=False) # PSF | TNPS | HAPPINESS | RECONFIRMATION | ADVISOR
    status: Mapped[str] = mapped_column(String(40), default="PENDING") # PENDING | IN_PROGRESS | CONTACTED | NOT_CONTACTED | CALLBACK_REQUESTED | CLOSED_MAX_ATTEMPTS
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    contacted_count: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_followup_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    calls: Mapped[List["Call"]] = relationship(back_populates="queue", cascade="all, delete-orphan")
    attempts_log: Mapped[List["CallAttempt"]] = relationship(back_populates="queue", cascade="all, delete-orphan")
    reminders: Mapped[List["Reminder"]] = relationship(back_populates="queue", cascade="all, delete-orphan")
    job_card: Mapped["JobCard"] = relationship(back_populates="followup_queues", foreign_keys=[job_card_id])
    assigned_to: Mapped[Optional["User"]] = relationship(foreign_keys=[assigned_to_id])

    __table_args__ = (
        Index("ix_followup_queues_tenant_type_status_due", "tenant_id", "queue_type", "status", "due_at"),
        Index("ix_followup_queues_tenant_assigned_status_due", "tenant_id", "assigned_to_id", "status", "due_at"),
    )


class CallAttempt(Base):
    __tablename__ = "call_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    followup_queue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("followup_queues.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    call_status: Mapped[str] = mapped_column(String(50), nullable=False) # Connected | Not Connected
    case_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # Delight, No Response, etc.
    voc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    called_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    called_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)

    queue: Mapped["FollowupQueue"] = relationship(back_populates="attempts_log")
    called_by: Mapped[Optional["User"]] = relationship(foreign_keys=[called_by_id])

    __table_args__ = (
        Index("ix_call_attempts_queue_attempt", "followup_queue_id", "attempt_number"),
    )


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    followup_queue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("followup_queues.id", ondelete="CASCADE"), nullable=False, index=True)
    job_card_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    called_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    called_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    phone_dialed: Mapped[str] = mapped_column(String(255), nullable=False) # Encrypted
    call_status: Mapped[str] = mapped_column(String(50), nullable=False) # Connected, Not Connected, Busy, Switched Off, etc.
    case_status: Mapped[str] = mapped_column(String(50), nullable=False) # Satisfied, Dissatisfied, Complaint Registered, etc.
    voc: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Voice of Customer
    alt_contact_used: Mapped[bool] = mapped_column(Boolean, default=False)
    recording_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    queue: Mapped["FollowupQueue"] = relationship(back_populates="calls")
    caller: Mapped["User"] = relationship(foreign_keys=[called_by_id])
    job_card: Mapped["JobCard"] = relationship(foreign_keys=[job_card_id])
    survey_responses: Mapped[List["SurveyResponse"]] = relationship(back_populates="call", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_calls_tenant_called_at", "tenant_id", "called_at"),
        Index("ix_calls_tenant_caller_date", "tenant_id", "called_by_id", "called_at"),
    )


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)
    job_card_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    questionnaire_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("questionnaires.id"), nullable=False, index=True)
    questionnaire_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False) # Dynamic answers payload
    csat_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    nps_score: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    nps_category: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True) # PROMOTER | PASSIVE | DETRACTOR
    channel: Mapped[str] = mapped_column(String(20), default="PHONE") # PHONE | WHATSAPP
    raw_rating: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    call: Mapped["Call"] = relationship(back_populates="survey_responses")
    questionnaire: Mapped["Questionnaire"] = relationship(foreign_keys=[questionnaire_id])

    __table_args__ = (
        Index("ix_survey_responses_answers_gin", "answers", postgresql_using="gin"),
        Index("ix_survey_responses_tenant_nps", "tenant_id", "nps_category"),
    )


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    followup_queue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("followup_queues.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    queue: Mapped["FollowupQueue"] = relationship(back_populates="reminders")

    __table_args__ = (
        Index("ix_reminders_tenant_user_ack_time", "tenant_id", "assigned_to_id", "is_acknowledged", "remind_at"),
    )
