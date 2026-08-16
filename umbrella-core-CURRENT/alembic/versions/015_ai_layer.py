"""Add AI operating-system layer: model configs, constitution rules, decision logs (Phase 5)

Revision ID: 015_ai_layer
Revises: 014_phase4_automation
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa


revision = '015_ai_layer'
down_revision = '014_phase4_automation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai_model_configs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('provider', sa.String(32), nullable=False),
        sa.Column('model_name', sa.String(128), nullable=False),
        sa.Column('task_type', sa.String(64), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_healthy', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_ai_model_configs_task_type', 'ai_model_configs', ['task_type'])

    op.create_table(
        'constitution_rules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tier', sa.Enum('PLATFORM_SAFETY', 'CORE_PLATFORM', 'SERVER', 'ROLE', 'TASK', name='constitutiontier'), nullable=False),
        sa.Column('title', sa.String(128), nullable=False),
        sa.Column('rule_text', sa.Text(), nullable=False),
        sa.Column('is_seed_rule', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'ai_decision_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('task_type', sa.String(64), nullable=False),
        sa.Column('requested_by', sa.String(64), nullable=True),
        sa.Column('input_summary', sa.Text(), nullable=False),
        sa.Column('output_summary', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('evidence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('retrieval_summary', sa.Text(), nullable=True),
        sa.Column('primary_provider', sa.String(32), nullable=False),
        sa.Column('primary_model', sa.String(128), nullable=False),
        sa.Column('secondary_provider', sa.String(32), nullable=True),
        sa.Column('secondary_model', sa.String(128), nullable=True),
        sa.Column('dual_review_agreement', sa.Boolean(), nullable=True),
        sa.Column('escalated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_ai_decision_logs_task_type', 'ai_decision_logs', ['task_type'])


def downgrade() -> None:
    op.drop_index('ix_ai_decision_logs_task_type', table_name='ai_decision_logs')
    op.drop_table('ai_decision_logs')
    op.drop_table('constitution_rules')
    op.drop_index('ix_ai_model_configs_task_type', table_name='ai_model_configs')
    op.drop_table('ai_model_configs')
    # Postgres enum types must be dropped explicitly and Postgres is this
    # project's production target — but SQLite has no DROP TYPE syntax at
    # all (confirmed by actually running this downgrade against SQLite
    # during development: it fails with a syntax error, not a no-op), so
    # this must be dialect-gated rather than run unconditionally.
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS constitutiontier')
