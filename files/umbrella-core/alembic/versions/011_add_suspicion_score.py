"""Add suspicion_score column to players table

Revision ID: 011_add_suspicion_score
Revises: 010_mc_commands_translation
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa


revision = '011_add_suspicion_score'
down_revision = '010_mc_commands_translation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('players', sa.Column('suspicion_score', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('players', 'suspicion_score')
