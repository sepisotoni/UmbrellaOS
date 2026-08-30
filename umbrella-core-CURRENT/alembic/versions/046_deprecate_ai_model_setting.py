"""Mark the ai.model setting as deprecated in live database rows.

DEFAULT_SETTINGS in settings_service.py was updated (2026-08-28 audit) to
describe this key as "[DEPRECATED] Legacy model string — no effect" but that
only affects rows seeded on fresh databases. Existing live databases already
have the old description "AI model string" in the settings table.

This migration updates the description column of the existing row in-place so
operators on live deployments see the deprecation notice immediately rather
than on their next fresh-deploy.

Safe to run on a DB that has already seeded the row (UPDATE WHERE key=...),
and a no-op if the row does not exist (UPDATE affects 0 rows — not an error).

Revision ID: 046_deprecate_ai_model_setting
Revises: 045_merge_042_branches
Create Date: 2026-08-29
"""
from alembic import op
import sqlalchemy as sa

revision = "046_deprecate_ai_model_setting"
down_revision = "045_merge_042_branches"
branch_labels = None
depends_on = None

_NEW_DESC = "[DEPRECATED] Legacy model string — no effect. Model selection uses the AI Models table (ai_model_configs)."
_OLD_DESC_PATTERNS = ("AI model string", "Legacy model string")  # for downgrade match


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE settings SET description = :desc WHERE key = 'ai.model'"
        ).bindparams(desc=_NEW_DESC)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE settings SET description = 'AI model string' WHERE key = 'ai.model'"
        )
    )
