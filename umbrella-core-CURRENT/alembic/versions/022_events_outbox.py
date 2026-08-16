"""Add events table - the durable outbox for Phase 7's event bus
(handoff-to-new-session-phase7-START.md, Decision 1). See
models/events.py's module docstring for the full reasoning, including why
next_attempt_at exists beyond the decision doc's original column list.

Revision ID: 022_events_outbox
Revises: 021_escalation_notified_at
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa


revision = '022_events_outbox'
down_revision = '021_escalation_notified_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('topic', sa.String(length=150), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_events_topic', 'events', ['topic'])
    op.create_index('ix_events_created_at', 'events', ['created_at'])
    op.create_index('ix_events_dispatched_at', 'events', ['dispatched_at'])


def downgrade() -> None:
    op.drop_index('ix_events_dispatched_at', table_name='events')
    op.drop_index('ix_events_created_at', table_name='events')
    op.drop_index('ix_events_topic', table_name='events')
    op.drop_table('events')
