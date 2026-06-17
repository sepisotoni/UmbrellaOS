"""Phase 7 Discord bridge: Discord accounts and chat messages

Revision ID: 003_phase7_discord_bridge
Revises: 002_phase3_foundation_models
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa


revision = "003_phase7_discord_bridge"
down_revision = "002_phase3_foundation_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discord_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("discord_id", sa.String(32), nullable=False),
        sa.Column("player_uuid", sa.String(36), sa.ForeignKey("players.uuid", ondelete="SET NULL"), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discord_username", sa.String(64), nullable=True),
    )
    op.create_index("ix_discord_accounts_discord_id", "discord_accounts", ["discord_id"], unique=True)
    op.create_index("ix_discord_accounts_player_uuid", "discord_accounts", ["player_uuid"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("player_uuid", sa.String(36), sa.ForeignKey("players.uuid", ondelete="SET NULL"), nullable=True),
        sa.Column("discord_id", sa.String(32), nullable=True),
        sa.Column("discord_channel_id", sa.String(32), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("translated_message", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("filtered", sa.Boolean(), nullable=False, server_default="false"),
        sa.CheckConstraint("source IN ('minecraft', 'discord')", name="ck_chat_messages_source"),
    )
    op.create_index("ix_chat_messages_source", "chat_messages", ["source"])
    op.create_index("ix_chat_messages_player_uuid", "chat_messages", ["player_uuid"])
    op.create_index("ix_chat_messages_discord_id", "chat_messages", ["discord_id"])

    # Add bridge settings to settings table
    op.execute("""
        INSERT INTO settings (key, value, category, description, sensitive, requires_restart)
        VALUES 
            ('bridge.mode', 'off', 'bridge', 'Bridge mode: off, partial, or full', false, false),
            ('bridge.mc_to_discord', 'true', 'bridge', 'Forward Minecraft chat to Discord', false, false),
            ('bridge.discord_to_mc', 'true', 'bridge', 'Forward Discord chat to Minecraft', false, false),
            ('bridge.show_avatars', 'true', 'bridge', 'Show avatars in bridged messages', false, false),
            ('bridge.discord_channel_id', '', 'bridge', 'Discord channel ID for bridging', false, false)
    """)


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key LIKE 'bridge.%'")
    
    op.drop_index("ix_chat_messages_discord_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_player_uuid", table_name="chat_messages")
    op.drop_index("ix_chat_messages_source", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_discord_accounts_player_uuid", table_name="discord_accounts")
    op.drop_index("ix_discord_accounts_discord_id", table_name="discord_accounts")
    op.drop_table("discord_accounts")
