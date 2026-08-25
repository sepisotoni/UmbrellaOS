"""plugin_heartbeats_and_commands — create tables for plugin heartbeat registry and plugin control commands.

plugin_heartbeats: keyed by server_id (one row per connected Minecraft server).
  Written on every POST /api/v1/plugin/heartbeat call. The dashboard reads
  this to show live server status, TPS, online player count, and plugin version.

plugin_commands: queued control commands issued via POST /api/v1/plugin/control.
  Separate from mc_commands (Discord-initiated commands that the plugin polls and
  executes) — plugin_commands are umbrella-core-initiated control signals.

Both tables were registered with SQLAlchemy Base but had no Alembic migration,
causing 'relation does not exist' 500s on any Alembic-managed (production) database.

Revision ID: 034_plugin_heartbeats_and_commands
Revises:     033_add_anticheat_violations_table
Create Date: 2026-08-26
"""
import sqlalchemy as sa
from alembic import op

revision = "034_plugin_heartbeats_and_commands"
down_revision = "033_add_anticheat_violations_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plugin_heartbeats",
        sa.Column("server_id", sa.String(length=64), primary_key=True),
        sa.Column("server_name", sa.String(length=128), nullable=False, server_default="Minecraft Server"),
        sa.Column("online_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tps", sa.Float(), nullable=False, server_default="20.0"),
        sa.Column("version", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("plugin_version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("grim_connected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "last_seen",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "plugin_commands",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("plugin_name", sa.String(length=128), nullable=True, index=True),
        sa.Column("action", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("plugin_commands")
    op.drop_table("plugin_heartbeats")
