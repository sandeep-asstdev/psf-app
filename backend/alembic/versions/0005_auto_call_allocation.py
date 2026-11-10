"""automatic equal call allocation tables

Revision ID: 0005_auto_call_allocation
Revises: 0004_role_hierarchy_perms
Create Date: 2026-11-03 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0005_auto_call_allocation'
down_revision: Union[str, None] = '0004_role_hierarchy_perms'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Attendance Overrides
    op.create_table(
        'attendance_overrides',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attendance_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('marked_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('uq_attendance_overrides_tenant_user_date', 'attendance_overrides', ['tenant_id', 'user_id', 'attendance_date'], unique=True)
    op.create_index('ix_attendance_overrides_date', 'attendance_overrides', ['attendance_date'])

    # 2. Allocation Runs
    op.create_table(
        'allocation_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('import_batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('import_batches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('run_type', sa.String(length=40), server_default='IMPORT_ALLOCATION', nullable=False),
        sa.Column('strategy', sa.String(length=40), server_default='EQUAL_PRESENT_CRE', nullable=False),
        sa.Column('present_cre_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_items', sa.Integer(), server_default='0', nullable=False),
        sa.Column('allocated_items', sa.Integer(), server_default='0', nullable=False),
        sa.Column('unallocated_items', sa.Integer(), server_default='0', nullable=False),
        sa.Column('started_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('undone_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('undone_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_allocation_runs_tenant_created', 'allocation_runs', ['tenant_id', 'created_at'])
    op.create_index('ix_allocation_runs_batch', 'allocation_runs', ['import_batch_id'])

    # 3. Allocation Assignments
    op.create_table(
        'allocation_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('allocation_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('queue_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('followup_queues.id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('to_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reason', sa.String(length=50), server_default='IMPORT_EQUAL_SPLIT', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_allocation_assignments_run_id', 'allocation_assignments', ['run_id'])
    op.create_index('ix_allocation_assignments_queue_item', 'allocation_assignments', ['queue_item_id'])

    # 4. Allocation Cursors
    op.create_table(
        'allocation_cursors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('pool_key', sa.String(length=60), nullable=False),
        sa.Column('last_cre_index', sa.Integer(), server_default='0', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('uq_allocation_cursors_tenant_pool', 'allocation_cursors', ['tenant_id', 'pool_key'], unique=True)


def downgrade() -> None:
    op.drop_table('allocation_cursors')
    op.drop_table('allocation_assignments')
    op.drop_table('allocation_runs')
    op.drop_table('attendance_overrides')

