"""plugin_kv_entries — generic key-value storage scoped per plugin
(Phase 10 step 7 Tier 2, Decision 2 Option A). Backs manifest.storage's
"kv" mode, referenced since Phase 7/8 but never actually built until now
— see models/plugin_kv.py's module docstring.

Revision ID: 027_plugin_kv_entries
Revises: 026_dashboard_layouts
Create Date: 2026-08-12
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "027_plugin_kv_entries"
down_revision = "026_dashboard_layouts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plugin_kv_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("plugin_id", sa.String(length=128), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False),
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
        sa.UniqueConstraint("plugin_id", "key", name="uq_plugin_kv_entries_plugin_key"),
    )
    op.create_index("ix_plugin_kv_entries_plugin_id", "plugin_kv_entries", ["plugin_id"])


def downgrade() -> None:
    op.drop_index("ix_plugin_kv_entries_plugin_id", table_name="plugin_kv_entries")
    op.drop_table("plugin_kv_entries")
