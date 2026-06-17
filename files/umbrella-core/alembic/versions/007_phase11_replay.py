"""
alembic/versions/007_phase11_replay.py

Revision ID: 007_phase11_replay
Revises: 006_phase10_analytics
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "007_phase11_replay"
down_revision = "006_phase10_analytics"


def upgrade():
    # Create replay_sessions table
    op.create_table(
        "replay_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trigger", sa.String(64), nullable=False),
        sa.Column("triggered_by", sa.String(128), nullable=False),
        sa.Column("minecraft_uuid", sa.String(36), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("incident_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_replay_sessions_minecraft_uuid", "replay_sessions", ["minecraft_uuid"])
    op.create_index("ix_replay_sessions_created_at", "replay_sessions", ["created_at"])

    # Create replay_events table
    op.create_table(
        "replay_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("replay_id", sa.String(36), nullable=False),
        sa.Column("minecraft_uuid", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_data_json", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("world", sa.String(128), nullable=True),
    )
    op.create_index("ix_replay_events_replay_id", "replay_events", ["replay_id"])
    op.create_index("ix_replay_events_minecraft_uuid", "replay_events", ["minecraft_uuid"])
    op.create_index("ix_replay_events_timestamp", "replay_events", ["timestamp"])
    op.create_foreign_key(
        "fk_replay_events_replay_id_replay_sessions",
        "replay_events",
        "replay_sessions",
        ["replay_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    # Drop replay_events first (due to foreign key)
    op.drop_constraint(
        "fk_replay_events_replay_id_replay_sessions",
        "replay_events",
        type_="foreignkey",
    )
    op.drop_index("ix_replay_events_timestamp", table_name="replay_events")
    op.drop_index("ix_replay_events_minecraft_uuid", table_name="replay_events")
    op.drop_index("ix_replay_events_replay_id", table_name="replay_events")
    op.drop_table("replay_events")

    # Drop replay_sessions
    op.drop_index("ix_replay_sessions_created_at", table_name="replay_sessions")
    op.drop_index("ix_replay_sessions_minecraft_uuid", table_name="replay_sessions")
    op.drop_table("replay_sessions")
