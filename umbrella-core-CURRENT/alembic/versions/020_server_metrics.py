"""Add server_metric_snapshots table - time-series for predictive crash prevention / NL ops queries (Phase 5)

Revision ID: 020_server_metrics
Revises: 019_memory
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa


revision = '020_server_metrics'
down_revision = '019_memory'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'server_metric_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('server_id', sa.String(64), nullable=False),
        sa.Column('tps', sa.Float(), nullable=False),
        sa.Column('online_count', sa.Integer(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_server_metric_snapshots_server_id', 'server_metric_snapshots', ['server_id'])
    op.create_index('ix_server_metric_snapshots_recorded_at', 'server_metric_snapshots', ['recorded_at'])


def downgrade() -> None:
    op.drop_index('ix_server_metric_snapshots_recorded_at', table_name='server_metric_snapshots')
    op.drop_index('ix_server_metric_snapshots_server_id', table_name='server_metric_snapshots')
    op.drop_table('server_metric_snapshots')
