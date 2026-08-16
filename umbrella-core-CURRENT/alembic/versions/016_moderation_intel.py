"""Add moderation intelligence layer: reports, analyses, staff escalations (Phase 5, ported from Moo-assistant)

Revision ID: 016_moderation_intel
Revises: 015_ai_layer
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa


revision = '016_moderation_intel'
down_revision = '015_ai_layer'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'moderation_actions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(32), nullable=False),
        sa.Column('moderator_id', sa.String(32), nullable=False),
        sa.Column(
            'action_type',
            sa.Enum('WARN', 'DELETE_MESSAGE', 'TIMEOUT', 'UNTIMEOUT', 'KICK', 'BAN', name='moderationactiontype'),
            nullable=False,
        ),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_moderation_actions_user_id', 'moderation_actions', ['user_id'])

    op.create_table(
        'moderation_reports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('reported_user_id', sa.String(32), nullable=False),
        sa.Column('reporter_id', sa.String(32), nullable=True),
        sa.Column('channel_id', sa.String(32), nullable=True),
        sa.Column('reported_message_id', sa.String(32), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False, server_default='user'),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'AUTO_RESOLVED', 'ESCALATED', 'DISMISSED', name='reportstatus'),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_moderation_reports_reported_user_id', 'moderation_reports', ['reported_user_id'])
    op.create_index('ix_moderation_reports_status', 'moderation_reports', ['status'])

    op.create_table(
        'moderation_analyses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('report_id', sa.String(36), sa.ForeignKey('moderation_reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column(
            'recommended_action',
            sa.Enum('NONE', 'WARN', 'DELETE_MESSAGE', 'TIMEOUT', 'ESCALATE', name='recommendedaction'),
            nullable=False,
        ),
        sa.Column('evidence_summary', sa.Text(), nullable=False),
        sa.Column('primary_model', sa.String(150), nullable=False),
        sa.Column('secondary_model', sa.String(150), nullable=True),
        sa.Column('agreement', sa.Boolean(), nullable=True),
        sa.Column('action_taken', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_moderation_analyses_report_id', 'moderation_analyses', ['report_id'])

    op.create_table(
        'staff_escalations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('related_report_id', sa.String(36), sa.ForeignKey('moderation_reports.id', ondelete='SET NULL'), nullable=True),
        sa.Column('related_investigation_id', sa.String(36), nullable=True),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_by', sa.String(32), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_staff_escalations_resolved', 'staff_escalations', ['resolved'])


def downgrade() -> None:
    op.drop_index('ix_staff_escalations_resolved', table_name='staff_escalations')
    op.drop_table('staff_escalations')
    op.drop_index('ix_moderation_analyses_report_id', table_name='moderation_analyses')
    op.drop_table('moderation_analyses')
    op.drop_index('ix_moderation_reports_status', table_name='moderation_reports')
    op.drop_index('ix_moderation_reports_reported_user_id', table_name='moderation_reports')
    op.drop_table('moderation_reports')
    op.drop_index('ix_moderation_actions_user_id', table_name='moderation_actions')
    op.drop_table('moderation_actions')
    # See 015_ai_layer.py's downgrade() for why this is dialect-gated:
    # SQLite has no DROP TYPE syntax at all.
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS recommendedaction')
        op.execute('DROP TYPE IF EXISTS reportstatus')
        op.execute('DROP TYPE IF EXISTS moderationactiontype')
