"""bot_guild_channels — stores Discord guild text channel list pushed by bot.

Bot pushes on startup via POST /api/v1/bot/channels.
Dashboard reads via GET /api/v1/bot/channels to populate broadcaster dropdown.

Revision ID: 037_bot_guild_channels
Revises:     036_bot_command_manifest
Create Date: 2026-08-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "037_bot_guild_channels"
down_revision = "036_bot_command_manifest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_guild_channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channels", sa.Text(), nullable=False),
        sa.Column(
            "pushed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("bot_guild_channels")
