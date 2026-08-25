"""add_discord_avatar_hash

Revision ID: 032_add_discord_avatar_hash
Revises:     031_add_bot_registration
Create Date: 2026-08-24
"""
import sqlalchemy as sa
from alembic import op

revision = "032_add_discord_avatar_hash"
down_revision = "031_add_bot_registration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("discord_avatar_hash", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "discord_avatar_hash")
