"""
================================================================================
FILE PURPOSE: Dealership Master Data Schemas (Brands, Branches, Workshops, Service Types).
Defines Pydantic validation models for creating and updating dealership master entities.

KEY RESPONSIBILITIES:
- Validates Brand creation and updates (name, OEM code, primary color, logo URL).
- Validates Branch creation and updates (name, code, brand link, contact phone, city).
- Validates Service Type and Technician records.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: ValidationError: primary_color must be a valid hex color code
  -> Cause: Brand color was entered in an invalid format (e.g. 'blue' instead of '#0052CC').
  -> What should you do: Use a valid 6-character hex color format like #1E40AF.
================================================================================
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# -----------------------------------------
# Brand Schemas
# -----------------------------------------
class BrandBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=30)
    logo_url: Optional[str] = None
    primary_color: Optional[str] = "#002C6C"
    is_active: bool = True


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    is_active: Optional[bool] = None


class BrandResponse(BrandBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    branches_count: Optional[int] = 0
    has_happiness_calling: bool = False

    class Config:
        from_attributes = True


# -----------------------------------------
# Branch Schemas
# -----------------------------------------
class BranchBase(BaseModel):
    brand_id: Optional[uuid.UUID] = None
    name: str = Field(..., max_length=150)
    code: str = Field(..., max_length=50)
    dms_code: Optional[str] = None
    display_name: Optional[str] = None
    needs_review: bool = False
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    brand_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    code: Optional[str] = None
    dms_code: Optional[str] = None
    display_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


class BranchResponse(BranchBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    brand_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -----------------------------------------
# Complaint Category Schemas
# -----------------------------------------
class ComplaintCategoryBase(BaseModel):
    brand_id: Optional[uuid.UUID] = None
    name: str = Field(..., max_length=100)
    default_sla_hours: int = 24
    severity_level: str = "MEDIUM" # LOW | MEDIUM | HIGH | CRITICAL
    is_active: bool = True


class ComplaintCategoryCreate(ComplaintCategoryBase):
    pass


class ComplaintCategoryUpdate(BaseModel):
    brand_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    default_sla_hours: Optional[int] = None
    severity_level: Optional[str] = None
    is_active: Optional[bool] = None


class ComplaintCategoryResponse(ComplaintCategoryBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -----------------------------------------
# Tenant Settings Schema
# -----------------------------------------
class SettingUpdate(BaseModel):
    config_key: str
    config_value: Dict[str, Any]


class SettingResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    config_key: str
    config_value: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# -----------------------------------------
# Branch Contacts Schemas
# -----------------------------------------
class BranchContactBase(BaseModel):
    branch_id: uuid.UUID
    role: str = "SERVICE_MANAGER"
    name: str = Field(..., max_length=120)
    phone: str = Field(..., max_length=30)
    email: Optional[str] = None
    notify_on: Optional[str] = "complaint,low_rating,daily_summary"
    is_active: bool = True


class BranchContactCreate(BranchContactBase):
    pass


class BranchContactUpdate(BaseModel):
    role: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notify_on: Optional[str] = None
    is_active: Optional[bool] = None


class BranchContactResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID
    branch_name: Optional[str] = None
    branch_code: Optional[str] = None
    dms_code: Optional[str] = None
    role: str
    name: str
    phone: str
    phone_masked: str
    email: Optional[str] = None
    notify_on: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BranchContactsOverviewResponse(BaseModel):
    items: List[BranchContactResponse]
    total_contacts: int
    missing_branches: List[Dict[str, Any]]
    missing_count: int


# -----------------------------------------
# Rating Scales and Bands Schemas
# -----------------------------------------
class RatingScaleBandBase(BaseModel):
    min_score: int
    max_score: int
    label: str
    derived_case_status: str
    is_delight: bool = False
    is_complaint_trigger: bool = False


class RatingScaleBandCreate(RatingScaleBandBase):
    pass


class RatingScaleBandUpdate(BaseModel):
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    label: Optional[str] = None
    derived_case_status: Optional[str] = None
    is_delight: Optional[bool] = None
    is_complaint_trigger: Optional[bool] = None


class RatingScaleBandResponse(RatingScaleBandBase):
    id: uuid.UUID
    scale_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class RatingScaleResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    brand_id: uuid.UUID
    brand_name: Optional[str] = None
    brand_code: Optional[str] = None
    name: str
    max_rating: int
    is_active: bool
    bands: List[RatingScaleBandResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -----------------------------------------
# Call Status & Case Status Schemas
# -----------------------------------------
class CallStatusCreate(BaseModel):
    name: str
    category: str = "SENTIMENT"
    counts_as_contacted: bool = False
    closes_followup: bool = False
    retry_allowed: bool = True
    color: Optional[str] = "#2563EB"
    is_active: bool = True


class CallStatusUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    counts_as_contacted: Optional[bool] = None
    closes_followup: Optional[bool] = None
    retry_allowed: Optional[bool] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class CallStatusResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    category: str
    counts_as_contacted: bool
    closes_followup: bool
    retry_allowed: bool
    color: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CaseStatusCreate(BaseModel):
    name: str
    category: str = "SENTIMENT"
    counts_as_contacted: bool = False
    closes_followup: bool = False
    retry_allowed: bool = True
    color: Optional[str] = "#10B981"
    is_active: bool = True


class CaseStatusUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    counts_as_contacted: Optional[bool] = None
    closes_followup: Optional[bool] = None
    retry_allowed: Optional[bool] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class CaseStatusResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    category: str
    counts_as_contacted: bool
    closes_followup: bool
    retry_allowed: bool
    color: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
        from_attributes = True

