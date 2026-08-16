"""plugin_execution_records — per-execution timing/resource-usage
telemetry for sandboxed plugin calls (Phase 8 completion, Task A).
Backs models/plugin_execution.py::PluginExecutionRecord — see that
module's docstring for why this is a separate table from anything a
plugin's own capability call returns.

Column list mirrors the ORM model directly (String/Text/Float/Integer/
DateTime), same as every other migration in this chain. `index=True` is
NOT passed to sa.Column here — it's only used by
`Base.metadata.create_all()`'s own indexing convention
(database/engine.py::create_tables, the dev/test path); this migration
declares its indexes with explicit op.create_index calls instead, exactly
once each, deliberately avoiding the duplicate-index bug found and fixed
in migrations 004/005 (see dispatches/PHASE10-COMPLETION/handback/
STEP9-MARKETPLACE-UI-AND-FIRST-TEST-PASS.md, "Three real migration bugs
found and fixed along the way") — declaring index=True on the Column
*and* a separate op.create_index for the same index in one migration
creates it twice.

Revision ID: 028_plugin_execution_records
Revises: 027_plugin_kv_entries
Create Date: 2026-08-16
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "028_plugin_execution_records"
down_revision = "027_plugin_kv_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plugin_execution_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("plugin_id", sa.String(length=128), nullable=False),
        sa.Column("entrypoint", sa.String(length=256), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("wall_time_ms", sa.Float(), nullable=False),
        sa.Column("cpu_time_ms", sa.Float(), nullable=True),
        sa.Column("peak_memory_bytes", sa.Integer(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_plugin_execution_records_plugin_id", "plugin_execution_records", ["plugin_id"]
    )
    op.create_index(
        "ix_plugin_execution_records_outcome", "plugin_execution_records", ["outcome"]
    )
    op.create_index(
        "ix_plugin_execution_records_created_at", "plugin_execution_records", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_plugin_execution_records_created_at", table_name="plugin_execution_records")
    op.drop_index("ix_plugin_execution_records_outcome", table_name="plugin_execution_records")
    op.drop_index("ix_plugin_execution_records_plugin_id", table_name="plugin_execution_records")
    op.drop_table("plugin_execution_records")
