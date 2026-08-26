"""bot_command_manifest — stores the Discord bot's slash command list.

The bot pushes its full command manifest on startup via
POST /api/v1/bot/commands. The dashboard reads it via
GET /api/v1/bot/commands to display real command data.

Revision ID: 036_bot_command_manifest
Revises:     035_plugin_console_lines
Create Date: 2026-08-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "036_bot_command_manifest"
down_revision = "035_plugin_console_lines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_command_manifest",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("commands", sa.Text(), nullable=False),
        sa.Column(
            "pushed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("bot_command_manifest")
