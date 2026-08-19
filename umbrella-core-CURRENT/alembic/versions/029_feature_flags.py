"""feature_flags — boolean registry of named runtime feature gates.

Adds the feature_flags table (see models/feature_flag.py) and seeds one
well-known row: anticheat.enabled, which the Phase 13 GrimAC bridge
checks before forwarding reports. Seeded with enabled=true so an upgrade
on an existing cluster doesn't silently drop live anticheat coverage.

downgrade() drops the whole table — no data migration needed since there
are no foreign keys pointing into feature_flags.

Revision ID: 029_feature_flags
Revises: 028_plugin_execution_records
Create Date: 2026-08-19
"""
import uuid
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "029_feature_flags"
down_revision = "028_plugin_execution_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
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
    op.create_index("ix_feature_flags_name", "feature_flags", ["name"], unique=True)

    # Seed the anticheat flag
    op.execute(
        "INSERT INTO feature_flags (id, name, enabled, description, created_at, updated_at) "
        f"VALUES ('{uuid.uuid4()}', 'anticheat.enabled', true, "
        "'Enable GrimAC anticheat bridge reporting', now(), now())"
    )


def downgrade() -> None:
    op.drop_index("ix_feature_flags_name", table_name="feature_flags")
    op.drop_table("feature_flags")
