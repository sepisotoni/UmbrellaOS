"""Add notified_at to staff_escalations - tracks whether umbrella-discord's
notification poller has already announced this escalation, so restarts
don't cause duplicate posts (Phase 6).

Revision ID: 021_escalation_notified_at
Revises: 020_server_metrics
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa


revision = '021_escalation_notified_at'
down_revision = '020_server_metrics'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'staff_escalations',
        sa.Column('notified_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('staff_escalations', 'notified_at')
