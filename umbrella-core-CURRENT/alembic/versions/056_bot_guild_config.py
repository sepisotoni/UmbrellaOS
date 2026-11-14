"""Store Discord bot discovery and configuration per guild.

Revision ID: 056_bot_guild_config
Revises:     055_fix_admin_role_permissions
"""

from alembic import op
import sqlalchemy as sa

revision = "056_bot_guild_config"
down_revision = "055_fix_admin_role_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_guilds",
        sa.Column("guild_id", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("channels", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("roles", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("staff_alert_channel_id", sa.String(length=32), nullable=True),
        sa.Column("verified_role_id", sa.String(length=32), nullable=True),
        sa.Column("owner_role_id", sa.String(length=32), nullable=True),
        sa.Column("admin_role_id", sa.String(length=32), nullable=True),
        sa.Column("moderator_role_id", sa.String(length=32), nullable=True),
        sa.Column("helper_role_id", sa.String(length=32), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "pushed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("bot_guilds")
