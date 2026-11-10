"""
================================================================================
FILE PURPOSE: Call Allocation & Attendance Data Schemas.
Defines Pydantic models for automatic call distribution rules,
present CRE summaries, manual attendance overrides, rebalance previews, and undo requests.

KEY RESPONSIBILITIES:
- Validates allocation rules (strategy, pool mode, sticky customer toggle, cursor pointer).
- Formats Present CRE roster items (login status, pending call load, override flags).
- Formats Rebalance and Allocate Now preview diffs (current vs proposed calls).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: ValidationError: Input should be a valid strategy ('EQUAL_PRESENT_CRE', 'ROUND_ROBIN', 'BY_BRANCH', 'MANUAL')
  -> Cause: An invalid allocation strategy name was submitted to the rules endpoint.
  -> What should you do: Select one of the valid enum strategies from the Admin Console dropdown.
================================================================================
"""
import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AttendanceOverrideRequest(BaseModel):
    user_id: uuid.UUID
    attendance_date: Optional[date] = None
    status: str = Field(..., pattern="^(PRESENT|ABSENT|ON_LEAVE)$")
    reason: Optional[str] = None


class AttendanceOverrideResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    attendance_date: date
    status: str
    marked_by_id: uuid.UUID
    marked_by_name: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PresentCreItem(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    role_name: str
    phone: Optional[str] = None
    is_present: bool
    attendance_status: str  # PRESENT | ABSENT | ON_LEAVE
    has_active_login: bool
    login_time: Optional[datetime] = None
    has_override: bool
    override_reason: Optional[str] = None
    marked_by_name: Optional[str] = None
    current_pending: int = 0
    assigned_branches: List[str] = []
    weight: float = 1.0


class PresentCresResponse(BaseModel):
    attendance_date: date
    total_eligible: int
    total_present: int
    total_absent: int
    cres: List[PresentCreItem]


class AllocationRulesConfig(BaseModel):
    strategy: str = "EQUAL_PRESENT_CRE"  # EQUAL_PRESENT_CRE | ROUND_ROBIN | BY_BRANCH | MANUAL
    pool_mode: str = "CRE_POOL"  # CRE_POOL | BRANCH_ONLY
    allocation_trigger_mode: str = "WHEN_MIN_PRESENT"  # IMMEDIATE | SCHEDULED_AT_TIME | WHEN_MIN_PRESENT
    scheduled_time: str = "09:30"  # HH:MM format
    min_present_cres: int = 2  # Minimum present CREs required before auto-allocation triggers
    sticky_customers: bool = True
    balance_total_pending: bool = False
    logout_policy: str = "KEEP"  # KEEP | RETURN_TO_POOL | REDISTRIBUTE_EQUALLY
    undo_window_minutes: int = 15
    weights: Dict[str, float] = Field(default_factory=dict)


class AllocationRunSummary(BaseModel):
    id: uuid.UUID
    run_type: str
    strategy: str
    import_batch_id: Optional[uuid.UUID] = None
    present_cre_count: int
    total_items: int
    allocated_items: int
    unallocated_items: int
    started_by_id: Optional[uuid.UUID] = None
    started_by_name: Optional[str] = None
    summary: Dict[str, Any]
    undone_at: Optional[datetime] = None
    created_at: datetime
    can_undo: bool = False


class RebalancePreviewItem(BaseModel):
    user_id: uuid.UUID
    full_name: str
    current_pending: int
    proposed_pending: int
    net_change: int


class RebalancePreviewResponse(BaseModel):
    total_movable_calls: int
    present_cre_count: int
    items: List[RebalancePreviewItem]


class UnallocatedQueuesResponse(BaseModel):
    total_unallocated: int
    items: List[Dict[str, Any]]


class AllocateNowPreviewItem(BaseModel):
    user_id: uuid.UUID
    full_name: str
    current_pending: int
    allocated_in_this_run: int
    new_total_pending: int


class AllocateNowPreviewResponse(BaseModel):
    total_unallocated_calls: int
    present_cre_count: int
    strategy: str = "EQUAL_PRESENT_CRE"
    items: List[AllocateNowPreviewItem]
    message: Optional[str] = None

