"""add_users_sessions_discord_oauth — create the three tables that exist in
models but have never had an Alembic migration.

Critical finding #2 from CRITICAL-FINDINGS-2026-08-17.md: users, sessions,
and discord_oauth_pending are live SQLAlchemy models that create_tables()
(used by every test and every dev startup) built directly from Base.metadata,
but `alembic upgrade head` on a clean database never created them because no
migration existed. This migration fills that gap.

Key relationships:
  users.role_id → roles.id (FK, SET NULL on delete)
  sessions.user_id → users.id (FK, CASCADE on delete)
  api_keys.user_id → users.id (FK, CASCADE on delete) — created by 013,
    but users didn't exist yet in the migration chain; 013 could only have
    worked because create_all() pre-built the table before alembic ran.

Revision ID: 040_add_users_sessions_discord_oauth
Revises:     039_fix_check_constraints
Create Date: 2026-08-26
"""
import sqlalchemy as sa
from alembic import op

revision = "040_add_users_sessions_discord_oauth"
down_revision = "039_fix_check_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("discord_id", sa.String(32), nullable=False, unique=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("email", sa.String(128), nullable=True),
        sa.Column(
            "role_id",
            sa.String(36),
            sa.ForeignKey("roles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("discord_avatar_hash", sa.String(32), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("extra_permissions", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("mfa_secret", sa.String(64), nullable=True),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_discord_id", "users", ["discord_id"], unique=True)

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
    op.create_index(
        "ix_discord_oauth_pending_state", "discord_oauth_pending", ["state"], unique=True
    )

    # 013_identity_phase3 created api_keys with FK api_keys.user_id → users.id,
    # but users didn't exist in the migration chain until now. On a fresh DB
    # (alembic upgrade head) that FK would fail at 013 time. Since we can't
    # retroactively change 013, we add the FK constraint here now that the
    # table exists. On databases already bootstrapped via create_all() this
    # constraint already exists and this will be a no-op (add_constraint with
    # IF NOT EXISTS isn't standard SQL, so we use a try/except in the migration).
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
        # Already exists (create_all() path) — safe to ignore.
        pass


def downgrade() -> None:
    try:
        op.drop_constraint("fk_api_keys_user_id", "api_keys", type_="foreignkey")
    except Exception:
        pass
    op.drop_table("discord_oauth_pending")
    op.drop_table("sessions")
    op.drop_table("users")
