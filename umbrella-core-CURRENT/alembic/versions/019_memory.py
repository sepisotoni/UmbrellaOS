"""Add memory domain table: memory_entries (Phase 5, ported from Moo-assistant)

Revision ID: 019_memory
Revises: 018_knowledge_base
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa


revision = '019_memory'
down_revision = '018_knowledge_base'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'memory_entries',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            'scope',
            sa.Enum('SHORT_TERM', 'SERVER', 'OPERATIONAL', name='memoryscope'),
            nullable=False,
        ),
        sa.Column('key', sa.String(300), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('hit_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('scope', 'key', name='uq_memory_scope_key'),
    )
    op.create_index('ix_memory_entries_scope', 'memory_entries', ['scope'])


def downgrade() -> None:
    op.drop_index('ix_memory_entries_scope', table_name='memory_entries')
    op.drop_table('memory_entries')
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS memoryscope')
