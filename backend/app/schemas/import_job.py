"""
================================================================================
FILE PURPOSE: DMS File Import, Header Mapping & Batch Report Schemas.
Defines Pydantic models for file upload responses, column header mapping templates,
row validation previews, and import error reports.

KEY RESPONSIBILITIES:
- Validates column mapping aliases (e.g. 'Job Card No' vs 'JC Number').
- Formats import batch statistics (success rows, skipped duplicates, errors).
- Structures downloadable row error summaries.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: ValidationError: Missing required column mapping for 'Job Card No'
  -> Cause: The uploaded file is missing mandatory columns.
  -> What should you do: Download the sample template from the Data Import page and ensure all 13 standard columns are present.
================================================================================
"""
import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


# -------------------------------------------------------------
# Row-Level Error & Warning Schemas
# -------------------------------------------------------------
class ImportRowError(BaseModel):
    row_number: int
    job_card_no: Optional[str] = None
    column: Optional[str] = None
    rejected_value: Optional[str] = None
    reason: str
    fix_hint: Optional[str] = None


class ImportRowWarning(BaseModel):
    row_number: int
    job_card_no: Optional[str] = None
    column: Optional[str] = None
    warning_value: Optional[str] = None
    reason: str
    fix_hint: Optional[str] = None


class DuplicateSkippedDetail(BaseModel):
    row_number: int
    job_card_no: str
    branch_name: Optional[str] = None
    duplicate_type: str = Field(..., description="IDENTICAL | DIFFERENT")
    diff_summary: Optional[str] = None


# -------------------------------------------------------------
# Column Mapping & Preview
# -------------------------------------------------------------
class ImportPreviewRow(BaseModel):
    row_number: int
    job_card_no: Optional[str] = None
    job_card_date: Optional[str] = None
    customer_name: Optional[str] = None
    contact_number: Optional[str] = None
    brand: Optional[str] = None
    branch: Optional[str] = None
    reg_no: Optional[str] = None
    vin_no: Optional[str] = None
    model: Optional[str] = None
    service_advisor: Optional[str] = None
    service_type: Optional[str] = None
    total_service_amount: Optional[float] = None
    status: str = Field(..., description="VALID | WARNING | ERROR")
    warnings: List[ImportRowWarning] = []
    errors: List[ImportRowError] = []


class ImportPreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_name: str
    file_hash: str
    has_duplicate_file_hash: bool = False
    previous_batch_info: Optional[Dict[str, Any]] = None
    total_rows: int
    valid_rows: int
    warning_rows: int
    error_rows: int
    detected_columns: List[str]
    mapped_headers: Dict[str, str]
    suggested_mapping: Dict[str, str] = Field(default_factory=dict)
    unmapped_headers: List[str]
    preview_rows: List[ImportPreviewRow]


class ImportProcessRequest(BaseModel):
    file_hash: Optional[str] = None
    confirm_duplicate_hash: bool = False
    brand_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    column_mapping: Dict[str, str]
    allocation_mode: str = Field("ROUND_ROBIN", description="ROUND_ROBIN | BY_BRANCH | UNASSIGNED")
    duplicate_action: str = Field("SKIP", description="SKIP | UPDATE")
    save_mapping_template: bool = False
    template_name: Optional[str] = None


class ImportSummaryResponse(BaseModel):
    batch_id: uuid.UUID
    file_name: str
    file_hash: Optional[str] = None
    total_rows: int
    success_rows: int
    skipped_rows: int
    skipped_identical_count: int = 0
    skipped_different_count: int = 0
    skipped_details: List[DuplicateSkippedDetail] = []
    warning_rows: int = 0
    error_rows: int = 0
    queues_created: int = 0
    happiness_scheduled: int = 0
    new_placeholder_advisors: List[str] = []
    unmapped_service_types: List[str] = []
    errors: List[ImportRowError] = []
    allocation_run_id: Optional[uuid.UUID] = None
    allocation_summary: Optional[Dict[str, Any]] = None


class ImportBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    brand_id: Optional[uuid.UUID] = None
    brand_name: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None
    branch_name: Optional[str] = None
    file_name: str
    file_hash: Optional[str] = None
    total_rows: int
    processed_rows: int
    success_rows: int
    error_rows: int
    status: str
    error_log: Optional[Dict[str, Any]] = None
    uploaded_by: uuid.UUID
    uploader_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# -------------------------------------------------------------
# Direct DMS Webhook Schema
# -------------------------------------------------------------
class DmsJobCardWebhook(BaseModel):
    brand_code: str = Field(..., description="Brand code e.g. HYUN, MG, ATHER")
    branch_code: str = Field(..., description="Branch code e.g. GUR-01")
    job_card_no: str = Field(..., max_length=60)
    job_card_date: date
    customer_name: str = Field(..., max_length=150)
    customer_phone: str = Field(..., max_length=30)
    customer_alt_phone: Optional[str] = None
    customer_email: Optional[str] = None
    reg_no: str = Field(..., max_length=30)
    vin: Optional[str] = None
    model: str = Field(..., max_length=100)
    variant: Optional[str] = None
    service_advisor: Optional[str] = None
    technician: Optional[str] = None
    service_type: Optional[str] = None
    total_amount: Decimal = Decimal("0.0")
    odometer: Optional[int] = None
