"""standard dms import template and batch file hash

Revision ID: 0006_standard_dms_template
Revises: 0005_auto_call_allocation
Create Date: 2026-11-03 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0006_standard_dms_template'
down_revision: Union[str, None] = '0005_auto_call_allocation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add file_hash to import_batches
    op.add_column('import_batches', sa.Column('file_hash', sa.String(length=64), nullable=True))
    op.create_index('ix_import_batches_file_hash', 'import_batches', ['tenant_id', 'file_hash'])

    # 2. Make brand_id nullable on import_batches for multi-brand/row-level DMS files
    op.alter_column('import_batches', 'brand_id', existing_type=postgresql.UUID(as_uuid=True), nullable=True)


def downgrade() -> None:
    op.alter_column('import_batches', 'brand_id', existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.drop_index('ix_import_batches_file_hash', table_name='import_batches')
    op.drop_column('import_batches', 'file_hash')

