"""add_mc_commands_server_id

[PLUGIN] subsystem audit: mc_commands had no server routing at all, so in
a real multi-server fleet every plugin instance polled the same global
pending-commands queue and executed every command regardless of which
server it targeted. See models/mc_commands.py's column docstring for the
full rationale.

Revision ID: 051_add_mc_commands_server_id
Revises:     050_add_mfa_recovery_codes
Create Date: 2026-08-31
"""
import sqlalchemy as sa
from alembic import op

revision = "051_add_mc_commands_server_id"
down_revision = "050_add_mfa_recovery_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("""
            DO $$
            BEGIN
                ALTER TABLE mc_commands ADD COLUMN server_id VARCHAR(64) NOT NULL DEFAULT 'default';
            EXCEPTION
                WHEN duplicate_column THEN NULL;
            END $$;
        """))
        op.execute(sa.text("""
            DO $$
            BEGIN
                CREATE INDEX ix_mc_commands_server_id ON mc_commands (server_id);
            EXCEPTION
                WHEN duplicate_table THEN NULL;
            END $$;
        """))
    else:
        # SQLite (tests): create_all()-bootstrapped databases already have
        # this from the model directly; only runs for a genuine
        # migration-based SQLite database.
        try:
            op.add_column(
                "mc_commands",
                sa.Column("server_id", sa.String(64), nullable=False, server_default="default"),
            )
            op.create_index("ix_mc_commands_server_id", "mc_commands", ["server_id"])
        except Exception:
            pass


def downgrade() -> None:
    op.drop_index("ix_mc_commands_server_id", table_name="mc_commands")
    op.drop_column("mc_commands", "server_id")
