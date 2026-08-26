"""bot_guild_roles — stores Discord guild mentionable role list pushed by bot.

Bot pushes on startup via POST /api/v1/bot/roles.
Dashboard reads via GET /api/v1/bot/roles to populate broadcaster role-mention dropdown.

Revision ID: 038_bot_guild_roles
Revises:     037_bot_guild_channels
Create Date: 2026-08-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "038_bot_guild_roles"
down_revision = "037_bot_guild_channels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_guild_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("roles", sa.Text(), nullable=False),
        sa.Column(
            "pushed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("bot_guild_roles")
