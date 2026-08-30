"""Add suspicion_score column to players table

Revision ID: 011_add_suspicion_score
Revises: 010_mc_commands_translation
Create Date: 2026-06-18

AUDIT-2026-08-30 fix (flagged by [AI] during a real end-to-end migration
run — Base.metadata.create_all() in the SQLite test harness never
exercises this, since it skips the whole migration history and builds
straight from the current models): this migration is a duplicate.
005_phase9_alt_detection.py already runs
`op.add_column("players", sa.Column("suspicion_score", ...))` earlier in
this exact same linear chain (005 -> ... -> 010 -> this file). Running
the full sequence from scratch hits 005 first, successfully adding the
column, then errors here with DuplicateColumn when this migration tries
to add it again.

Converted to a no-op rather than deleted: 012_hosting_domain.py's
down_revision points at this revision id, and any already-deployed
database that recorded reaching "011_add_suspicion_score" in its
alembic_version table (from a run that got this far before 032's later,
separate duplicate-column break) needs this revision id to keep existing
in the chain. Only the upgrade()/downgrade() bodies are neutered.
"""
from alembic import op
import sqlalchemy as sa


revision = '011_add_suspicion_score'
down_revision = '010_mc_commands_translation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op — see module docstring. Column already added by
    # 005_phase9_alt_detection.py earlier in this same chain.
    pass


def downgrade() -> None:
    # No-op to match upgrade(). The real column-drop, if ever needed, is
    # 005_phase9_alt_detection.py's downgrade() responsibility, since that's
    # the migration that actually owns adding it.
    pass
