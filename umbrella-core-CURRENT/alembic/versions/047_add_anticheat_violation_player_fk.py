"""Add FK from anticheat_violations.player_uuid to players.uuid.

AUDIT-2026-08-29 finding: anticheat_violations.player_uuid had no foreign
key constraint at all — just an indexed plain string column. The model
(models/anticheat_violation.py) was fixed by another concurrent pass to
declare the FK as nullable with ondelete="SET NULL" (preserves violation
history even if the player row is later removed, rather than cascading
the delete) — but no migration existed yet to actually apply that to the
live schema, so the model and the real DB had silently diverged.

This migration: (1) drops the existing NOT NULL constraint on
player_uuid to match the model's `nullable=True`, then (2) adds the FK
as NOT VALID.

NOT VALID: this table may already have rows from before this fix (or
from any period where Player auto-creation had a bug), and validating
the constraint against 100% of existing data isn't necessary for the fix
to do its job — the important thing is that the constraint is enforced
on all new writes/updates from this point forward. NOT VALID does
exactly that (Postgres skips checking pre-existing rows) without risking
this migration failing/rolling back over unrelated legacy data quality.
A follow-up `VALIDATE CONSTRAINT` can run separately once/if any
orphaned rows are cleaned up.

Revision ID: 047_add_anticheat_violation_player_fk
Revises: 046_deprecate_ai_model_setting
Create Date: 2026-08-29
"""
from alembic import op

revision = "047_add_anticheat_violation_player_fk"
down_revision = "046_deprecate_ai_model_setting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE anticheat_violations ALTER COLUMN player_uuid DROP NOT NULL"
    )
    op.execute(
        "ALTER TABLE anticheat_violations "
        "ADD CONSTRAINT fk_anticheat_violations_player_uuid "
        "FOREIGN KEY (player_uuid) REFERENCES players(uuid) ON DELETE SET NULL "
        "NOT VALID"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE anticheat_violations "
        "DROP CONSTRAINT fk_anticheat_violations_player_uuid"
    )
    op.execute(
        "ALTER TABLE anticheat_violations ALTER COLUMN player_uuid SET NOT NULL"
    )
