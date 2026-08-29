"""add_reduced_appeal_status — add 'reduced' to ck_appeals_status.

AUDIT-PLAYERS-MODERATION-2026-08-29 finding: close_appeal's REDUCE_SENTENCE
action sets appeal.status to a "reduced" state, but ck_appeals_status
(migration 039) never included it — only 'open', 'accepted', 'denied',
'pending', 'rejected', 'escalated', 'review_scheduled'. Every
REDUCE_SENTENCE close_appeal call raised a CheckViolationError at commit.

This migration also does NOT change case-sensitivity: the constraint has
always been lowercase-only. close_appeal was writing uppercase status
strings ("ACCEPTED", "REJECTED", etc.) for every action, which never
matched the lowercase constraint either — that's fixed in the router
code (api/routers/appeals.py), not here. This migration only adds the
missing 'reduced' value.

Revision ID: 042_add_reduced_appeal_status
Revises:     041_fix_ipban_player_uuid_and_punishment_nullable
Create Date: 2026-08-29
"""
from alembic import op

revision = "042_add_reduced_appeal_status"
down_revision = "041_fix_ipban_player_uuid_and_punishment_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_appeals_status", "appeals", type_="check")
    op.create_check_constraint(
        "ck_appeals_status",
        "appeals",
        "status IN ('open', 'accepted', 'denied', 'pending', 'rejected', "
        "'escalated', 'review_scheduled', 'reduced')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_appeals_status", "appeals", type_="check")
    op.create_check_constraint(
        "ck_appeals_status",
        "appeals",
        "status IN ('open', 'accepted', 'denied', 'pending', 'rejected', "
        "'escalated', 'review_scheduled')",
    )
