"""Add api_keys table and MFA columns on users.

Also creates the users table itself if it does not already exist.
The users table was always a live SQLAlchemy model but was never created
by any migration in the 001-012 chain — every prior bootstrap used
create_all() which bypassed Alembic. A fresh 'alembic upgrade head' on a
genuinely empty database would reach this migration and fail on the
op.add_column('users', ...) call because the table didn't exist yet.

Fix: create users here (the earliest migration that touches it), using a
raw DDL 'CREATE TABLE IF NOT EXISTS' so this is safe against both:
  (a) fresh databases (no prior create_all) — creates the table, then adds columns
  (b) existing databases bootstrapped via create_all() — IF NOT EXISTS is a no-op,
      then add_column proceeds normally

Migration 040 creates sessions and discord_oauth_pending (which depend on
users) and also creates users with IF NOT EXISTS as a safety net for any
path that somehow reaches 040 without 013.

Revision ID: 013_identity_phase3
Revises: 012_hosting_domain
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = '013_identity_phase3'
down_revision = '012_hosting_domain'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table if it doesn't exist yet. This is the earliest migration
    # that references users, so we own its creation. IF NOT EXISTS makes this
    # safe on databases already bootstrapped via create_all().
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

    # Now add MFA columns if they don't exist (safe for create_all-bootstrapped DBs)
    conn = op.get_bind()
    existing_cols = {
        row[0] for row in conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
        )
    }
    if 'mfa_secret' not in existing_cols:
        op.add_column('users', sa.Column('mfa_secret', sa.String(64), nullable=True))
    if 'mfa_enabled' not in existing_cols:
        op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'))

    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('key_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('key_prefix', sa.String(16), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.drop_table('api_keys')
    op.drop_column('users', 'mfa_enabled')
    op.drop_column('users', 'mfa_secret')
    # Do not drop users in downgrade — it predates this migration and is
    # owned by migration 040. Dropping here would break 040's downgrade.
