"""add_anticheat_violations_table — dedicated GrimAC flag storage.

Replaces the previous approach of shoehorning anticheat flag records into
AITask rows with task_type='anticheat_review'.  The new table gives each
flag its own typed columns, making server_id filtering, per-check
aggregation, and VL-timeline queries work without regex parsing of
ai_summary strings.

Existing AITask rows with task_type='anticheat_review' are left in place —
they continue to appear in the anticheat_service's punishment/tempban logic
output and are still valid audit history.  New flags written after this
migration will go to anticheat_violations exclusively (see Task 3).

server_id is nullable so old plugin versions (that don't send the field)
continue to work — their records just get NULL there.

downgrade() drops the table entirely.  No foreign keys point into it, so
there are no cascades to worry about.

Revision ID: 030_add_anticheat_violations_table
Revises: 029_feature_flags
Create Date: 2026-08-22
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "030_add_anticheat_violations_table"
down_revision = "029_feature_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anticheat_violations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("player_uuid", sa.String(length=36), nullable=False),
        sa.Column("player_name", sa.String(length=64), nullable=False),
        # nullable — old plugin versions don't send server_id
        sa.Column("server_id", sa.String(length=128), nullable=True),
        sa.Column("check_name", sa.String(length=128), nullable=False),
        sa.Column("verbose", sa.Text(), nullable=False, server_default=""),
        sa.Column("vl", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Indexes matching the model's index=True annotations
    op.create_index("ix_anticheat_violations_player_uuid", "anticheat_violations", ["player_uuid"])
    op.create_index("ix_anticheat_violations_server_id", "anticheat_violations", ["server_id"])
    op.create_index("ix_anticheat_violations_check_name", "anticheat_violations", ["check_name"])
    op.create_index("ix_anticheat_violations_timestamp", "anticheat_violations", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_anticheat_violations_timestamp", table_name="anticheat_violations")
    op.drop_index("ix_anticheat_violations_check_name", table_name="anticheat_violations")
    op.drop_index("ix_anticheat_violations_server_id", table_name="anticheat_violations")
    op.drop_index("ix_anticheat_violations_player_uuid", table_name="anticheat_violations")
    op.drop_table("anticheat_violations")
