"""Phase 3 foundation models: players, IPs, punishments, appeals

Revision ID: 002_phase3_foundation_models
Revises: 001_initial
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa


revision = "002_phase3_foundation_models"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column("uuid", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("playtime", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("joins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deaths", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discord_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_players_username", "players", ["username"])

    op.create_table(
        "ip_addresses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("player_uuid", sa.String(36), sa.ForeignKey("players.uuid", ondelete="CASCADE"), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ip_addresses_player_uuid", "ip_addresses", ["player_uuid"])
    op.create_index("ix_ip_addresses_ip_address", "ip_addresses", ["ip_address"])

    op.create_table(
        "punishments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("player_uuid", sa.String(36), sa.ForeignKey("players.uuid", ondelete="CASCADE"), nullable=False),
        sa.Column("staff_id", sa.String(64), nullable=True),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.CheckConstraint("type IN ('warn', 'mute', 'tempban', 'ban')", name="ck_punishments_type"),
    )
    op.create_index("ix_punishments_player_uuid", "punishments", ["player_uuid"])

    op.create_table(
        "appeals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("punishment_id", sa.String(36), sa.ForeignKey("punishments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_uuid", sa.String(36), sa.ForeignKey("players.uuid", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('open', 'accepted', 'denied')", name="ck_appeals_status"),
    )
    op.create_index("ix_appeals_punishment_id", "appeals", ["punishment_id"])
    op.create_index("ix_appeals_player_uuid", "appeals", ["player_uuid"])


def downgrade() -> None:
    op.drop_index("ix_appeals_player_uuid", table_name="appeals")
    op.drop_index("ix_appeals_punishment_id", table_name="appeals")
    op.drop_table("appeals")

    op.drop_index("ix_punishments_player_uuid", table_name="punishments")
    op.drop_table("punishments")

    op.drop_index("ix_ip_addresses_ip_address", table_name="ip_addresses")
    op.drop_index("ix_ip_addresses_player_uuid", table_name="ip_addresses")
    op.drop_table("ip_addresses")

    op.drop_index("ix_players_username", table_name="players")
    op.drop_table("players")
