"""
================================================================================
FILE PURPOSE: PSF Calling Workspace, Dashboard & Call Console Schemas.
Defines Pydantic models for high-level calling KPIs, calling queue line items,
customer dossiers for the calling dialer modal, and call submission logs.

KEY RESPONSIBILITIES:
- Formats dashboard counters (total pending, contacted, connect rate, open complaints).
- Formats line items spreadsheet rows with masked phone numbers and assigned caller tags.
- Validates call submission logs (call status, sentiment, VOC, survey ratings, complaint escalation).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: ValidationError: call_status is required
  -> Cause: Call console modal submitted without selecting a call outcome (e.g. Connected, Busy, Not Connected).
  -> What should you do: Ensure the caller selects an outcome button before clicking Submit.
================================================================================
"""
import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.questionnaire import QuestionnaireDetailResponse


class PsfDashboardStats(BaseModel):
    total_pending: int = 0
    total_contacted: int = 0
    connect_rate_pct: float = 0.0
    open_complaints_count: int = 0
    reminders_today_count: int = 0
    by_brand_branch: List[Dict[str, Any]] = []
    by_call_status: List[Dict[str, Any]] = []
    open_complaints_by_branch: List[Dict[str, Any]] = []
    closed_complaints_by_branch: List[Dict[str, Any]] = []
    by_advisor: List[Dict[str, Any]] = []
    by_assigned_cre: List[Dict[str, Any]] = []
    tnps_calls_by_branch: List[Dict[str, Any]] = []
    unassigned_count: int = 0
    nps_score: Optional[float] = None
    promoters_count: Optional[int] = 0
    passives_count: Optional[int] = 0
    detractors_count: Optional[int] = 0
    nps_respondents: Optional[int] = 0


class FollowupQueueListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_card_id: uuid.UUID
    job_card_no: str
    job_card_date: date
    total_amount: Decimal
    customer_id: uuid.UUID
    customer_name: str
    customer_phone_masked: str
    customer_phone_raw: Optional[str] = None
    vehicle_reg_no: str
    vehicle_model: str
    brand_id: uuid.UUID
    brand_name: str
    brand_code: str
    brand_color: Optional[str] = None
    branch_id: uuid.UUID
    branch_name: str
    service_advisor: Optional[str] = None
    queue_type: str
    status: str
    attempts: int
    last_attempt_at: Optional[datetime] = None
    due_at: datetime
    assigned_to_id: Optional[uuid.UUID] = None
    assigned_to_name: Optional[str] = None
    last_call_status: Optional[str] = None
    last_case_status: Optional[str] = None
    vin_no: Optional[str] = None
    brand_logo_url: Optional[str] = None
    service_type: Optional[str] = None
    technician_name: Optional[str] = None
    voc: Optional[str] = None
    contacted_count: int = 0
    followup_timestamp: Optional[datetime] = None


class CallConsoleDetails(BaseModel):
    queue: FollowupQueueListItem
    customer: Dict[str, Any]
    vehicle: Dict[str, Any]
    job_card: Dict[str, Any]
    call_history: List[Dict[str, Any]] = []
    questionnaire: Optional[QuestionnaireDetailResponse] = None
    next_queue_id: Optional[uuid.UUID] = None


class SubmitCallRequest(BaseModel):
    followup_queue_id: uuid.UUID
    call_status: str = Field(..., description="Connected | Not Connected | Busy | Switched Off | Wrong Number | Callback Requested")
    case_status: str = Field("Satisfied", description="Satisfied | Dissatisfied | Complaint Registered | Callback Requested | Closed")
    duration_seconds: int = 0
    voc: Optional[str] = None
    survey_answers: Optional[Dict[str, Any]] = None
    has_complaint: bool = False
    complaint_category_id: Optional[uuid.UUID] = None
    complaint_severity: Optional[str] = "MEDIUM"
    complaint_description: Optional[str] = None
    complaint_assigned_to_id: Optional[uuid.UUID] = None
    callback_at: Optional[datetime] = None
    callback_note: Optional[str] = None


class SubmitCallResponse(BaseModel):
    call_id: uuid.UUID
    queue_id: uuid.UUID
    queue_status: str
    csat_score: Optional[Decimal] = None
    nps_score: Optional[int] = None
    nps_category: Optional[str] = None
    complaint_ticket_no: Optional[str] = None
    next_queue_id: Optional[uuid.UUID] = None


class BulkAssignRequest(BaseModel):
    queue_ids: List[uuid.UUID]
    assigned_to_id: Optional[uuid.UUID] = None


class CallAttemptResponse(BaseModel):
    id: uuid.UUID
    followup_queue_id: uuid.UUID
    attempt_number: int
    call_status: str
    case_status: Optional[str] = None
    voc: Optional[str] = None
    rating: Optional[int] = None
    called_by_id: Optional[uuid.UUID] = None
    called_by_name: Optional[str] = None
    called_at: datetime
    duration_seconds: int = 0

    class Config:
        from_attributes = True


