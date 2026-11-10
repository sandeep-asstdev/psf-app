"""ather tnps model correction

Revision ID: 0007_ather_tnps_model_correction
Revises: 0006_standard_dms_template
Create Date: 2026-11-10 14:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0007_ather_tnps_model_correction'
down_revision: Union[str, None] = '0006_standard_dms_template'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add legacy_tnps_date to job_cards
    op.add_column('job_cards', sa.Column('legacy_tnps_date', sa.Date(), nullable=True))
    op.create_index('ix_job_cards_legacy_tnps_date', 'job_cards', ['legacy_tnps_date'])

    # 2. Migrate existing scheduled_tnps_date values from followup_queues to job_cards.legacy_tnps_date (zero data loss)
    op.execute("""
        UPDATE job_cards
        SET legacy_tnps_date = followup_queues.scheduled_tnps_date
        FROM followup_queues
        WHERE followup_queues.job_card_id = job_cards.id
          AND followup_queues.scheduled_tnps_date IS NOT NULL
    """)

    # 3. Drop scheduled_tnps_date from followup_queues
    op.drop_column('followup_queues', 'scheduled_tnps_date')

    # 4. Add enable_tnps and tnps_label to brands table
    op.add_column('brands', sa.Column('enable_tnps', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('brands', sa.Column('tnps_label', sa.String(length=50), server_default='TNPS', nullable=False))

    # 5. Enable TNPS for Ather Energy brand
    op.execute("""
        UPDATE brands
        SET enable_tnps = true, tnps_label = 'TNPS'
        WHERE code = 'ATHER' OR UPPER(name) LIKE '%ATHER%'
    """)


def downgrade() -> None:
    # 1. Add scheduled_tnps_date back to followup_queues
    op.add_column('followup_queues', sa.Column('scheduled_tnps_date', sa.Date(), nullable=True))

    # 2. Restore values from job_cards.legacy_tnps_date
    op.execute("""
        UPDATE followup_queues
        SET scheduled_tnps_date = job_cards.legacy_tnps_date
        FROM job_cards
        WHERE followup_queues.job_card_id = job_cards.id
          AND job_cards.legacy_tnps_date IS NOT NULL
    """)

    # 3. Drop legacy_tnps_date from job_cards
    op.drop_index('ix_job_cards_legacy_tnps_date', table_name='job_cards')
    op.drop_column('job_cards', 'legacy_tnps_date')

    # 4. Drop enable_tnps and tnps_label from brands
    op.drop_column('brands', 'tnps_label')
    op.drop_column('brands', 'enable_tnps')

