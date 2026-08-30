"""Add FK from anticheat_violations.player_uuid to players.uuid.

AUDIT-2026-08-29 finding: anticheat_violations.player_uuid had no foreign
key constraint at all — just an indexed plain string column — despite
services/anticheat_service.py always creating the Player row first
(auto-upsert) before writing a violation, so a real FK is safe going
forward. ondelete="CASCADE" matches the established pattern for other
non-nullable player-owned child tables (see models/player.py).

Added as NOT VALID: this table may already have rows from before this fix
(or from a period where Player auto-creation had a bug), and validating
the constraint against 100% of existing data isn't necessary for the fix
to do its job — the important thing is that every new row is enforced
from this point forward. NOT VALID does exactly that (Postgres skips
checking pre-existing rows but enforces the constraint on all new writes
and updates) without the migration risking failure/rollback on unrelated
legacy data quality. A follow-up `VALIDATE CONSTRAINT` can run separately
once/if any orphaned rows are cleaned up.

Revision ID: 046_add_anticheat_violation_player_fk
Revises: 042_add_reduced_appeal_status
Create Date: 2026-08-29
"""
from alembic import op

revision = "046_add_anticheat_violation_player_fk"
down_revision = "042_add_reduced_appeal_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE anticheat_violations "
        "ADD CONSTRAINT fk_anticheat_violations_player_uuid "
        "FOREIGN KEY (player_uuid) REFERENCES players(uuid) ON DELETE CASCADE "
        "NOT VALID"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE anticheat_violations "
        "DROP CONSTRAINT fk_anticheat_violations_player_uuid"
    )
