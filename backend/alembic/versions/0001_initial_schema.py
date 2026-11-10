"""Initial schema with 26 entities, UUIDv7, GIN indexes, and tenant scoping

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-02 12:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tenants
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("primary_color", sa.String(20), server_default="#2563EB", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)
    op.create_index("ix_tenants_is_active", "tenants", ["is_active"])
    op.create_index("ix_tenants_is_deleted", "tenants", ["is_deleted"])

    # 2. Brands
    op.create_table(
        "brands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("primary_color", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("uq_brands_tenant_code", "brands", ["tenant_id", "code"], unique=True)
    op.create_index("ix_brands_tenant_active", "brands", ["tenant_id", "is_active"])
    op.create_index("ix_brands_is_deleted", "brands", ["is_deleted"])

    # 3. Branches
    op.create_table(
        "branches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("pincode", sa.String(20), nullable=True),
        sa.Column("phone", sa.String(255), nullable=True),
        sa.Column("email", sa.String(150), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("uq_branches_tenant_brand_code", "branches", ["tenant_id", "brand_id", "code"], unique=True)
    op.create_index("ix_branches_tenant_active", "branches", ["tenant_id", "is_active"])
    op.create_index("ix_branches_is_deleted", "branches", ["is_deleted"])

    # 4. Settings
    op.create_table(
        "settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("config_key", sa.String(80), nullable=False),
        sa.Column("config_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("uq_settings_tenant_key", "settings", ["tenant_id", "config_key"], unique=True)

    # 5. Roles
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("uq_roles_tenant_name", "roles", ["tenant_id", "name"], unique=True)
    op.create_index("ix_roles_is_deleted", "roles", ["is_deleted"])

    # 6. Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("email", sa.String(150), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(255), nullable=True), # Encrypted
        sa.Column("phone_hash", sa.String(64), nullable=True), # HMAC
        sa.Column("employee_id", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("uq_users_tenant_email", "users", ["tenant_id", "email"], unique=True)
    op.create_index("ix_users_tenant_active", "users", ["tenant_id", "is_active"])
    op.create_index("ix_users_phone_hash", "users", ["phone_hash"])
    op.create_index("ix_users_is_deleted", "users", ["is_deleted"])

    # 7. User Scopes
    op.create_table(
        "user_scopes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=True),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("uq_user_scopes_unique", "user_scopes", ["user_id", "brand_id", "branch_id"], unique=True)
    op.create_index("ix_user_scopes_tenant_id", "user_scopes", ["tenant_id"])

    # 8. Login Logs (Attendance tracking)
    op.create_table(
        "login_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("login_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("logout_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("device_info", sa.String(200), nullable=True),
        sa.Column("status", sa.String(30), server_default="SUCCESS", nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_login_logs_tenant_user_login", "login_logs", ["tenant_id", "user_id", "login_at"])
    op.create_index("ix_login_logs_tenant_login", "login_logs", ["tenant_id", "login_at"])

    # 9. Customers
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("phone", sa.String(255), nullable=False), # Encrypted
        sa.Column("phone_hash", sa.String(64), nullable=False), # HMAC
        sa.Column("alt_phone", sa.String(255), nullable=True), # Encrypted
        sa.Column("email", sa.String(150), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("do_not_disturb", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_customers_tenant_phone_hash", "customers", ["tenant_id", "phone_hash"])
    op.create_index("ix_customers_tenant_name", "customers", ["tenant_id", "name"])

    # 10. Vehicles
    op.create_table(
        "vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reg_no", sa.String(30), nullable=False),
        sa.Column("vin", sa.String(50), nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("variant", sa.String(100), nullable=True),
        sa.Column("fuel_type", sa.String(30), nullable=True),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_vehicles_tenant_reg_no", "vehicles", ["tenant_id", "reg_no"])
    op.create_index("ix_vehicles_tenant_vin", "vehicles", ["tenant_id", "vin"])

    # 11. Import Batches
    op.create_table(
        "import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=True),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processed_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("success_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_log", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(30), server_default="PENDING", nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_import_batches_tenant_status_created", "import_batches", ["tenant_id", "status", "created_at"])

    # 12. Job Cards
    op.create_table(
        "job_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("import_batches.id"), nullable=True),
        sa.Column("job_card_no", sa.String(60), nullable=False),
        sa.Column("job_card_date", sa.Date(), nullable=False),
        sa.Column("service_advisor_name", sa.String(120), nullable=True),
        sa.Column("service_advisor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("technician_name", sa.String(120), nullable=True),
        sa.Column("service_type", sa.String(80), nullable=True),
        sa.Column("total_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False),
        sa.Column("odometer_reading", sa.Integer(), nullable=True),
        sa.Column("promised_delivery_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_delivery_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("uq_job_cards_tenant_branch_no", "job_cards", ["tenant_id", "branch_id", "job_card_no"], unique=True)
    op.create_index("ix_job_cards_tenant_branch_date", "job_cards", ["tenant_id", "branch_id", "job_card_date"])
    op.create_index("ix_job_cards_tenant_advisor", "job_cards", ["tenant_id", "service_advisor_id"])
    op.create_index("ix_job_cards_tenant_customer", "job_cards", ["tenant_id", "customer_id"])

    # 13. Followup Queues
    op.create_table(
        "followup_queues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_card_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("queue_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), server_default="PENDING", nullable=False),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("contacted_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_followup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_followup_queues_tenant_type_status_due", "followup_queues", ["tenant_id", "queue_type", "status", "due_at"])
    op.create_index("ix_followup_queues_tenant_assigned_status_due", "followup_queues", ["tenant_id", "assigned_to_id", "status", "due_at"])

    # 14. Calls
    op.create_table(
        "calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("followup_queue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("followup_queues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_card_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("called_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("called_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("phone_dialed", sa.String(255), nullable=False), # Encrypted
        sa.Column("call_status", sa.String(50), nullable=False),
        sa.Column("case_status", sa.String(50), nullable=False),
        sa.Column("voc", sa.Text(), nullable=True),
        sa.Column("alt_contact_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("recording_url", sa.String(500), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_calls_tenant_called_at", "calls", ["tenant_id", "called_at"])
    op.create_index("ix_calls_tenant_caller_date", "calls", ["tenant_id", "called_by_id", "called_at"])

    # 15. Dynamic Questionnaires
    op.create_table(
        "questionnaires",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("uq_questionnaires_tenant_brand_type_ver", "questionnaires", ["tenant_id", "brand_id", "type", "version"], unique=True)

    # 16. Questions
    op.create_table(
        "questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("questionnaire_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questionnaires.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("section", sa.String(80), server_default="General", nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("show_if", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("weight", sa.Numeric(4, 2), server_default="1.0", nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_questions_questionnaire_order", "questions", ["questionnaire_id", "display_order"])

    # 17. Survey Responses
    op.create_table(
        "survey_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_card_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("questionnaire_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questionnaires.id"), nullable=False),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("csat_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("nps_score", sa.SmallInteger(), nullable=True),
        sa.Column("nps_category", sa.String(20), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_survey_responses_answers_gin", "survey_responses", ["answers"], postgresql_using="gin")
    op.create_index("ix_survey_responses_tenant_nps", "survey_responses", ["tenant_id", "nps_category"])

    # 18. Complaint Categories
    op.create_table(
        "complaint_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("default_sla_hours", sa.Integer(), server_default="24", nullable=False),
        sa.Column("severity_level", sa.String(30), server_default="MEDIUM", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("uq_complaint_cat_tenant_name", "complaint_categories", ["tenant_id", "name"], unique=True)

    # 19. Complaints
    op.create_table(
        "complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_card_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id"), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("complaint_categories.id"), nullable=False),
        sa.Column("complaint_no", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(30), server_default="MEDIUM", nullable=False),
        sa.Column("status", sa.String(40), server_default="OPEN", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_sla_breached", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("resolution_remarks", sa.Text(), nullable=True),
        sa.Column("resolved_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_complaints_no", "complaints", ["complaint_no"], unique=True)
    op.create_index("ix_complaints_tenant_branch_status_sla", "complaints", ["tenant_id", "branch_id", "status", "sla_due_at"])
    op.create_index("ix_complaints_tenant_assigned_status", "complaints", ["tenant_id", "assigned_to_id", "status"])

    # 20. Complaint Events
    op.create_table(
        "complaint_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("complaint_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False),
        sa.Column("performed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("from_status", sa.String(40), nullable=True),
        sa.Column("to_status", sa.String(40), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_complaint_events_complaint_created", "complaint_events", ["complaint_id", "created_at"])

    # 21. Reconfirmations
    op.create_table(
        "reconfirmations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("complaint_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conducted_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reconfirmation_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("call_status", sa.String(50), nullable=False),
        sa.Column("customer_feedback", sa.Text(), nullable=True),
        sa.Column("closure_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_reconfirmations_tenant_complaint", "reconfirmations", ["tenant_id", "complaint_id"])

    # 22. TNPS Calls
    op.create_table(
        "tnps_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_card_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conducted_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("brand_recommend_score", sa.SmallInteger(), nullable=False),
        sa.Column("workshop_recommend_score", sa.SmallInteger(), nullable=False),
        sa.Column("voc", sa.Text(), nullable=True),
        sa.Column("document_url", sa.String(500), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_tnps_calls_tenant_job", "tnps_calls", ["tenant_id", "job_card_id"])

    # 23. Advisor Calls
    op.create_table(
        "advisor_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_card_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("advisor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("adv_call_status", sa.String(50), nullable=False),
        sa.Column("adv_case_status", sa.String(50), nullable=False),
        sa.Column("adv_voc", sa.Text(), nullable=True),
        sa.Column("adv_status", sa.String(40), server_default="PENDING", nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_advisor_calls_tenant_advisor", "advisor_calls", ["tenant_id", "advisor_id"])

    # 24. Reminders
    op.create_table(
        "reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("followup_queue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("followup_queues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_acknowledged", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_reminders_tenant_user_ack_time", "reminders", ["tenant_id", "assigned_to_id", "is_acknowledged", "remind_at"])

    # 25. Documents
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_documents_tenant_entity", "documents", ["tenant_id", "entity_type", "entity_id"])

    # 26. Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=True),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("old_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_logs_tenant_created", "audit_logs", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("documents")
    op.drop_table("reminders")
    op.drop_table("advisor_calls")
    op.drop_table("tnps_calls")
    op.drop_table("reconfirmations")
    op.drop_table("complaint_events")
    op.drop_table("complaints")
    op.drop_table("complaint_categories")
    op.drop_table("survey_responses")
    op.drop_table("questions")
    op.drop_table("questionnaires")
    op.drop_table("calls")
    op.drop_table("followup_queues")
    op.drop_table("job_cards")
    op.drop_table("import_batches")
    op.drop_table("vehicles")
    op.drop_table("customers")
    op.drop_table("login_logs")
    op.drop_table("user_scopes")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("settings")
    op.drop_table("branches")
    op.drop_table("brands")
    op.drop_table("tenants")

