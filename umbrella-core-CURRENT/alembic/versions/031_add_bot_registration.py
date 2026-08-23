"""add_bot_registration — single-row table for bot webhook callback URL.

Core reads this on push events (Phase 16B Task B) to know where to POST
staff.escalation.new and other push events. Upserted on bot startup via
POST /api/v1/bot/register; always id=1 so only one registration exists.

Revision ID: 031_add_bot_registration
Revises:     030_appeal_close_fields
Create Date: 2026-08-23
"""
import sqlalchemy as sa
from alembic import op

revision = "031_add_bot_registration"
down_revision = "030_appeal_close_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_registration",
        sa.Column("id", sa.Integer(), nullable=False, default=1),
        sa.Column("callback_url", sa.Text(), nullable=False),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("bot_registration")
