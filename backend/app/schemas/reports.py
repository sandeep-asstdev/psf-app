"""
================================================================================
FILE PURPOSE: Analytics, Performance Reports & Export Schemas.
Defines Pydantic models for dealership executive reports, CRE calling summaries,
branch satisfaction comparisons, and Excel export request filters.

KEY RESPONSIBILITIES:
- Formats date-range filtered report summaries.
- Structures CRE caller productivity metrics (attempted vs contacted counts).
- Defines parameters for generating Excel export reports.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: ValidationError: start_date cannot be greater than end_date
  -> Cause: Selected date filter has an inverted range.
  -> What should you do: Verify the date picker values on the Reports page.
================================================================================
"""
import uuid
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class ReportKpiSummary(BaseModel):
    total_job_cards: int = 0
    total_calls_attempted: int = 0
    total_calls_connected: int = 0
    overall_connect_rate: float = 0.0
    average_csat: float = 0.0
    net_promoter_score: float = 0.0
    open_complaints_count: int = 0
    sla_compliance_rate: float = 0.0
    avg_call_duration_seconds: int = 0


class CsatNpsTrendItem(BaseModel):
    date_label: str
    csat_score: float
    nps_score: float
    calls_count: int


class CreProductivityItem(BaseModel):
    cre_id: Optional[uuid.UUID] = None
    cre_name: str
    calls_attempted: int
    calls_connected: int
    connect_rate: float
    avg_duration_seconds: int
    csat_recorded: float


class AdvisorScorecardItem(BaseModel):
    advisor_name: str
    branch_name: str
    total_jobs: int
    csat_score: float
    promoters_count: int
    detractors_count: int
    open_complaints: int
    resolved_complaints: int


class ComplaintCategoryBreakdown(BaseModel):
    category_name: str
    count: int
    percentage: float
    breached_count: int


class BranchLeaderboardItem(BaseModel):
    branch_id: uuid.UUID
    branch_name: str
    branch_code: str
    brand_name: str
    total_cards: int
    connect_rate: float
    csat_score: float
    nps_score: float
    complaints_count: int


class FunnelMetricItem(BaseModel):
    stage: str
    count: int
    conversion_rate: float


class ComprehensiveReportResponse(BaseModel):
    kpis: ReportKpiSummary
    trends: List[CsatNpsTrendItem]
    cre_productivity: List[CreProductivityItem]
    advisor_scorecards: List[AdvisorScorecardItem]
    complaint_breakdown: List[ComplaintCategoryBreakdown]
    branch_leaderboard: List[BranchLeaderboardItem]
    funnel: List[FunnelMetricItem]

