"""Initial schema — Phase 1 foundation

Revision ID: 001_initial
Revises:
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- settings ---
    op.create_table(
        'settings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('key', sa.String(128), nullable=False, unique=True),
        sa.Column('value', sa.Text(), nullable=False, server_default=''),
        sa.Column('category', sa.String(64), nullable=False, server_default='general'),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('sensitive', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('requires_restart', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_settings_key', 'settings', ['key'])

    # --- audit_log ---
    op.create_table(
        'audit_log',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('actor', sa.String(128), nullable=False),
        sa.Column('actor_type', sa.String(32), nullable=False, server_default='system'),
        sa.Column('action', sa.String(128), nullable=False),
        sa.Column('target', sa.String(128), nullable=True),
        sa.Column('details_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_audit_log_action', 'audit_log', ['action'])
    op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])

    # --- roles ---
    op.create_table(
        'roles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(64), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- permissions ---
    op.create_table(
        'permissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('permission_key', sa.String(128), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_permissions_key', 'permissions', ['permission_key'])

    # --- role_permissions (join table) ---
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.String(36),
                  sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('permission_id', sa.String(36),
                  sa.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table('role_permissions')
    op.drop_index('ix_permissions_key', table_name='permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_index('ix_audit_log_created_at', table_name='audit_log')
    op.drop_index('ix_audit_log_action', table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_index('ix_settings_key', table_name='settings')
    op.drop_table('settings')
