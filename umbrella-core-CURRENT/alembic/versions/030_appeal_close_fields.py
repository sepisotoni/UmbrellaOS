"""appeal_close_fields — add close/AI review columns to appeals; add status to punishments.

Adds to the appeals table:
  - action_taken      VARCHAR(32)   nullable — ACCEPT | REDUCE_SENTENCE | REJECT | ESCALATE | SCHEDULE_REVIEW
  - handled_by        VARCHAR(128)  nullable — staff username who closed the appeal
  - case_summary      TEXT          nullable — auto-generated on close
  - closed_at         TIMESTAMPTZ   nullable — when the appeal was closed
  - ai_review_status  VARCHAR(16)   nullable — PENDING | COMPLETED | FAILED
  - ai_review_result  TEXT          nullable — JSON blob of AI output

Adds to the punishments table:
  - status            VARCHAR(32)   not null default 'ACTIVE' — ACTIVE | PARDONED etc.

Revision ID: 030_appeal_close_fields
Revises:     029_feature_flags
Create Date: 2026-08-22
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "030_appeal_close_fields"
down_revision = "029_feature_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- appeals table: new close + AI review fields --
    op.add_column(
        "appeals",
        sa.Column("action_taken", sa.String(32), nullable=True),
    )
    op.add_column(
        "appeals",
        sa.Column("handled_by", sa.String(128), nullable=True),
    )
    op.add_column(
        "appeals",
        sa.Column("case_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "appeals",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "appeals",
        sa.Column("ai_review_status", sa.String(16), nullable=True),
    )
    op.add_column(
        "appeals",
        sa.Column("ai_review_result", sa.Text(), nullable=True),
    )

    # -- punishments table: add explicit status column --
    op.add_column(
        "punishments",
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="ACTIVE",
        ),
    )


def downgrade() -> None:
    # -- punishments --
    op.drop_column("punishments", "status")

    # -- appeals --
    op.drop_column("appeals", "ai_review_result")
    op.drop_column("appeals", "ai_review_status")
    op.drop_column("appeals", "closed_at")
    op.drop_column("appeals", "case_summary")
    op.drop_column("appeals", "handled_by")
    op.drop_column("appeals", "action_taken")
