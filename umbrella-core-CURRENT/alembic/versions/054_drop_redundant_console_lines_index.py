"""drop_redundant_console_lines_index

Cleanup for the mistake documented in 052_add_plugin_console_lines_index's
module docstring: that migration's original (buggy) version created
"ix_plugin_console_lines_server_id_captured_at" — a composite index
redundant with "ix_plugin_console_lines_server_id_ts", which
035_plugin_console_lines.py has created since this table's very first
migration. Confirmed live in production (real Supabase, per [CURSOR]'s
check) before this fix landed — the buggy 052 had already run there.

Runs on every upgrade path downstream of 052, whether or not a given
database actually hit the bug:
  - Production and any other database that ran the original buggy 052:
    has the redundant index, DROP INDEX IF EXISTS removes it.
  - Any fresh database created after 052 was corrected to a no-op: never
    had the redundant index in the first place, DROP INDEX IF EXISTS is
    silently a no-op.
Either way this migration is idempotent and safe to run unconditionally.

Revision ID: 054_drop_redundant_console_lines_index
Revises:     052_add_plugin_console_lines_index
Create Date: 2026-08-31
"""
import sqlalchemy as sa
from alembic import op

revision = "054_drop_redundant_console_lines_index"
down_revision = "053_add_discord_role_id_settings"
branch_labels = None
depends_on = None

REDUNDANT_INDEX_NAME = "ix_plugin_console_lines_server_id_captured_at"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text(f"DROP INDEX IF EXISTS {REDUNDANT_INDEX_NAME}"))
    else:
        # SQLite: op.drop_index has no IF EXISTS equivalent via Alembic's
        # generic API on every SQLite backend version, so guard with a
        # try/except instead — same pattern used elsewhere in this repo
        # for SQLite-side idempotent DDL.
        try:
            op.drop_index(REDUNDANT_INDEX_NAME, table_name="plugin_console_lines")
        except Exception:
            pass


def downgrade() -> None:
    # Deliberately not recreated on downgrade — it was never supposed to
    # exist. Downgrading past this point returns to the (buggy) state
    # where 052 may or may not have created it depending on which version
    # of 052 was applied; not worth reproducing that ambiguity here.
    pass
