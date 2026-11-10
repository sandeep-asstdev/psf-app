"""reconfirmations is_deleted default

Revision ID: 0003_reconf_is_deleted
Revises: 0002_real_data_alignment
Create Date: 2026-11-02 17:56:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_reconf_is_deleted'
down_revision: Union[str, None] = '0002_real_data_alignment'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    reconf_cols = set(c["name"] for c in insp.get_columns("reconfirmations"))

    if "is_deleted" not in reconf_cols:
        op.add_column(
            'reconfirmations',
            sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False)
        )
        op.create_index('ix_reconfirmations_is_deleted', 'reconfirmations', ['is_deleted'])
    else:
        op.alter_column(
            'reconfirmations',
            'is_deleted',
            server_default=sa.text('false'),
            nullable=False,
        )

    if "deleted_at" not in reconf_cols:
        op.add_column(
            'reconfirmations',
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    op.alter_column(
        'reconfirmations',
        'is_deleted',
        server_default=None,
        nullable=True,
    )

