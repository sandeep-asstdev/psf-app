"""
================================================================================
FILE PURPOSE: Pydantic Schemas for Follow-Up Programs & Config Versions.
================================================================================
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FollowUpProgramBase(BaseModel):
    brand_id: Optional[uuid.UUID] = None
    code: str = Field(..., max_length=50)
    label: str = Field(..., max_length=100)
    enabled: bool = True
    trigger: str = Field(default="ON_IMPORT", max_length=50)
    channel: str = Field(default="PHONE", max_length=20)
    questionnaire_id: Optional[uuid.UUID] = None
    rating_scale_id: Optional[uuid.UUID] = None
    max_attempts: int = Field(default=3, ge=1, le=10)
    retry_gap_hours: int = Field(default=24, ge=1, le=168)
    sla_hours: int = Field(default=48, ge=1, le=720)
    sort_order: int = Field(default=0, ge=0)


class FollowUpProgramCreate(FollowUpProgramBase):
    pass


class FollowUpProgramUpdate(BaseModel):
    brand_id: Optional[uuid.UUID] = None
    code: Optional[str] = None
    label: Optional[str] = None
    enabled: Optional[bool] = None
    trigger: Optional[str] = None
    channel: Optional[str] = None
    questionnaire_id: Optional[uuid.UUID] = None
    rating_scale_id: Optional[uuid.UUID] = None
    max_attempts: Optional[int] = None
    retry_gap_hours: Optional[int] = None
    sla_hours: Optional[int] = None
    sort_order: Optional[int] = None


class FollowUpProgramResponse(FollowUpProgramBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    brand_name: Optional[str] = None
    questionnaire_title: Optional[str] = None
    rating_scale_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReorderItem(BaseModel):
    id: uuid.UUID
    sort_order: int


class ReorderRequest(BaseModel):
    orders: List[ReorderItem]


class ConfigVersionBase(BaseModel):
    scope: str = "DEALERSHIP"
    scope_id: Optional[uuid.UUID] = None
    config_type: str
    payload: Dict[str, Any]
    note: Optional[str] = None


class ConfigVersionCreate(ConfigVersionBase):
    pass


class ConfigPublishRequest(BaseModel):
    version_id: Optional[uuid.UUID] = None
    config_type: str = "PROGRAMS"
    scope: str = "DEALERSHIP"
    scope_id: Optional[uuid.UUID] = None
    note: Optional[str] = None


class ConfigRollbackRequest(BaseModel):
    target_version_id: Optional[uuid.UUID] = None
    config_type: str = "PROGRAMS"
    scope: str = "DEALERSHIP"
    scope_id: Optional[uuid.UUID] = None
    reason: str


class ConfigVersionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    scope: str
    scope_id: Optional[uuid.UUID] = None
    config_type: str
    version: int
    status: str
    payload: Dict[str, Any]
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    published_at: Optional[datetime] = None
    note: Optional[str] = None

    class Config:
        from_attributes = True



class KpiTagBase(BaseModel):
    tag: str = Field(..., max_length=50)
    label: str = Field(..., max_length=100)
    description: Optional[str] = None
    is_active: bool = True


class KpiTagCreate(KpiTagBase):
    pass


class KpiTagResponse(KpiTagBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class OutcomeRuleBase(BaseModel):
    brand_id: Optional[uuid.UUID] = None
    program_id: Optional[uuid.UUID] = None
    name: str = Field(..., max_length=120)
    enabled: bool = True
    priority: int = 0
    conditions: Dict[str, Any]
    actions: Dict[str, Any]


class OutcomeRuleCreate(OutcomeRuleBase):
    pass


class OutcomeRuleUpdate(BaseModel):
    brand_id: Optional[uuid.UUID] = None
    program_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    conditions: Optional[Dict[str, Any]] = None
    actions: Optional[Dict[str, Any]] = None


class OutcomeRuleResponse(OutcomeRuleBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SimulateRequest(BaseModel):
    brand_id: Optional[uuid.UUID] = None
    program_id: Optional[uuid.UUID] = None
    job_card: Optional[Dict[str, Any]] = None
    answers: Dict[str, Any] = Field(default_factory=dict)
    scoring_method: str = "WEIGHTED_AVERAGE"


class SimulateResponse(BaseModel):
    overall_score: float
    csat_score: float
    nps_score: Optional[int] = None
    nps_category: Optional[str] = None
    derived_case_status: str
    is_delight: bool
    is_complaint_trigger: bool
    kpi_scores: Dict[str, float]
    normalized_answers: Dict[str, Dict[str, Any]]
    rules_matched: List[str]
    resulting_outcome: Optional[str] = None
    complaint: Optional[Dict[str, Any]] = None
    notifications: List[Dict[str, Any]]


class LabelOverrideBase(BaseModel):
    key: str = Field(..., max_length=100)
    language: str = Field("en", max_length=10)
    value: str = Field(..., max_length=255)


class LabelOverrideCreate(LabelOverrideBase):
    pass


class LabelOverrideResponse(LabelOverrideBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LabelOverrideBatch(BaseModel):
    labels: Dict[str, str] = Field(..., description="Mapping of label key to customized display value")
    language: str = Field("en", max_length=10)

