"""Fix ai_model_configs rows still pointing at the retired gemini-1.5-flash.

Google retired Gemini 1.0 and 1.5 models before 2026-08-31 — every request
to gemini-1.5-flash returns 404 from Google's own API. Migration 042 seeded
this exact model string as the primary/failover model for copilot,
player_review, appeal_review, and crash_risk, meaning the AI subsystem
shipped already pointed at a dead model. This surfaced live as:

    "AI orchestrator unavailable: no available model for task_type
    'copilot' (tried: gemini/gemini-1.5-flash)"

with the ModelRouter correctly recording the provider failure (Google's API
error) but having no working fallback configured in most environments.

This migration updates any existing row still set to gemini-1.5-flash to
gemini-2.5-flash — the current, non-retired equivalent. The seed migration
itself (042) has also been corrected for anyone running the chain fresh
from now on, but that fix has no effect on databases that already ran 042
before this correction (ON CONFLICT DO NOTHING means a rerun is a no-op) —
this migration is what actually fixes those already-seeded rows.

Revision ID: 049_fix_retired_gemini_model
Revises: 048_widen_alembic_version
Create Date: 2026-08-31
"""
from alembic import op
import sqlalchemy as sa

revision = "049_fix_retired_gemini_model"
down_revision = "048_widen_alembic_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text(
        "UPDATE ai_model_configs SET model_name = 'gemini-2.5-flash', "
        "is_healthy = true, consecutive_failures = 0 "
        "WHERE provider = 'gemini' AND model_name = 'gemini-1.5-flash'"
    ))


def downgrade() -> None:
    op.execute(sa.text(
        "UPDATE ai_model_configs SET model_name = 'gemini-1.5-flash' "
        "WHERE provider = 'gemini' AND model_name = 'gemini-2.5-flash'"
    ))
