"""webhook subscriptions (Phase 7 item 2)

Revision ID: 023_webhook_subscriptions
Revises: 022_events_outbox
Create Date: 2026-08-08
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "023_webhook_subscriptions"
down_revision = "022_events_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("topic", sa.String(length=150), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("secret", sa.String(length=128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_webhook_subscriptions_topic",
        "webhook_subscriptions",
        ["topic"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_subscriptions_topic", table_name="webhook_subscriptions")
    op.drop_table("webhook_subscriptions")
