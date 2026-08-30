"""Widen alembic_version.version_num — VARCHAR(32) is too narrow.

Reproduced concretely against a real, fresh Postgres 16 (not the SQLite
test harness, which never touches this table since tests build schema
via Base.metadata.create_all() and skip the migration chain entirely):

Several revision ids in this chain exceed 32 characters — e.g.
033_add_anticheat_violations_table (34 chars),
041_fix_ipban_player_uuid_and_punishment_nullable (49 chars). Alembic's
own auto-created `alembic_version.version_num` column defaults to
VARCHAR(32). When a migration's own revision id doesn't fit, the final
`UPDATE alembic_version SET version_num=...` step raises
StringDataRightTruncationError — and because this runs inside the same
transactional-DDL block as the migration's actual schema changes, the
failure rolls back everything, including changes that had already
succeeded (confirmed: 033's own `CREATE TABLE anticheat_violations`
executes cleanly, then vanishes on rollback when the version-stamp UPDATE
fails immediately after).

This was flagged by [HEAD]/[AI] via CHAT-COORDINATION.md as a real,
confirmed, cross-cutting blocker affecting the whole migration chain (not
specific to any one subsystem), still unclaimed at the time of this
migration. Fixing it here because it's what's directly blocking
047_add_anticheat_violation_player_fk (this chat's own migration) from
ever successfully executing against a real database — every fresh-DB
attempt to reach 047 dies at 033 first, for this reason, before 047 even
gets a chance to run.

VARCHAR(255) matches the ad-hoc width [AI] used locally to unblock their
own testing (see their CHAT-COORDINATION.md notice) — reusing the same
value rather than picking a new one arbitrarily.

This migration's own revision id is kept short and simple on purpose:
even though the widening happens inside the same transaction as this
migration's own version-stamp (so Postgres would see the already-widened
column either way), there's no reason to test that edge case when a
short id costs nothing.

Revision ID: 048_widen_alembic_version
Revises: 047_add_anticheat_violation_player_fk
Create Date: 2026-08-30
"""
from alembic import op

revision = "048_widen_alembic_version"
down_revision = "047_add_anticheat_violation_player_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)")


def downgrade() -> None:
    # Not reversed to VARCHAR(32): several already-applied revision ids in
    # this chain (033, 041, this one's own successors) exceed 32 chars, so
    # narrowing back would immediately break on the very next
    # `alembic downgrade`/`upgrade` version-stamp write. A no-op downgrade
    # is the only safe option once this has been applied.
    pass
