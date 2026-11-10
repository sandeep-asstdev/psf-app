"""
================================================================================
FILE PURPOSE: Dynamic Customer Survey Questionnaires & OEM Rating Scales.
Defines database tables for brand-specific survey templates (Questionnaire), survey questions,
answer choices, and recorded customer responses (SurveyResponse).

KEY RESPONSIBILITIES:
- Questionnaire: OEM survey template (e.g. Hyundai 4-Question Survey, Tata 7-Question Survey).
- Question: question text, answer type (RATING_5, RATING_10, YES_NO, TEXT), mandatory flag.
- SurveyResponse: stores the customer's actual ratings, CSAT score, and NPS classification (Promoter, Passive, Detractor).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Questionnaire not showing in Call Console
  -> Cause: No active questionnaire exists for the job card's brand and queue type.
  -> What should you do: Run `docker exec psf_api python -m app.db.seed_questionnaires` to seed default OEM survey templates.
================================================================================
"""
import uuid
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, Integer, Numeric, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.crypto import uuid7
from app.models.tenant import Brand


class Questionnaire(Base):
    __tablename__ = "questionnaires"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False) # PSF | TNPS | HAPPINESS | RECONFIRMATION
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="PUBLISHED", index=True) # DRAFT | PUBLISHED | ARCHIVED
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    brand: Mapped["Brand"] = relationship()
    questions: Mapped[List["Question"]] = relationship(back_populates="questionnaire", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uq_questionnaires_tenant_brand_type_ver", "tenant_id", "brand_id", "type", "version", unique=True),
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    questionnaire_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("questionnaires.id", ondelete="CASCADE"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    legacy_label: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Exact wording in legacy sheet / dropdown
    type: Mapped[str] = mapped_column(String(40), nullable=False) # rating_5 | nps_10 | yes_no | yes_no_na | single_select | multi_select | text | number
    answer_type: Mapped[str] = mapped_column(String(40), default="YES_NO") # Configurable per question: YES_NO | YES_NO_NA | RATING_10 | RATING_5 | TEXT
    section: Mapped[str] = mapped_column(String(80), default="General")
    options: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    show_if: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    weight: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=1.0)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    questionnaire: Mapped["Questionnaire"] = relationship(back_populates="questions")

    __table_args__ = (
        Index("ix_questions_questionnaire_order", "questionnaire_id", "display_order"),
    )
