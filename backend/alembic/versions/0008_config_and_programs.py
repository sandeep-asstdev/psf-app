"""config foundation and programs

Revision ID: 0008_config_foundation_and_programs
Revises: 0007_ather_tnps_model_correction
Create Date: 2026-11-10 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0008_config_and_programs'
down_revision: Union[str, None] = '0007_ather_tnps_model_correction'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create config_versions table
    op.create_table(
        'config_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scope', sa.String(length=20), nullable=False, server_default='DEALERSHIP'),
        sa.Column('scope_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('config_type', sa.String(length=50), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
    )
    op.create_index('ix_config_versions_tenant_id', 'config_versions', ['tenant_id'])
    op.create_index('ix_config_versions_lookup', 'config_versions', ['tenant_id', 'scope', 'scope_id', 'config_type', 'status'])
    op.create_index('uq_config_versions_ver', 'config_versions', ['tenant_id', 'scope', 'scope_id', 'config_type', 'version'], unique=True)

    # 2. Create follow_up_programs table
    op.create_table(
        'follow_up_programs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('brand_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brands.id', ondelete='CASCADE'), nullable=True),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('trigger', sa.String(length=50), nullable=False, server_default='ON_IMPORT'),
        sa.Column('channel', sa.String(length=20), nullable=False, server_default='PHONE'),
        sa.Column('questionnaire_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('questionnaires.id', ondelete='SET NULL'), nullable=True),
        sa.Column('rating_scale_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rating_scales.id', ondelete='SET NULL'), nullable=True),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('retry_gap_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('sla_hours', sa.Integer(), nullable=False, server_default='48'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_follow_up_programs_tenant_id', 'follow_up_programs', ['tenant_id'])
    op.create_index('ix_follow_up_programs_brand_id', 'follow_up_programs', ['brand_id'])
    op.create_index('ix_follow_up_programs_tenant_brand_order', 'follow_up_programs', ['tenant_id', 'brand_id', 'sort_order'])

    # 3. Add program_id to followup_queues
    op.add_column('followup_queues', sa.Column('program_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('follow_up_programs.id', ondelete='SET NULL'), nullable=True))
    op.create_index('ix_followup_queues_program_id', 'followup_queues', ['program_id'])

    # 4. Migrate / Seed default programs for existing brands (individual statements for asyncpg)
    op.execute("""
        INSERT INTO follow_up_programs (id, tenant_id, brand_id, code, label, enabled, trigger, channel, max_attempts, retry_gap_hours, sla_hours, sort_order)
        SELECT gen_random_uuid(), t.id, NULL, 'PSF', 'Post Service Follow-up (PSF)', true, 'ON_IMPORT', 'PHONE', 3, 24, 48, 0
        FROM tenants t
    """)

    op.execute("""
        INSERT INTO follow_up_programs (id, tenant_id, brand_id, code, label, enabled, trigger, channel, questionnaire_id, rating_scale_id, max_attempts, retry_gap_hours, sla_hours, sort_order)
        SELECT 
            gen_random_uuid(),
            b.tenant_id,
            b.id,
            'PSF',
            'Hyundai PSF Standard Survey',
            true,
            'ON_IMPORT',
            'PHONE',
            (SELECT q.id FROM questionnaires q WHERE q.brand_id = b.id AND q.type = 'PSF' LIMIT 1),
            (SELECT rs.id FROM rating_scales rs WHERE rs.brand_id = b.id LIMIT 1),
            3, 24, 48, 0
        FROM brands b
        WHERE b.code = 'HYUN' OR UPPER(b.name) LIKE '%HYUNDAI%'
    """)

    op.execute("""
        INSERT INTO follow_up_programs (id, tenant_id, brand_id, code, label, enabled, trigger, channel, questionnaire_id, rating_scale_id, max_attempts, retry_gap_hours, sla_hours, sort_order)
        SELECT 
            gen_random_uuid(),
            b.tenant_id,
            b.id,
            'HAPPINESS',
            'Hyundai 15/30-Day Happiness Calling',
            true,
            'AFTER_DAYS(15)',
            'PHONE',
            (SELECT q.id FROM questionnaires q WHERE q.brand_id = b.id AND q.type = 'HAPPINESS' LIMIT 1),
            (SELECT rs.id FROM rating_scales rs WHERE rs.brand_id = b.id LIMIT 1),
            3, 24, 72, 1
        FROM brands b
        WHERE b.code = 'HYUN' OR UPPER(b.name) LIKE '%HYUNDAI%'
    """)

    op.execute("""
        INSERT INTO follow_up_programs (id, tenant_id, brand_id, code, label, enabled, trigger, channel, questionnaire_id, max_attempts, retry_gap_hours, sla_hours, sort_order)
        SELECT 
            gen_random_uuid(),
            b.tenant_id,
            b.id,
            'TNPS',
            COALESCE(b.tnps_label, 'Ather Energy TNPS'),
            true,
            'ON_IMPORT',
            'PHONE',
            (SELECT q.id FROM questionnaires q WHERE q.brand_id = b.id AND q.type = 'TNPS' LIMIT 1),
            3, 24, 48, 0
        FROM brands b
        WHERE b.code = 'ATHER' OR UPPER(b.name) LIKE '%ATHER%'
    """)

    op.execute("""
        INSERT INTO follow_up_programs (id, tenant_id, brand_id, code, label, enabled, trigger, channel, questionnaire_id, rating_scale_id, max_attempts, retry_gap_hours, sla_hours, sort_order)
        SELECT 
            gen_random_uuid(),
            b.tenant_id,
            b.id,
            'PSF',
            'Tata Motors Post Service Feedback (PSF)',
            true,
            'ON_IMPORT',
            'PHONE',
            (SELECT q.id FROM questionnaires q WHERE q.brand_id = b.id AND q.type = 'PSF' LIMIT 1),
            (SELECT rs.id FROM rating_scales rs WHERE rs.brand_id = b.id LIMIT 1),
            3, 24, 48, 0
        FROM brands b
        WHERE b.code = 'TATA' OR UPPER(b.name) LIKE '%TATA%'
    """)

    op.execute("""
        INSERT INTO follow_up_programs (id, tenant_id, brand_id, code, label, enabled, trigger, channel, questionnaire_id, rating_scale_id, max_attempts, retry_gap_hours, sla_hours, sort_order)
        SELECT 
            gen_random_uuid(),
            b.tenant_id,
            b.id,
            'PSF',
            'MG Motors Post Service Feedback (PSF)',
            true,
            'ON_IMPORT',
            'PHONE',
            (SELECT q.id FROM questionnaires q WHERE q.brand_id = b.id AND q.type = 'PSF' LIMIT 1),
            (SELECT rs.id FROM rating_scales rs WHERE rs.brand_id = b.id LIMIT 1),
            3, 24, 48, 0
        FROM brands b
        WHERE b.code = 'MG' OR UPPER(b.name) LIKE '%MG%'
    """)

    op.execute("""
        UPDATE followup_queues fq
        SET program_id = p.id
        FROM follow_up_programs p, job_cards jc
        WHERE fq.job_card_id = jc.id
          AND fq.queue_type = p.code
          AND (p.brand_id = jc.brand_id OR (p.brand_id IS NULL AND NOT EXISTS (
              SELECT 1 FROM follow_up_programs p2 WHERE p2.brand_id = jc.brand_id AND p2.code = fq.queue_type
          )))
    """)


def downgrade() -> None:
    # 1. Drop program_id from followup_queues
    op.drop_index('ix_followup_queues_program_id', table_name='followup_queues')
    op.drop_column('followup_queues', 'program_id')

    # 2. Drop follow_up_programs table
    op.drop_index('ix_follow_up_programs_tenant_brand_order', table_name='follow_up_programs')
    op.drop_index('ix_follow_up_programs_brand_id', table_name='follow_up_programs')
    op.drop_index('ix_follow_up_programs_tenant_id', table_name='follow_up_programs')
    op.drop_table('follow_up_programs')

    # 3. Drop config_versions table
    op.drop_index('uq_config_versions_ver', table_name='config_versions')
    op.drop_index('ix_config_versions_lookup', table_name='config_versions')
    op.drop_index('ix_config_versions_tenant_id', table_name='config_versions')
    op.drop_table('config_versions')
