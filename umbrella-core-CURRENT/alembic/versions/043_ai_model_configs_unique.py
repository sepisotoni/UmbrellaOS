"""Add unique constraint on ai_model_configs(provider, model_name, task_type).

Migration 042 uses INSERT … ON CONFLICT DO NOTHING on those three columns,
but without a matching unique constraint (or index) PostgreSQL rejects the
statement with:
  "there is no unique or exclusion constraint matching the ON CONFLICT
  specification"

This migration adds that constraint so 042's idempotent seed INSERT works,
and so the /api/v1/ai/config/tasks dashboard endpoint's upsert logic can
safely rely on the uniqueness guarantee.

NOTE: migration 042 was later updated to also create this constraint at the
start of its own upgrade(), so on a fresh DB the constraint exists by the
time 043 runs.  This migration uses IF NOT EXISTS so it is safe either way —
042-first path (constraint already exists, 043 is a no-op) and the old
042-without-patch path (constraint doesn't exist yet, 043 creates it).

Revision ID: 043_ai_model_configs_unique
Revises: 042_seed_ai_model_configs
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "043_ai_model_configs_unique"
down_revision = "042_seed_ai_model_configs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # PostgreSQL has no `ADD CONSTRAINT IF NOT EXISTS` syntax — caught by
        # an end-to-end migration run against a real fresh Postgres instance;
        # the original version here was invalid SQL that would fail with
        # "syntax error at or near NOT" (same bug fixed in 042's upgrade()).
        #
        # Catches both duplicate_table (42P07) and duplicate_object (42710) —
        # confirmed directly against real Postgres 16 that ADD CONSTRAINT
        # UNIQUE raises duplicate_table specifically (via its backing unique
        # index), not duplicate_object as general "conditional DDL" examples
        # might suggest. Catching only one left the other uncaught on rerun.
        op.execute(sa.text("""
            DO $$
            BEGIN
                ALTER TABLE ai_model_configs
                ADD CONSTRAINT uq_ai_model_configs_provider_model_task
                UNIQUE (provider, model_name, task_type);
            EXCEPTION
                WHEN duplicate_table THEN NULL;
                WHEN duplicate_object THEN NULL;
            END $$;
        """))
    # SQLite does not support ADD CONSTRAINT and has no need for it
    # (the SQLite path in 042 uses per-row existence checks, not ON CONFLICT).


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text(
            "ALTER TABLE ai_model_configs "
            "DROP CONSTRAINT IF EXISTS uq_ai_model_configs_provider_model_task"
        ))
