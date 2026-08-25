"""plugin_console_lines — stores recent console output pushed by connected Minecraft plugins.

Capped at 500 rows per server_id (enforced in application layer on write).
The index on (server_id, captured_at DESC) makes the GET /console/recent
query fast: it filters by server_id then takes the N newest rows.

Revision ID: 035_plugin_console_lines
Revises:     034_plugin_heartbeats_and_commands
Create Date: 2026-08-26
"""
import sqlalchemy as sa
from alembic import op

revision = "035_plugin_console_lines"
down_revision = "034_plugin_heartbeats_and_commands"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plugin_console_lines",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("line", sa.Text(), nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_plugin_console_lines_server_id_ts",
        "plugin_console_lines",
        ["server_id", sa.text("captured_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_plugin_console_lines_server_id_ts", table_name="plugin_console_lines")
    op.drop_table("plugin_console_lines")
