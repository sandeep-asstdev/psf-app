"""0010_label_overrides

Revision ID: 0010_label_overrides
Revises: 0009_questions_scoring_rules
Create Date: 2026-11-10

Slice 3: Label overrides for customizable UI terminology (CRE, Delight, TNPS, Job Card, Complaint).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0010_label_overrides'
down_revision: Union[str, None] = '0009_questions_scoring_rules'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create label_overrides table
    op.create_table(
        'label_overrides',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('value', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('tenant_id', 'key', 'language', name='uq_label_override_tenant_key_lang'),
    )
    op.create_index('idx_label_overrides_tenant_key', 'label_overrides', ['tenant_id', 'key'])

    # Seed default terminology for all existing tenants
    op.execute(
        """
        INSERT INTO label_overrides (id, tenant_id, key, language, value)
        SELECT 
            gen_random_uuid(),
            t.id,
            v.key,
            'en',
            v.val
        FROM tenants t
        CROSS JOIN (
            VALUES 
                ('CRE', 'Customer Relationship Executive'),
                ('DELIGHT', 'Delight'),
                ('TNPS', 'Follow-up Program'),
                ('JOB_CARD', 'Job Card'),
                ('COMPLAINT', 'Customer Complaint')
        ) AS v(key, val)
        ON CONFLICT (tenant_id, key, language) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_index('idx_label_overrides_tenant_key', table_name='label_overrides')
    op.drop_table('label_overrides')
