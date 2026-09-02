"""Seed discord.admin_role_id, discord.moderator_role_id, discord.helper_role_id.

The dashboard's Discord Hub role-mapping table (DiscordView.tsx) defines 5
roles (owner, admin, moderator, helper, member) in both clearanceMap and
roleColor, but roleDiscordId() only had lookup branches for owner and
member — admin/moderator/helper always showed "Not mapped" in the UI
regardless of what was configured, because these three settings keys never
existed anywhere in the codebase before this fix (confirmed via full-repo
grep: zero references in either umbrella-core or umbrella-dashboard).

This adds the three missing keys with empty defaults on existing databases.
New databases pick them up automatically via settings_service.py's
DEFAULT_SETTINGS (already updated in the same commit as this migration) —
this migration exists only to backfill databases that seeded before that
change.

Revision ID: 053_add_discord_role_id_settings
Revises: 052_add_plugin_console_lines_index
Create Date: 2026-09-01
"""
import uuid
from alembic import op
import sqlalchemy as sa

revision = "053_add_discord_role_id_settings"
down_revision = "052_add_plugin_console_lines_index"
branch_labels = None
depends_on = None

_NEW_KEYS = [
    ("discord.admin_role_id", "Discord role ID for the Admin role; maps to dashboard clearance ADMIN"),
    ("discord.moderator_role_id", "Discord role ID for the Moderator role; maps to dashboard clearance MODERATOR"),
    ("discord.helper_role_id", "Discord role ID for the Helper role; maps to dashboard clearance SUPPORT"),
]


def upgrade() -> None:
    bind = op.get_bind()
    for key, description in _NEW_KEYS:
        existing = bind.execute(
            sa.text("SELECT 1 FROM settings WHERE key = :key LIMIT 1"),
            {"key": key},
        ).fetchone()
        if not existing:
            # Setting.id has no server-side default (Setting.id's
            # default=lambda: str(uuid.uuid4()) in models/setting.py is
            # evaluated by the SQLAlchemy ORM, not by the database) — a raw
            # SQL INSERT omitting id would fail with a NOT NULL violation.
            # Generate it explicitly here, matching what the ORM would do.
            op.execute(
                sa.text(
                    "INSERT INTO settings (id, key, value, category, description, sensitive, requires_restart) "
                    "VALUES (:id, :key, '', 'discord', :description, false, false)"
                ).bindparams(id=str(uuid.uuid4()), key=key, description=description)
            )


def downgrade() -> None:
    for key, _ in _NEW_KEYS:
        op.execute(
            sa.text("DELETE FROM settings WHERE key = :key").bindparams(key=key)
        )
