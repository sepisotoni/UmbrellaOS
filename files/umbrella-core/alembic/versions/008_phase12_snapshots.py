"""
alembic/versions/008_phase12_snapshots.py

Revision ID: 008_phase12_snapshots
Revises: 007_phase11_replay
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "008_phase12_snapshots"
down_revision = "007_phase11_replay"


def upgrade():
    # Create player_snapshots table
    op.create_table(
        "player_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("minecraft_uuid", sa.String(36), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trigger", sa.String(32), nullable=False, server_default="scheduled"),
        sa.Column("health", sa.Float(), nullable=True),
        sa.Column("food", sa.Integer(), nullable=True),
        sa.Column("xp", sa.Float(), nullable=True),
        sa.Column("inventory_json", sa.Text(), nullable=True),
        sa.Column("armor_json", sa.Text(), nullable=True),
        sa.Column("offhand_json", sa.Text(), nullable=True),
        sa.Column("x", sa.Float(), nullable=True),
        sa.Column("y", sa.Float(), nullable=True),
        sa.Column("z", sa.Float(), nullable=True),
        sa.Column("yaw", sa.Float(), nullable=True),
        sa.Column("pitch", sa.Float(), nullable=True),
        sa.Column("world", sa.String(128), nullable=True),
        sa.Column("dimension", sa.String(64), nullable=True),
        sa.Column("replay_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_player_snapshots_minecraft_uuid", "player_snapshots", ["minecraft_uuid"])
    op.create_index("ix_player_snapshots_timestamp", "player_snapshots", ["timestamp"])
    op.create_foreign_key(
        "fk_player_snapshots_replay_id_replay_sessions",
        "player_snapshots",
        "replay_sessions",
        ["replay_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    # Drop player_snapshots
    op.drop_constraint(
        "fk_player_snapshots_replay_id_replay_sessions",
        "player_snapshots",
        type_="foreignkey",
    )
    op.drop_index("ix_player_snapshots_timestamp", table_name="player_snapshots")
    op.drop_index("ix_player_snapshots_minecraft_uuid", table_name="player_snapshots")
    op.drop_table("player_snapshots")
