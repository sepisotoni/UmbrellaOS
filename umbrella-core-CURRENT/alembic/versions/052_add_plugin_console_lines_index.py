"""add_plugin_console_lines_index

CORRECTED to a no-op — see 054_drop_redundant_console_lines_index.py for
the full story. This revision id CANNOT be deleted or renumbered: real
production Supabase already applied the original version of this
migration (confirmed by [CURSOR] before this correction landed), so its
revision id is permanently recorded in that database's alembic_version
table. Removing this file would leave production's alembic_version
pointing at a revision Alembic can no longer find, breaking every future
upgrade/downgrade against it.

What actually happened: this migration originally created a composite
index (server_id, captured_at) on plugin_console_lines, believing (from
models/plugin_console_line.py's index=False declaration) that no such
index existed. That was wrong — 035_plugin_console_lines.py (the
migration that creates this table) already creates
"ix_plugin_console_lines_server_id_ts" on (server_id, captured_at DESC)
at table-creation time. The model's declaration was simply inaccurate,
not the database. This migration's original upgrade() was therefore
creating a second, redundant, differently-named, opposite-sort-direction
index on every fresh migration run — and it already did so once, for
real, in production, before the mistake was caught.

Neutered to a no-op here so any FUTURE fresh database stops creating the
redundant index (nothing to fix on a fresh install — it never ran the
original buggy version). Production, which already has the redundant
index from actually running the buggy version, is cleaned up by
054_drop_redundant_console_lines_index.py instead — a migration
downstream of this one always runs during any upgrade path, including on
databases that already applied this exact revision id.

Revision ID: 052_add_plugin_console_lines_index
Revises:     051_add_mc_commands_server_id
Create Date: 2026-08-31
"""
revision = "052_add_plugin_console_lines_index"
down_revision = "051_add_mc_commands_server_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op — see module docstring. The real index has existed since 035;
    # cleanup of the redundant index this migration mistakenly created in
    # production lives in 053, not here (053 runs regardless of whether a
    # given database hit the bug or not, since it's a downstream revision).
    pass


def downgrade() -> None:
    # No-op to match upgrade().
    pass
