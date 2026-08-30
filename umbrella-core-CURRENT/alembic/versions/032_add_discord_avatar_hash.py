"""add_discord_avatar_hash

Revision ID: 032_add_discord_avatar_hash
Revises:     031_add_bot_registration
Create Date: 2026-08-24

AUDIT-2026-08-30 fix (same class of bug [AI] found in 011, flagged
independently while chasing the migration-chain blockers [HEAD] listed):
this migration is a duplicate. 013_identity_phase3.py's
`CREATE TABLE IF NOT EXISTS users (...)` already includes
`discord_avatar_hash VARCHAR(32)` in its column list, and 013 (down_revision
012_hosting_domain) runs well before 032 (down_revision
031_add_bot_registration) in this linear chain. A genuine `alembic upgrade
head` from an empty database hits 013 first, creating the column, then
errors here with DuplicateColumn trying to add it again.

Converted to a no-op rather than deleted: 033_add_anticheat_violations_table.py's
down_revision points at this revision id, and any already-deployed database
that recorded reaching "032_add_discord_avatar_hash" needs this revision id
to keep existing in the chain. Only the upgrade()/downgrade() bodies are
neutered — same approach as 011_add_suspicion_score.py's fix for the
identical bug pattern.
"""
import sqlalchemy as sa
from alembic import op

revision = "032_add_discord_avatar_hash"
down_revision = "031_add_bot_registration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op — see module docstring. Column already added by
    # 013_identity_phase3.py's CREATE TABLE IF NOT EXISTS earlier in this
    # same chain.
    pass


def downgrade() -> None:
    # No-op to match upgrade(). The real column, if ever dropped, is
    # 013_identity_phase3.py's responsibility, since that's the migration
    # that actually owns adding it.
    pass
