"""
================================================================================
FILE PURPOSE: Dynamic Survey Questionnaire Schemas.
Defines Pydantic models for OEM survey question definitions,
answer option structures, and customer survey response payloads.

KEY RESPONSIBILITIES:
- Structures questionnaire templates (Hyundai 4-Q, Tata 7-Q, MG 5-Q).
- Validates rating scale responses (1-5 stars, 1-10 NPS, Yes/No).
- Formats CSAT score and NPS classification results.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: ValidationError: Rating score out of bounds
  -> Cause: A score of 12 was submitted for a 1-10 rating question.
  -> What should you do: Frontend dialer modal should restrict rating inputs to the question's configured range.
================================================================================
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator


# -----------------------------------------
# Question Schemas
# -----------------------------------------
class QuestionBase(BaseModel):
    key: str = Field(..., max_length=80, description="Unique slug for question (e.g. hyundai_work_quality)")
    label: str = Field(..., description="Label displayed to the caller")
    type: str = Field(
        ...,
        description="rating_5 | nps_10 | yes_no | yes_no_na | single_select | multi_select | text | number",
    )
    section: str = Field("General", max_length=80, description="Logical UI section grouping")
    options: Optional[Union[List[Any], Dict[str, Any]]] = None
    show_if: Optional[Dict[str, Any]] = None # e.g. {"field": "mg_advisor_rating", "operator": "<=", "value": 3}
    weight: Decimal = Decimal("1.0")
    display_order: int = 0
    is_required: bool = False


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    key: Optional[str] = None
    label: Optional[str] = None
    type: Optional[str] = None
    section: Optional[str] = None
    options: Optional[Union[List[Any], Dict[str, Any]]] = None
    show_if: Optional[Dict[str, Any]] = None
    weight: Optional[Decimal] = None
    display_order: Optional[int] = None
    is_required: Optional[bool] = None


class QuestionResponse(QuestionBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    questionnaire_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -----------------------------------------
# Questionnaire Schemas
# -----------------------------------------
class QuestionnaireBase(BaseModel):
    brand_id: uuid.UUID
    type: str = Field(..., description="PSF | TNPS | HAPPINESS | RECONFIRMATION")
    title: str = Field(..., max_length=150)
    version: int = 1
    is_active: bool = True


class QuestionnaireCreate(QuestionnaireBase):
    pass


class QuestionnaireUpdate(BaseModel):
    title: Optional[str] = None
    is_active: Optional[bool] = None


class QuestionnaireDetailResponse(QuestionnaireBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    brand_name: Optional[str] = None
    brand_code: Optional[str] = None
    questions: List[QuestionResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuestionnaireListItem(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    brand_id: uuid.UUID
    brand_name: Optional[str] = None
    brand_code: Optional[str] = None
    type: str
    title: str
    version: int
    questions_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReorderQuestionsRequest(BaseModel):
    question_ids: List[uuid.UUID]

