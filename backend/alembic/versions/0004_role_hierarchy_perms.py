"""role hierarchy and dynamic permissions matrix

Revision ID: 0004_role_hierarchy_perms
Revises: 0003_reconf_is_deleted
Create Date: 2026-11-03 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0004_role_hierarchy_perms'
down_revision: Union[str, None] = '0003_reconf_is_deleted'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update roles table
    op.add_column('roles', sa.Column('level', sa.String(length=20), server_default='L3', nullable=False))
    op.add_column('roles', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('roles', sa.Column('dashboard_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('roles', sa.Column('field_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index('ix_roles_is_active', 'roles', ['is_active'])

    # 2. Add reason to audit_logs
    op.add_column('audit_logs', sa.Column('reason', sa.Text(), nullable=True))

    # 3. Add status to questionnaires
    op.add_column('questionnaires', sa.Column('status', sa.String(length=30), server_default='PUBLISHED', nullable=False))
    op.create_index('ix_questionnaires_status', 'questionnaires', ['status'])

    # 4. Create role_permissions table
    conn = op.get_bind()
    insp = sa.inspect(conn)
    existing_tables = set(insp.get_table_names())

    if 'role_permissions' not in existing_tables:
        op.create_table(
            'role_permissions',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
            sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
            sa.Column('permission', sa.String(length=80), nullable=False),
            sa.Column('data_scope', sa.String(length=40), server_default='ALL', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )
        op.create_index('uq_role_permissions_tenant_role_perm', 'role_permissions', ['tenant_id', 'role_id', 'permission'], unique=True)
        op.create_index('ix_role_permissions_role_perm', 'role_permissions', ['role_id', 'permission'])

    # 5. Create service_types table
    if 'service_types' not in existing_tables:
        op.create_table(
            'service_types',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('code', sa.String(length=50), nullable=False),
            sa.Column('color', sa.String(length=30), nullable=True),
            sa.Column('icon', sa.String(length=30), nullable=True),
            sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
            sa.Column('behaviour_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )
        op.create_index('uq_service_types_tenant_code', 'service_types', ['tenant_id', 'code'], unique=True)
        op.create_index('ix_service_types_is_active', 'service_types', ['is_active'])

    # 6. Create custom_field_definitions table
    if 'custom_field_definitions' not in existing_tables:
        op.create_table(
            'custom_field_definitions',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
            sa.Column('brand_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brands.id', ondelete='CASCADE'), nullable=True),
            sa.Column('entity_type', sa.String(length=40), nullable=False),
            sa.Column('field_key', sa.String(length=60), nullable=False),
            sa.Column('field_label', sa.String(length=100), nullable=False),
            sa.Column('field_type', sa.String(length=30), server_default='TEXT', nullable=False),
            sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('is_required', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )
        op.create_index('uq_custom_fields_tenant_entity_key', 'custom_field_definitions', ['tenant_id', 'entity_type', 'field_key'], unique=True)

    # 7. Create import_mapping_templates table
    if 'import_mapping_templates' not in existing_tables:
        op.create_table(
            'import_mapping_templates',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
            sa.Column('brand_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brands.id', ondelete='CASCADE'), nullable=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('column_mapping', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )
        op.create_index('uq_import_templates_tenant_name', 'import_mapping_templates', ['tenant_id', 'name'], unique=True)

    # 8. Create config_change_histories table
    if 'config_change_histories' not in existing_tables:
        op.create_table(
            'config_change_histories',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
            sa.Column('config_type', sa.String(length=60), nullable=False),
            sa.Column('entity_id', sa.String(length=100), nullable=True),
            sa.Column('version', sa.Integer(), server_default='1', nullable=False),
            sa.Column('status', sa.String(length=30), server_default='PUBLISHED', nullable=False),
            sa.Column('config_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('changed_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )
        op.create_index('ix_config_history_tenant_type_ver', 'config_change_histories', ['tenant_id', 'config_type', 'version'])


def downgrade() -> None:
    op.drop_table('config_change_histories')
    op.drop_table('import_mapping_templates')
    op.drop_table('custom_field_definitions')
    op.drop_table('service_types')
    op.drop_table('role_permissions')
    op.drop_index('ix_questionnaires_status', table_name='questionnaires')
    op.drop_column('questionnaires', 'status')
    op.drop_column('audit_logs', 'reason')
    op.drop_index('ix_roles_is_active', table_name='roles')
    op.drop_column('roles', 'field_rules')
    op.drop_column('roles', 'dashboard_config')
    op.drop_column('roles', 'is_active')
    op.drop_column('roles', 'level')
