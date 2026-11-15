"""Persist expiring Core-to-bot events for callback and polling delivery.

Revision ID: 058_bot_delivery_outbox
Revises:     057_supabase_auth_claims
"""

from alembic import op
import sqlalchemy as sa

revision = "058_bot_delivery_outbox"
down_revision = "057_supabase_auth_claims"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_pending_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bot_pending_events_expires_at",
        "bot_pending_events",
        ["expires_at"],
    )
    op.create_index(
        "ix_bot_pending_events_pending",
        "bot_pending_events",
        ["acknowledged_at", "locked_until", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_bot_pending_events_pending", table_name="bot_pending_events")
    op.drop_index("ix_bot_pending_events_expires_at", table_name="bot_pending_events")
    op.drop_table("bot_pending_events")
