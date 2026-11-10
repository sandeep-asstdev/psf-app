"""align schema with real data (rating scales, call attempts, branch contacts, status categories)

Revision ID: 0002_real_data_alignment
Revises: 0001_initial_schema
Create Date: 2026-11-02 17:17:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002_real_data_alignment'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    existing_tables = set(insp.get_table_names())

    # 1. Update branches table (add dms_code, display_name, needs_review; alter brand_id nullable)
    branch_cols = set(c["name"] for c in insp.get_columns("branches"))
    if "display_name" not in branch_cols:
        op.add_column('branches', sa.Column('display_name', sa.String(length=150), nullable=True))
    if "dms_code" not in branch_cols:
        op.add_column('branches', sa.Column('dms_code', sa.String(length=50), nullable=True))
    if "needs_review" not in branch_cols:
        op.add_column('branches', sa.Column('needs_review', sa.Boolean(), server_default='false', nullable=False))
    
    op.alter_column('branches', 'brand_id', existing_type=postgresql.UUID(as_uuid=True), nullable=True)

    branch_indexes = set(i["name"] for i in insp.get_indexes("branches"))
    if "ix_branches_tenant_dms" not in branch_indexes:
        op.create_index('ix_branches_tenant_dms', 'branches', ['tenant_id', 'dms_code'], unique=False)
    if "uq_branches_tenant_code" not in branch_indexes:
        op.create_index('uq_branches_tenant_code', 'branches', ['tenant_id', 'code'], unique=True)

    # 2. Create branch_contacts table if not exists
    if 'branch_contacts' not in existing_tables:
        op.create_table(
            'branch_contacts',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('role', sa.String(length=50), server_default='SERVICE_MANAGER', nullable=False),
            sa.Column('name', sa.String(length=150), nullable=True),
            sa.Column('phone', sa.String(length=255), nullable=True),
            sa.Column('phone_hash', sa.String(length=64), nullable=True),
            sa.Column('email', sa.String(length=150), nullable=True),
            sa.Column('notify_on', sa.String(length=100), server_default='complaint,low_rating', nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_branch_contacts_tenant_branch', 'branch_contacts', ['tenant_id', 'branch_id'], unique=False)
        op.create_index('ix_branch_contacts_phone_hash', 'branch_contacts', ['phone_hash'], unique=False)

    # 3. Create rating_scales and rating_scale_bands
    if 'rating_scales' not in existing_tables:
        op.create_table(
            'rating_scales',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('brand_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('max_rating', sa.SmallInteger(), server_default='10', nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('uq_rating_scales_tenant_brand', 'rating_scales', ['tenant_id', 'brand_id'], unique=True)

    if 'rating_scale_bands' not in existing_tables:
        op.create_table(
            'rating_scale_bands',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('scale_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('min_score', sa.SmallInteger(), nullable=False),
            sa.Column('max_score', sa.SmallInteger(), nullable=False),
            sa.Column('label', sa.String(length=50), nullable=False),
            sa.Column('derived_case_status', sa.String(length=50), nullable=False),
            sa.Column('is_delight', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('is_complaint_trigger', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['scale_id'], ['rating_scales.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_scale_bands_scale_scores', 'rating_scale_bands', ['scale_id', 'min_score', 'max_score'], unique=False)

    # 4. Create call_statuses and case_statuses
    if 'call_statuses' not in existing_tables:
        op.create_table(
            'call_statuses',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('name', sa.String(length=50), nullable=False),
            sa.Column('category', sa.String(length=40), server_default='SENTIMENT', nullable=False),
            sa.Column('counts_as_contacted', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('closes_followup', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('retry_allowed', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('color', sa.String(length=20), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('uq_call_statuses_tenant_name', 'call_statuses', ['tenant_id', 'name'], unique=True)

    if 'case_statuses' not in existing_tables:
        op.create_table(
            'case_statuses',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('name', sa.String(length=50), nullable=False),
            sa.Column('category', sa.String(length=40), server_default='SENTIMENT', nullable=False),
            sa.Column('counts_as_contacted', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('closes_followup', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('retry_allowed', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('color', sa.String(length=20), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('uq_case_statuses_tenant_name', 'case_statuses', ['tenant_id', 'name'], unique=True)

    # 5. Create call_attempts table
    if 'call_attempts' not in existing_tables:
        op.create_table(
            'call_attempts',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('followup_queue_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('attempt_number', sa.Integer(), server_default='1', nullable=False),
            sa.Column('call_status', sa.String(length=50), nullable=False),
            sa.Column('case_status', sa.String(length=50), nullable=True),
            sa.Column('voc', sa.Text(), nullable=True),
            sa.Column('rating', sa.SmallInteger(), nullable=True),
            sa.Column('called_by_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('called_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('duration_seconds', sa.Integer(), server_default='0', nullable=False),
            sa.ForeignKeyConstraint(['called_by_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['followup_queue_id'], ['followup_queues.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_call_attempts_queue_attempt', 'call_attempts', ['followup_queue_id', 'attempt_number'], unique=False)

    # 6. Add columns to followup_queues
    fq_cols = set(c["name"] for c in insp.get_columns("followup_queues"))
    if "scheduled_tnps_date" not in fq_cols:
        op.add_column('followup_queues', sa.Column('scheduled_tnps_date', sa.Date(), nullable=True))

    # 7. Add columns to survey_responses
    sr_cols = set(c["name"] for c in insp.get_columns("survey_responses"))
    if "channel" not in sr_cols:
        op.add_column('survey_responses', sa.Column('channel', sa.String(length=20), server_default='PHONE', nullable=False))
    if "raw_rating" not in sr_cols:
        op.add_column('survey_responses', sa.Column('raw_rating', sa.SmallInteger(), nullable=True))

    # 8. Add columns to complaint_categories
    cc_cols = set(c["name"] for c in insp.get_columns("complaint_categories"))
    if "legacy_label" not in cc_cols:
        op.add_column('complaint_categories', sa.Column('legacy_label', sa.String(length=150), nullable=True))
    if "icon" not in cc_cols:
        op.add_column('complaint_categories', sa.Column('icon', sa.String(length=20), nullable=True))

    # 9. Add columns to questions
    q_cols = set(c["name"] for c in insp.get_columns("questions"))
    if "legacy_label" not in q_cols:
        op.add_column('questions', sa.Column('legacy_label', sa.Text(), nullable=True))
    if "answer_type" not in q_cols:
        op.add_column('questions', sa.Column('answer_type', sa.String(length=40), server_default='YES_NO', nullable=False))


def downgrade() -> None:
    pass
