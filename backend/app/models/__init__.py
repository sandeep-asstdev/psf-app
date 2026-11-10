"""
================================================================================
FILE PURPOSE: SQLAlchemy Models Package Registry.
This file imports and registers every database model class so that SQLAlchemy and Alembic
migrations can discover all database tables, foreign keys, and relationships in one central place.

KEY RESPONSIBILITIES:
- Imports tenant models (Tenant, Brand, Branch).
- Imports auth models (User, Role, RolePermission, LoginLog).
- Imports customer & vehicle models (Customer, Vehicle).
- Imports service models (JobCard, ServiceAdvisor).
- Imports followup & call models (FollowupQueue, Call, CallAttempt).
- Imports complaint models (Complaint, ComplaintCategory).
- Imports questionnaire models (Questionnaire, Question).
- Imports allocation models (AllocationRun, AllocationAssignment).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: sqlalchemy.exc.InvalidRequestError: When initializing mapper ..., expression ... refers to an unknown class
  -> Cause: A relationship was added referencing a model that was not imported in __init__.py.
  -> What should you do: Add the missing model import to this file so SQLAlchemy knows about it before building foreign key mappings.
================================================================================
"""
from app.core.database import Base
from app.models.tenant import Tenant, Brand, Branch, BranchContact, Setting
from app.models.auth import Role, RolePermission, User, UserScope, LoginLog
from app.models.customer import Customer, Vehicle
from app.models.service import ImportBatch, JobCard, ServiceType
from app.models.followup import FollowupQueue, Call, CallAttempt, CallStatus, CaseStatus, SurveyResponse, Reminder
from app.models.questionnaire import Questionnaire, Question, KpiTag
from app.models.complaint import ComplaintCategory, Complaint, ComplaintEvent, Reconfirmation
from app.models.allocation import (
    AttendanceOverride,
    AllocationRun,
    AllocationAssignment,
    AllocationCursor,
)
from app.models.additional import (
    RatingScale,
    RatingScaleBand,
    TNPSCall,
    AdvisorCall,
    Document,
    AuditLog,
    CustomFieldDefinition,
    ImportMappingTemplate,
    ConfigChangeHistory,
    NotificationLog,
)
from app.models.config import ConfigVersion, FollowUpProgram, OutcomeRule

__all__ = [
    "Base",
    "Tenant",
    "Brand",
    "Branch",
    "BranchContact",
    "Setting",
    "Role",
    "RolePermission",
    "User",
    "UserScope",
    "LoginLog",
    "Customer",
    "Vehicle",
    "ImportBatch",
    "JobCard",
    "ServiceType",
    "FollowupQueue",
    "Call",
    "CallAttempt",
    "CallStatus",
    "CaseStatus",
    "SurveyResponse",
    "Reminder",
    "Questionnaire",
    "Question",
    "ComplaintCategory",
    "Complaint",
    "ComplaintEvent",
    "Reconfirmation",
    "AttendanceOverride",
    "AllocationRun",
    "AllocationAssignment",
    "AllocationCursor",
    "RatingScale",
    "RatingScaleBand",
    "TNPSCall",
    "AdvisorCall",
    "Document",
    "AuditLog",
    "CustomFieldDefinition",
    "ImportMappingTemplate",
    "ConfigChangeHistory",
]
