"""log aggregation and security events (Phase 9, items 3 & 4)

Revision ID: 025_observability_security
Revises: 024_marketplace
Create Date: 2026-08-09
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "025_observability_security"
down_revision = "024_marketplace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "log_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("logger_name", sa.String(length=256), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="umbrella-core"),
        sa.Column("trace_id", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_log_entries_created_at", "log_entries", ["created_at"])
    op.create_index("ix_log_entries_level", "log_entries", ["level"])
    op.create_index("ix_log_entries_logger_name", "log_entries", ["logger_name"])
    op.create_index("ix_log_entries_source", "log_entries", ["source"])
    op.create_index("ix_log_entries_trace_id", "log_entries", ["trace_id"])

    op.create_table(
        "security_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("source_ip", sa.String(length=64), nullable=True),
        sa.Column("identifier", sa.String(length=256), nullable=True),
        sa.Column("detail", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_security_events_created_at", "security_events", ["created_at"])
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_source_ip", "security_events", ["source_ip"])


def downgrade() -> None:
    op.drop_index("ix_security_events_source_ip", table_name="security_events")
    op.drop_index("ix_security_events_event_type", table_name="security_events")
    op.drop_index("ix_security_events_created_at", table_name="security_events")
    op.drop_table("security_events")

    op.drop_index("ix_log_entries_trace_id", table_name="log_entries")
    op.drop_index("ix_log_entries_source", table_name="log_entries")
    op.drop_index("ix_log_entries_logger_name", table_name="log_entries")
    op.drop_index("ix_log_entries_level", table_name="log_entries")
    op.drop_index("ix_log_entries_created_at", table_name="log_entries")
    op.drop_table("log_entries")
