"""fix_check_constraints — correct ck_punishments_type and ck_appeals_status
to match what the application actually writes.

Bug #9: POST /api/v1/appeals created rows with status='pending', but
  ck_appeals_status only permitted ('open','accepted','denied'). Every appeal
  creation failed with a CheckViolationError. Fixed in the router by using
  'open' as the initial status. This migration widens the constraint to also
  permit 'pending' and 'rejected' for older rows and for the PATCH endpoint
  which can write arbitrary status strings (those are further validated by
  the close_appeal workflow).

Bug #10: POST /api/v1/moderation/kick wrote type='kick' and
  POST /api/v1/moderation/ipunban wrote type='ipban', but
  ck_punishments_type only permitted ('warn','mute','tempban','ban'). Both
  endpoints always failed. This migration adds 'kick' and 'ipban' to the
  allowed set and also adds 'kick' to the status constraint since a kick is
  also treated as a punishment record with active=False.

Approach: Postgres CHECK constraints can't be altered in place — we drop
  and recreate. This is a DDL-only migration with no data changes.

Revision ID: 039_fix_check_constraints
Revises:     038_bot_guild_roles
Create Date: 2026-08-26
"""
from alembic import op

revision = "039_fix_check_constraints"
down_revision = "038_bot_guild_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- punishments table ---
    # Old constraint: type IN ('warn', 'mute', 'tempban', 'ban')
    # New constraint: adds 'kick' and 'ipban'
    op.drop_constraint("ck_punishments_type", "punishments", type_="check")
    op.create_check_constraint(
        "ck_punishments_type",
        "punishments",
        "type IN ('warn', 'mute', 'tempban', 'ban', 'kick', 'ipban')",
    )

    # --- appeals table ---
    # Old constraint: status IN ('open', 'accepted', 'denied')
    # New constraint: adds 'pending', 'rejected', 'escalated', 'review_scheduled'
    # to match what close_appeal endpoint writes and any future status flows.
    op.drop_constraint("ck_appeals_status", "appeals", type_="check")
    op.create_check_constraint(
        "ck_appeals_status",
        "appeals",
        "status IN ('open', 'accepted', 'denied', 'pending', 'rejected', 'escalated', 'review_scheduled')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_appeals_status", "appeals", type_="check")
    op.create_check_constraint(
        "ck_appeals_status",
        "appeals",
        "status IN ('open', 'accepted', 'denied')",
    )

    op.drop_constraint("ck_punishments_type", "punishments", type_="check")
    op.create_check_constraint(
        "ck_punishments_type",
        "punishments",
        "type IN ('warn', 'mute', 'tempban', 'ban')",
    )
