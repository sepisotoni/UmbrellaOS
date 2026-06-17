"""Phase 8 Verification: Player verification system

Revision ID: 004_phase8_verification
Revises: 003_phase7_discord_bridge
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa


revision = "004_phase8_verification"
down_revision = "003_phase7_discord_bridge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create verification_codes table
    op.create_table(
        "verification_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("player_uuid", sa.String(36), nullable=False, index=True),
        sa.Column("player_username", sa.String(64), nullable=False),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ip_address", sa.String(45), nullable=True),
    )
    op.create_index("ix_verification_codes_code", "verification_codes", ["code"], unique=True)
    op.create_index("ix_verification_codes_player_uuid", "verification_codes", ["player_uuid"])

    # Add new columns to discord_accounts table
    op.add_column("discord_accounts", sa.Column("banned", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("discord_accounts", sa.Column("ban_reason", sa.String(256), nullable=True))
    op.add_column("discord_accounts", sa.Column("previous_usernames", sa.String(512), nullable=True))


def downgrade() -> None:
    # Remove new columns from discord_accounts table
    op.drop_column("discord_accounts", "previous_usernames")
    op.drop_column("discord_accounts", "ban_reason")
    op.drop_column("discord_accounts", "banned")

    # Drop verification_codes table
    op.drop_index("ix_verification_codes_player_uuid", table_name="verification_codes")
    op.drop_index("ix_verification_codes_code", table_name="verification_codes")
    op.drop_table("verification_codes")
