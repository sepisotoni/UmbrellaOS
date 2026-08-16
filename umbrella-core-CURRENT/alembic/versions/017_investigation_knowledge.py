"""Add knowledge reference data and investigation tables (Phase 5, ported from Moo-assistant)

Revision ID: 017_investigation_knowledge
Revises: 016_moderation_intel
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa


revision = '017_investigation_knowledge'
down_revision = '016_moderation_intel'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'known_issues',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by', sa.String(32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_known_issues_is_resolved', 'known_issues', ['is_resolved'])

    op.create_table(
        'whitelist_entries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('ingame_username', sa.String(100), nullable=False),
        sa.Column('discord_user_id', sa.String(32), nullable=True),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'APPROVED', 'DENIED', name='whiteliststatus'),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('ingame_username', name='uq_whitelist_entries_username'),
    )

    op.create_table(
        'investigations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('requested_by', sa.String(32), nullable=False),
        sa.Column('target_user_id', sa.String(32), nullable=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'investigation_findings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('investigation_id', sa.String(36), sa.ForeignKey('investigations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tool_key', sa.String(100), nullable=False),
        sa.Column('finding_text', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_investigation_findings_investigation_id', 'investigation_findings', ['investigation_id'])


def downgrade() -> None:
    op.drop_index('ix_investigation_findings_investigation_id', table_name='investigation_findings')
    op.drop_table('investigation_findings')
    op.drop_table('investigations')
    op.drop_table('whitelist_entries')
    op.drop_index('ix_known_issues_is_resolved', table_name='known_issues')
    op.drop_table('known_issues')
    # See 015_ai_layer.py's downgrade() for why this is dialect-gated.
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS whiteliststatus')
