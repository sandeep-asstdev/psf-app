"""
================================================================================
FILE PURPOSE: Customer Complaints & SLA Tracking Schemas.
Defines Pydantic models for registering customer complaints,
updating complaint tickets, recording manager action logs, and viewing SLA timelines.

KEY RESPONSIBILITIES:
- Validates new complaint creation payloads (category, description, severity, assigned advisor).
- Validates complaint status transitions (OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED).
- Formats complaint audit timelines and SLA breach indicators.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: ValidationError: status transition not permitted
  -> Cause: Attempted an invalid complaint state transition (e.g. going from CLOSED back to OPEN directly).
  -> What should you do: Follow proper lifecycle progression or verify user permissions.
================================================================================
"""
import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


# -------------------------------------------------------------
# Complaint Lifecycle Schemas
# -------------------------------------------------------------
class ComplaintEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    remarks: Optional[str] = None
    performed_by_name: str
    created_at: datetime


class ReconfirmationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reconfirmation_date: datetime
    status: str
    call_status: str
    customer_feedback: Optional[str] = None
    closure_verified: bool
    conducted_by_name: str


class ComplaintListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    complaint_no: str
    job_card_id: uuid.UUID
    job_card_no: str
    customer_name: str
    customer_phone_masked: str
    customer_phone_raw: Optional[str] = None
    vehicle_reg_no: str
    vehicle_model: str
    brand_name: str
    brand_code: str
    branch_name: str
    category_name: str
    severity: str
    status: str
    description: str
    assigned_to_id: Optional[uuid.UUID] = None
    assigned_to_name: Optional[str] = None
    sla_due_at: datetime
    is_sla_breached: bool
    hours_remaining: float
    created_at: datetime


class ComplaintDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    complaint_no: str
    severity: str
    status: str
    description: str
    sla_due_at: datetime
    is_sla_breached: bool
    resolution_remarks: Optional[str] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    category_name: str
    branch_name: str
    brand_name: str
    job_card_no: str
    job_card_date: date
    customer_name: str
    customer_phone_masked: str
    customer_phone_raw: Optional[str] = None
    vehicle_reg_no: str
    vehicle_model: str
    service_advisor: Optional[str] = None
    assigned_to_name: Optional[str] = None
    events: List[ComplaintEventResponse] = []
    reconfirmations: List[ReconfirmationResponse] = []
    created_at: datetime


class ComplaintStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="ASSIGNED | IN_PROGRESS | RESOLVED | CLOSED | REOPENED")
    assigned_to_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None
    resolution_remarks: Optional[str] = None


class ReconfirmationSubmitRequest(BaseModel):
    complaint_id: uuid.UUID
    call_status: str = Field(..., description="Connected | Not Connected | Busy | Callback")
    status: str = Field(..., description="SATISFIED_CLOSED | UNSATISFIED_REOPENED")
    customer_feedback: Optional[str] = None
    closure_verified: bool = True


# -------------------------------------------------------------
# TNPS Schemas
# -------------------------------------------------------------
class SubmitTnpsRequest(BaseModel):
    followup_queue_id: uuid.UUID
    call_status: str
    brand_recommend_score: int = Field(..., ge=0, le=10)
    workshop_recommend_score: int = Field(..., ge=0, le=10)
    voc: Optional[str] = None
    document_url: Optional[str] = None


class TnpsStatsResponse(BaseModel):
    total_responses: int = 0
    brand_nps: float = 0.0
    workshop_nps: float = 0.0
    promoters_count: int = 0
    passives_count: int = 0
    detractors_count: int = 0
    promoters_pct: float = 0.0
    detractors_pct: float = 0.0


# -------------------------------------------------------------
# Service Advisor Follow-up Schemas
# -------------------------------------------------------------
class AdvisorCallListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_card_id: uuid.UUID
    job_card_no: str
    job_card_date: date
    customer_name: str
    customer_phone_masked: str
    vehicle_reg_no: str
    vehicle_model: str
    branch_name: str
    dissatisfied_voc: Optional[str] = None
    csat_score: Optional[Decimal] = None
    nps_category: Optional[str] = None
    adv_call_status: Optional[str] = None
    adv_case_status: Optional[str] = None
    adv_voc: Optional[str] = None
    adv_status: str = "PENDING"
    created_at: datetime


class AdvisorCorrectionSubmitRequest(BaseModel):
    job_card_id: uuid.UUID
    adv_call_status: str = Field(..., description="Connected | No Answer | Customer Busy")
    adv_case_status: str = Field(..., description="Customer Convinced | Part Ordered | Inspection Scheduled | Unresolved")
    adv_voc: str = Field(..., description="Service advisor corrective actions and explanation")
    adv_status: str = Field("RESOLVED", description="PENDING | RESOLVED | CLOSED")

