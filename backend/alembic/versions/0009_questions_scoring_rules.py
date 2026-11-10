"""questions scoring and outcome rules

Revision ID: 0009_questions_scoring_rules
Revises: 0008_config_and_programs
Create Date: 2026-11-10 16:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0009_questions_scoring_rules'
down_revision: Union[str, None] = '0008_config_and_programs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create kpi_tags table
    op.create_table(
        'kpi_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tag', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_kpi_tags_tenant_id', 'kpi_tags', ['tenant_id'])
    op.create_index('uq_kpi_tags_tenant_tag', 'kpi_tags', ['tenant_id', 'tag'], unique=True)

    # 2. Add columns to questions table
    op.add_column('questions', sa.Column('kpi_tag', sa.String(length=50), nullable=True))
    op.add_column('questions', sa.Column('ask_reason_below', sa.Numeric(5, 2), nullable=True))
    op.add_column('questions', sa.Column('complaint_trigger_below', sa.Numeric(5, 2), nullable=True))
    op.add_column('questions', sa.Column('rating_min', sa.Integer(), nullable=True))
    op.add_column('questions', sa.Column('rating_max', sa.Integer(), nullable=True))
    op.add_column('questions', sa.Column('rating_labels', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index('ix_questions_kpi_tag', 'questions', ['kpi_tag'])

    # 3. Add questionnaire_version to survey_responses
    op.add_column('survey_responses', sa.Column('questionnaire_version', sa.Integer(), nullable=False, server_default='1'))

    # 4. Create outcome_rules table
    op.create_table(
        'outcome_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('brand_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brands.id', ondelete='CASCADE'), nullable=True),
        sa.Column('program_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('follow_up_programs.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_outcome_rules_tenant_id', 'outcome_rules', ['tenant_id'])
    op.create_index('ix_outcome_rules_tenant_brand_priority', 'outcome_rules', ['tenant_id', 'brand_id', 'priority'])

    # 5. Create notification_logs table
    op.create_table(
        'notification_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('recipient', sa.String(length=100), nullable=False),
        sa.Column('template', sa.String(length=100), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='SENT'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_notification_logs_tenant_created', 'notification_logs', ['tenant_id', 'created_at'])

    # 6. Seed standard KPI tags for existing tenants
    op.execute("""
        INSERT INTO kpi_tags (id, tenant_id, tag, label, description, is_active)
        SELECT gen_random_uuid(), t.id, 'SERVICE_QUALITY', 'Service & Repair Quality', 'Workmanship, repair thoroughness, repeat issue resolution', true
        FROM tenants t
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        INSERT INTO kpi_tags (id, tenant_id, tag, label, description, is_active)
        SELECT gen_random_uuid(), t.id, 'TIMELINESS', 'Delivery & Timeliness', 'Vehicle on-time delivery against committed promise', true
        FROM tenants t
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        INSERT INTO kpi_tags (id, tenant_id, tag, label, description, is_active)
        SELECT gen_random_uuid(), t.id, 'ADVISOR_BEHAVIOR', 'Service Advisor Courtesy & Attentiveness', 'Advisor communication, explanation of estimates and billing', true
        FROM tenants t
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        INSERT INTO kpi_tags (id, tenant_id, tag, label, description, is_active)
        SELECT gen_random_uuid(), t.id, 'CLEANLINESS', 'Vehicle & Facility Cleanliness', 'Interior vacuuming, exterior wash finish, lounge and restroom hygiene', true
        FROM tenants t
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        INSERT INTO kpi_tags (id, tenant_id, tag, label, description, is_active)
        SELECT gen_random_uuid(), t.id, 'BILLING_TRANSPARENCY', 'Billing & Cost Transparency', 'Accurate invoice line items, parts charges explanation', true
        FROM tenants t
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        INSERT INTO kpi_tags (id, tenant_id, tag, label, description, is_active)
        SELECT gen_random_uuid(), t.id, 'RECOMMENDATION', 'Brand & Dealer Recommendation', 'Net Promoter Score likelihood to recommend to peers', true
        FROM tenants t
        ON CONFLICT DO NOTHING
    """)

    # 7. Seed standard KPI tags onto existing questions based on question keys
    op.execute("""
        UPDATE questions
        SET kpi_tag = CASE
            WHEN key LIKE '%clean%' OR key LIKE '%wash%' OR key LIKE '%restroom%' THEN 'CLEANLINESS'
            WHEN key LIKE '%advisor%' OR key LIKE '%courtesy%' OR key LIKE '%polite%' OR key LIKE '%explained%' THEN 'ADVISOR_BEHAVIOR'
            WHEN key LIKE '%delivery%' OR key LIKE '%time%' OR key LIKE '%sameday%' OR key LIKE '%ontime%' THEN 'TIMELINESS'
            WHEN key LIKE '%charges%' OR key LIKE '%invoice%' OR key LIKE '%billing%' OR key LIKE '%cost%' THEN 'BILLING_TRANSPARENCY'
            WHEN key LIKE '%recommend%' OR key LIKE '%nps%' OR key LIKE '%tnps%' THEN 'RECOMMENDATION'
            ELSE 'SERVICE_QUALITY'
        END
        WHERE kpi_tag IS NULL
    """)

    # 8. Set rating_min and rating_max for existing rating questions
    op.execute("""
        UPDATE questions
        SET rating_min = 1, rating_max = 5
        WHERE type = 'rating_5'
    """)

    op.execute("""
        UPDATE questions
        SET rating_min = 0, rating_max = 10
        WHERE type = 'nps_10'
    """)

    # 9. Backfill existing survey_responses questionnaire_version
    op.execute("""
        UPDATE survey_responses sr
        SET questionnaire_version = COALESCE(
            (SELECT q.version FROM questionnaires q WHERE q.id = sr.questionnaire_id), 1
        )
    """)

    # 10. Backfill existing answers to store raw and score
    op.execute("""
        UPDATE survey_responses
        SET answers = (
            SELECT jsonb_object_agg(
                elem.key,
                CASE 
                    WHEN jsonb_typeof(elem.value) = 'object' AND elem.value ? 'score' THEN elem.value
                    WHEN jsonb_typeof(elem.value) = 'string' AND LOWER(elem.value#>>'{}') IN ('yes', 'true') THEN jsonb_build_object('raw', elem.value#>>'{}', 'score', 100.0)
                    WHEN jsonb_typeof(elem.value) = 'string' AND LOWER(elem.value#>>'{}') IN ('no', 'false') THEN jsonb_build_object('raw', elem.value#>>'{}', 'score', 0.0)
                    WHEN jsonb_typeof(elem.value) = 'number' AND (elem.value#>>'{}')::numeric > 5 THEN jsonb_build_object('raw', (elem.value#>>'{}')::numeric, 'score', (elem.value#>>'{}')::numeric * 10.0)
                    WHEN jsonb_typeof(elem.value) = 'number' THEN jsonb_build_object('raw', (elem.value#>>'{}')::numeric, 'score', (elem.value#>>'{}')::numeric * 20.0)
                    ELSE jsonb_build_object('raw', elem.value#>>'{}', 'score', null)
                END
            )
            FROM jsonb_each(answers) AS elem
        )
        WHERE answers IS NOT NULL AND answers != '{}'::jsonb
    """)


def downgrade() -> None:
    # 1. Drop notification_logs
    op.drop_index('ix_notification_logs_tenant_created', table_name='notification_logs')
    op.drop_table('notification_logs')

    # 2. Drop outcome_rules
    op.drop_index('ix_outcome_rules_tenant_brand_priority', table_name='outcome_rules')
    op.drop_index('ix_outcome_rules_tenant_id', table_name='outcome_rules')
    op.drop_table('outcome_rules')

    # 3. Drop questionnaire_version from survey_responses
    op.drop_column('survey_responses', 'questionnaire_version')

    # 4. Drop added columns from questions
    op.drop_index('ix_questions_kpi_tag', table_name='questions')
    op.drop_column('questions', 'rating_labels')
    op.drop_column('questions', 'rating_max')
    op.drop_column('questions', 'rating_min')
    op.drop_column('questions', 'complaint_trigger_below')
    op.drop_column('questions', 'ask_reason_below')
    op.drop_column('questions', 'kpi_tag')

    # 5. Drop kpi_tags
    op.drop_index('uq_kpi_tags_tenant_tag', table_name='kpi_tags')
    op.drop_index('ix_kpi_tags_tenant_id', table_name='kpi_tags')
    op.drop_table('kpi_tags')
