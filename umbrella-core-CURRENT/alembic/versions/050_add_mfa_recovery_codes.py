"""add_mfa_recovery_codes

Master bug report finding #5: no MFA recovery path existed. Adds
mfa_recovery_codes_hash (JSON array of SHA-256 hashes, nullable) to users —
see models/user.py's column docstring for the full design rationale.

Revision ID: 050_add_mfa_recovery_codes
Revises:     049_fix_retired_gemini_model
Create Date: 2026-08-31
"""
import sqlalchemy as sa
from alembic import op

revision = "050_add_mfa_recovery_codes"
down_revision = "049_fix_retired_gemini_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("""
            DO $$
            BEGIN
                ALTER TABLE users ADD COLUMN mfa_recovery_codes_hash JSON;
            EXCEPTION
                WHEN duplicate_column THEN NULL;
            END $$;
        """))
    else:
        # SQLite (tests): plain ADD COLUMN, no duplicate-guard syntax needed
        # or available — create_all()-bootstrapped databases already have
        # this from the model directly, so this only runs on a genuine
        # migration-based SQLite database (uncommon, but supported).
        try:
            op.add_column("users", sa.Column("mfa_recovery_codes_hash", sa.JSON(), nullable=True))
        except Exception:
            pass


def downgrade() -> None:
    op.drop_column("users", "mfa_recovery_codes_hash")
