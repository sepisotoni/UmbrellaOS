"""Widen knowledge_entries.discord_message_id from VARCHAR(32) to VARCHAR(64).

Dashboard-created entries previously used f"dashboard-{uuid}" (46 chars),
which overflowed the original String(32) column. The REST create path now
writes a 32-char dash-prefixed id; widening gives headroom for Discord
snowflakes and any remaining prefixed ids.

Revision ID: 044_widen_knowledge_discord_message_id
Revises: 043_ai_model_configs_unique
Create Date: 2026-08-29
"""
from alembic import op
import sqlalchemy as sa

revision = "044_widen_knowledge_discord_message_id"
down_revision = "043_ai_model_configs_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("knowledge_entries") as batch_op:
        batch_op.alter_column(
            "discord_message_id",
            existing_type=sa.String(32),
            type_=sa.String(64),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("knowledge_entries") as batch_op:
        batch_op.alter_column(
            "discord_message_id",
            existing_type=sa.String(64),
            type_=sa.String(32),
            existing_nullable=False,
        )
