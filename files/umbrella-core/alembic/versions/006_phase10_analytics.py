"""Phase 10 Analytics Pipeline: Event tracking and player statistics

Revision ID: 006_phase10_analytics
Revises: 005_phase9_alt_detection
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa


revision = "006_phase10_analytics"
down_revision = "005_phase9_alt_detection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create analytics_events table
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("minecraft_uuid", sa.String(36), nullable=True),
        sa.Column("data_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_analytics_events_event_type", "analytics_events", ["event_type"])
    op.create_index("ix_analytics_events_minecraft_uuid", "analytics_events", ["minecraft_uuid"])
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"])

    # Create player_stats table
    op.create_table(
        "player_stats",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("minecraft_uuid", sa.String(36), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("value", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("period", sa.String(16), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_player_stats_minecraft_uuid", "player_stats", ["minecraft_uuid"])
    op.create_unique_constraint(
        "uq_player_stats_player_metric_period",
        "player_stats",
        ["minecraft_uuid", "metric", "period", "period_start"],
    )


def downgrade() -> None:
    # Drop player_stats table
    op.drop_constraint("uq_player_stats_player_metric_period", "player_stats", type_="unique")
    op.drop_index("ix_player_stats_minecraft_uuid", table_name="player_stats")
    op.drop_table("player_stats")
    
    # Drop analytics_events table
    op.drop_index("ix_analytics_events_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_minecraft_uuid", table_name="analytics_events")
    op.drop_index("ix_analytics_events_event_type", table_name="analytics_events")
    op.drop_table("analytics_events")
