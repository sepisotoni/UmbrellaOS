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

AUDIT-2026-08-30/31 fix ([HEAD] flagged this migration as one of the
migration-chain blockers; [AUTH] traced and fixed it in two passes): the
original upgrade() also tried to retrofit a foreign key on api_keys,
referencing "api_keys.user_id" — a column that has never existed (the
real column is `created_by`, per models/api_key.py). A first pass fixed
the column name, ondelete behavior, and swapped the bare
`except Exception: pass` for a targeted duplicate_object-catching DO
block. Verified against real Postgres 16, that no longer raised — but it
also revealed the retrofit was never actually needed: 013_identity_phase3
already creates api_keys with `created_by`'s FK to users.id inline, at
table-creation time (013 creates users first, then api_keys, in the same
migration — there is no point in this chain where api_keys exists without
users). The "fixed" version was successfully adding a second, redundant,
differently-named FK constraint on the same column every run, since
Postgres doesn't treat two different constraint names as a duplicate_object
collision. The api_keys FK block is now a genuine no-op, same convention
as 011/032's fixes for the analogous "this work was already done earlier
in the chain" bug class.

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

    # No-op — see module docstring for the full history of this block.
    #
    # This retrofit was based on a false premise from the start, on two
    # separate levels:
    #   1. It referenced "api_keys.user_id", a column that has never
    #      existed (the real column, and the model's actual FK, has always
    #      been `created_by` — see models/api_key.py).
    #   2. Even correcting the column name, the retrofit itself was
    #      unnecessary: 013_identity_phase3.py's op.create_table("api_keys",
    #      ...) already declares created_by with its FK to users.id
    #      (ondelete="SET NULL") INLINE, at table-creation time — not
    #      "before users existed" as this migration's original comment
    #      assumed. 013 creates users first, then api_keys with the FK, in
    #      the same migration. There was never a point in this chain where
    #      api_keys existed without users, so there was never anything to
    #      retrofit.
    #
    # Confirmed directly against real Postgres 16: running the corrected
    # version of this block (which fixed the column name to created_by,
    # correct ondelete, and a duplicate_object-catching DO block) did not
    # error, but it silently created a SECOND foreign key constraint on the
    # same column — Postgres allows multiple differently-named FK
    # constraints on one column, so `fk_api_keys_created_by` (this
    # migration) coexisted right alongside `api_keys_created_by_fkey` (the
    # one 013 already created), rather than tripping the duplicate_object
    # guard. Confirmed via pg_constraint that 013's FK already carries
    # identical semantics (same column, same target, same ON DELETE SET
    # NULL) — there is nothing for this migration to add.
    pass


def downgrade() -> None:
    # No-op to match upgrade() — the FK on api_keys.created_by is owned by
    # 013_identity_phase3.py (created inline with the table), not this
    # migration. Nothing here to undo.
    op.drop_table("discord_oauth_pending")
    op.drop_table("sessions")
    # Do not drop users — it's owned by 013 which creates it first
