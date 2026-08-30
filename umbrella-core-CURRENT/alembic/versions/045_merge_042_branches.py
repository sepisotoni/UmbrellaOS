"""Merge the two 042 branches into a single head.

Two migrations both declared down_revision = "041_fix_ipban_player_uuid_and_punishment_nullable":
  - 042_add_reduced_appeal_status  (appeals surface, written by another agent)
  - 042_seed_ai_model_configs      (AI subsystem, written by AI audit agent)

This created an alembic branch split: `alembic upgrade head` would fail with
"Multiple head revisions are present" until the branches are merged.

This merge migration has no DDL of its own — it only reconnects the two branches
into a single linear chain so `alembic upgrade head` works again.

Chain after this migration:
  041
  ├── 042_add_reduced_appeal_status
  └── 042_seed_ai_model_configs → 043_ai_model_configs_unique → 044_widen_knowledge_discord_message_id
                                                                          ↓
                                                           045_merge_042_branches  ← (you are here)

Both branches have been applied to the DB before this migration runs
(alembic applies all ancestors before a merge point), so no DDL is needed.

Revision ID: 045_merge_042_branches
Revises: 042_add_reduced_appeal_status, 044_widen_knowledge_discord_message_id
Create Date: 2026-08-29
"""
from alembic import op

revision = "045_merge_042_branches"
down_revision = ("044_widen_knowledge_discord_message_id", "042_add_reduced_appeal_status")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No DDL — this migration only merges two alembic branch heads.
    pass


def downgrade() -> None:
    pass
