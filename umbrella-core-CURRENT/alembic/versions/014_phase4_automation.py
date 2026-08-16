"""Add backups and schedules tables (Phase 4)

Revision ID: 014_phase4_automation
Revises: 013_identity_phase3
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa


revision = '014_phase4_automation'
down_revision = '013_identity_phase3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('servers', sa.Column('crash_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('servers', sa.Column('last_crash_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'backups',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('server_id', sa.String(36), sa.ForeignKey('servers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='pending'),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_backups_server_id', 'backups', ['server_id'])

    op.create_table(
        'schedules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('cron_expression', sa.String(64), nullable=False),
        sa.Column('capability_name', sa.String(128), nullable=False),
        sa.Column('capability_params', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_status', sa.String(16), nullable=True),
        sa.Column('last_run_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('schedules')
    op.drop_index('ix_backups_server_id', table_name='backups')
    op.drop_table('backups')
    op.drop_column('servers', 'last_crash_at')
    op.drop_column('servers', 'crash_count')
