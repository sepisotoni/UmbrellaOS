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

    # Retrofit api_keys.user_id FK now that users is guaranteed to exist.
    try:
        op.create_foreign_key(
            "fk_api_keys_user_id",
            "api_keys",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
    except Exception:
        pass  # Already exists on create_all()-bootstrapped databases


def downgrade() -> None:
    try:
        op.drop_constraint("fk_api_keys_user_id", "api_keys", type_="foreignkey")
    except Exception:
        pass
    op.drop_table("discord_oauth_pending")
    op.drop_table("sessions")
    # Do not drop users — it's owned by 013 which creates it first
