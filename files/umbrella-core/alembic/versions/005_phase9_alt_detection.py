"""Phase 9 Alt Detection: Suspicion scoring and alt detection

Revision ID: 005_phase9_alt_detection
Revises: 004_phase8_verification
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa


revision = "005_phase9_alt_detection"
down_revision = "004_phase8_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add suspicion_score column to players table
    op.add_column("players", sa.Column("suspicion_score", sa.Integer(), nullable=False, server_default="0"))
    
    # Create suspicion_events table
    op.create_table(
        "suspicion_events",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("player_uuid", sa.String(36), nullable=False, index=True),
        sa.Column("trigger", sa.String(128), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reviewed_by", sa.String(128), nullable=True),
        sa.Column("false_positive", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_suspicion_events_player_uuid", "suspicion_events", ["player_uuid"])

    # Create alt_groups table
    op.create_table(
        "alt_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Create alt_group_members table
    op.create_table(
        "alt_group_members",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("group_id", sa.Integer(), nullable=False, index=True),
        sa.Column("player_uuid", sa.String(36), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("added_by", sa.String(128), nullable=True),
    )
    op.create_foreign_key(
        "fk_alt_group_members_group_id",
        "alt_group_members",
        "alt_groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Drop alt_group_members table
    op.drop_constraint("fk_alt_group_members_group_id", "alt_group_members", type_="foreignkey")
    op.drop_table("alt_group_members")
    
    # Drop alt_groups table
    op.drop_table("alt_groups")
    
    # Drop suspicion_events table
    op.drop_index("ix_suspicion_events_player_uuid", table_name="suspicion_events")
    op.drop_table("suspicion_events")
    
    # Remove suspicion_score column from players table
    op.drop_column("players", "suspicion_score")
