"""add_users_sessions_discord_oauth — create sessions and discord_oauth_pending,
and ensure users exists (created in 013 but documented here for completeness).

Critical finding #2 from CRITICAL-FINDINGS-2026-08-17.md: users, sessions,
and discord_oauth_pending are live SQLAlchemy models that create_tables()
(used by every test and every dev startup) built directly from Base.metadata,
but alembic upgrade head on a clean database never created sessions or
discord_oauth_pending because no migration existed for them. This migration
fills that gap.

users: created in 013_identity_phase3 (the earliest migration that
  references it). Created here too with IF NOT EXISTS as a safety net.

sessions: FK to users.id. Created here unconditionally.
discord_oauth_pending: no FK dependencies. Created here unconditionally.

Revision ID: 040_add_users_sessions_discord_oauth
Revises:     039_fix_check_constraints
Create Date: 2026-08-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "040_add_users_sessions_discord_oauth"
down_revision = "039_fix_check_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users: created in 013 — IF NOT EXISTS in case any path bypassed 013
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(36) PRIMARY KEY,
            discord_id VARCHAR(32) NOT NULL UNIQUE,
            username VARCHAR(64) NOT NULL,
            email VARCHAR(128),
            role_id VARCHAR(36) REFERENCES roles(id) ON DELETE SET NULL,
            discord_avatar_hash VARCHAR(32),
            is_active BOOLEAN NOT NULL DEFAULT true,
            extra_permissions JSON NOT NULL DEFAULT '[]',
            mfa_secret VARCHAR(64),
            mfa_enabled BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_discord_id ON users (discord_id)"
    ))

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(256), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_token", "sessions", ["token"], unique=True)

    op.create_table(
        "discord_oauth_pending",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("state", sa.String(128), nullable=False, unique=True),
        sa.Column("code_verifier", sa.String(256), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_discord_oauth_pending_state "
        "ON discord_oauth_pending (state)"
    ))

    # Retrofit api_keys.created_by FK now that users is guaranteed to exist.
    #
    # FIX: this previously referenced "api_keys.user_id" — a column that has
    # never existed. models/api_key.py's ApiKey ORM model has always declared
    # the column as `created_by` (String(36), ForeignKey("users.id",
    # ondelete="SET NULL"), nullable=True) — never user_id, and never CASCADE.
    # On a real migration-based Postgres deployment, create_foreign_key with
    # the wrong column name raised UndefinedColumn every single time; the
    # bare `except Exception: pass` silently swallowed that, so this FK was
    # NEVER actually created via migrations, on any database, ever — not just
    # on "already exists" reruns as the comment claimed. It only ever existed
    # on databases bootstrapped via create_all() (tests, local dev), because
    # that path reads the correct column name directly from the model and
    # bypasses this migration entirely — which is exactly why nothing caught
    # this until a real `alembic upgrade head` run against fresh Postgres did.
    #
    # Also corrected ondelete from CASCADE to SET NULL to match the model:
    # deleting a user should not delete every API key they ever created —
    # api_key.creator becoming NULL (an "orphaned" key, still functional) is
    # the intended behaviour, same as knowledge_entries and other created_by
    # columns elsewhere in this schema.
    #
    # Uses the same duplicate_object-catching DO block as 043's fix (verified
    # against real Postgres 16 there) rather than a bare Python except, so a
    # genuine second failure mode isn't silently masked alongside the
    # "already exists" case this is meant to tolerate.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(text("""
            DO $$
            BEGIN
                ALTER TABLE api_keys
                ADD CONSTRAINT fk_api_keys_created_by
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
        """))
    else:
        # SQLite (tests): create_all() already applies the model's inline FK;
        # SQLite also can't ALTER TABLE ADD CONSTRAINT at all, so there is
        # nothing to retrofit here on that dialect.
        pass


def downgrade() -> None:
    try:
        op.drop_constraint("fk_api_keys_created_by", "api_keys", type_="foreignkey")
    except Exception:
        pass
    op.drop_table("discord_oauth_pending")
    op.drop_table("sessions")
    # Do not drop users — it's owned by 013 which creates it first
