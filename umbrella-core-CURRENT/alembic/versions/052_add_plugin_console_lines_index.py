"""add_plugin_console_lines_index

[PLUGIN] subsystem audit: plugin_console_lines.server_id was explicitly
index=False despite every query against this table filtering on it
combined with ORDER BY captured_at. See models/plugin_console_line.py's
column docstring for the full rationale on why this is a composite index
rather than a single-column one.

Revision ID: 052_add_plugin_console_lines_index
Revises:     051_add_mc_commands_server_id
Create Date: 2026-08-31
"""
import sqlalchemy as sa
from alembic import op

revision = "052_add_plugin_console_lines_index"
down_revision = "051_add_mc_commands_server_id"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_plugin_console_lines_server_id_captured_at"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text(f"""
            DO $$
            BEGIN
                CREATE INDEX {INDEX_NAME} ON plugin_console_lines (server_id, captured_at);
            EXCEPTION
                WHEN duplicate_table THEN NULL;
            END $$;
        """))
    else:
        try:
            op.create_index(INDEX_NAME, "plugin_console_lines", ["server_id", "captured_at"])
        except Exception:
            pass


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="plugin_console_lines")
