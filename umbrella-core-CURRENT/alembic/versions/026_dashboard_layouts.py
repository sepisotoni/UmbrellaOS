"""dashboard_layouts — per-user custom widget layout (Phase 10 step 6)

Revision ID: 026_dashboard_layouts
Revises: 025_observability_security
Create Date: 2026-08-11
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "026_dashboard_layouts"
down_revision = "025_observability_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_layouts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_id", sa.String(length=64), nullable=False),
        sa.Column("layout_json", sa.Text(), nullable=False, server_default="[]"),
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
        sa.UniqueConstraint("user_id", "page_id", name="uq_dashboard_layouts_user_page"),
    )
    op.create_index("ix_dashboard_layouts_user_id", "dashboard_layouts", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_dashboard_layouts_user_id", table_name="dashboard_layouts")
    op.drop_table("dashboard_layouts")
