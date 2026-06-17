"""
alembic/versions/009_phase13_ai_tasks.py

Revision ID: 009_phase13_ai_tasks
Revises: 008_phase12_snapshots
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "009_phase13_ai_tasks"
down_revision = "008_phase12_snapshots"


def upgrade():
    # Create ai_tasks table
    op.create_table(
        "ai_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("player_uuid", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=False),
        sa.Column("ai_recommendation", sa.String(256), nullable=False),
        sa.Column("ai_confidence", sa.Float(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(64), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("action_taken", sa.String(256), nullable=True),
    )
    op.create_index("ix_ai_tasks_player_uuid", "ai_tasks", ["player_uuid"])


def downgrade():
    # Drop ai_tasks
    op.drop_index("ix_ai_tasks_player_uuid", table_name="ai_tasks")
    op.drop_table("ai_tasks")
