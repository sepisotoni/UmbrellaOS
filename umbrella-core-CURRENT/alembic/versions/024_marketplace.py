"""marketplace plugin listings, versions, and installs (Phase 7 item 3)

Revision ID: 024_marketplace
Revises: 023_webhook_subscriptions
Create Date: 2026-08-09
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "024_marketplace"
down_revision = "023_webhook_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plugin_listings",
        sa.Column("plugin_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("author", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("latest_version", sa.String(length=64), nullable=False),
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

    op.create_table(
        "plugin_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "plugin_id",
            sa.String(length=64),
            sa.ForeignKey("plugin_listings.plugin_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("zip_path", sa.String(length=512), nullable=False),
        sa.Column(
            "published_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("plugin_id", "version", name="uq_plugin_versions_plugin_id_version"),
    )
    op.create_index("ix_plugin_versions_plugin_id", "plugin_versions", ["plugin_id"])

    op.create_table(
        "plugin_installs",
        sa.Column(
            "plugin_id",
            sa.String(length=64),
            sa.ForeignKey("plugin_listings.plugin_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("installed_version", sa.String(length=64), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("zip_path", sa.String(length=512), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("registered_capability_names", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "installed_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "installed_at",
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


def downgrade() -> None:
    op.drop_table("plugin_installs")
    op.drop_index("ix_plugin_versions_plugin_id", table_name="plugin_versions")
    op.drop_table("plugin_versions")
    op.drop_table("plugin_listings")
