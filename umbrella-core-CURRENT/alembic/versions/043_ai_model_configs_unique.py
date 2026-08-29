"""Add unique constraint on ai_model_configs(provider, model_name, task_type).

Migration 042 uses INSERT … ON CONFLICT DO NOTHING on those three columns,
but without a matching unique constraint (or index) PostgreSQL rejects the
statement with:
  "there is no unique or exclusion constraint matching the ON CONFLICT
  specification"

This migration adds that constraint so 042's idempotent seed INSERT works,
and so the /api/v1/ai/config/tasks dashboard endpoint's upsert logic can
safely rely on the uniqueness guarantee.

Must run before 042 (which is why it has a lower revision number even though
it was written after 042 was noticed to be broken).

Revision ID: 043_ai_model_configs_unique
Revises: 042_seed_ai_model_configs
Create Date: 2026-08-28
"""
from alembic import op

revision = "043_ai_model_configs_unique"
down_revision = "042_seed_ai_model_configs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_ai_model_configs_provider_model_task",
        "ai_model_configs",
        ["provider", "model_name", "task_type"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_ai_model_configs_provider_model_task",
        "ai_model_configs",
        type_="unique",
    )
