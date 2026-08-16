"""Add knowledge base tables: entries, versions (Phase 5, ported from Moo-assistant)

Revision ID: 018_knowledge_base
Revises: 017_investigation_knowledge
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa


revision = '018_knowledge_base'
down_revision = '017_investigation_knowledge'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'knowledge_entries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('channel_id', sa.String(32), nullable=False),
        sa.Column('channel_name', sa.String(200), nullable=False),
        sa.Column('discord_message_id', sa.String(32), nullable=False, unique=True),
        sa.Column('author_id', sa.String(32), nullable=False),
        sa.Column('author_name', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column(
            'review_status',
            sa.Enum('APPROVED', 'PENDING', 'REJECTED', name='knowledgereviewstatus'),
            nullable=False,
            server_default='APPROVED',
        ),
        sa.Column('reviewed_by', sa.String(32), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('corrects_entry_id', sa.String(36), sa.ForeignKey('knowledge_entries.id', ondelete='SET NULL'), nullable=True),
        sa.Column('superseded_by_id', sa.String(36), sa.ForeignKey('knowledge_entries.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_knowledge_entries_channel_id', 'knowledge_entries', ['channel_id'])
    op.create_index('ix_knowledge_entries_discord_message_id', 'knowledge_entries', ['discord_message_id'])
    op.create_index('ix_knowledge_entries_review_status', 'knowledge_entries', ['review_status'])

    op.create_table(
        'knowledge_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('knowledge_entry_id', sa.String(36), sa.ForeignKey('knowledge_entries.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('edited_by', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_knowledge_versions_knowledge_entry_id', 'knowledge_versions', ['knowledge_entry_id'])


def downgrade() -> None:
    op.drop_index('ix_knowledge_versions_knowledge_entry_id', table_name='knowledge_versions')
    op.drop_table('knowledge_versions')
    op.drop_index('ix_knowledge_entries_review_status', table_name='knowledge_entries')
    op.drop_index('ix_knowledge_entries_discord_message_id', table_name='knowledge_entries')
    op.drop_index('ix_knowledge_entries_channel_id', table_name='knowledge_entries')
    op.drop_table('knowledge_entries')
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS knowledgereviewstatus')
