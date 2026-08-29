"""Seed ai_model_configs with default (provider, model) rows for every task type.

The ModelRouter selects candidates from this table. Without rows, every
Orchestrator.run() call raises NoAvailableModelError and returns 503 —
the copilot endpoint, crash-risk endpoint, and every capability that calls
the orchestrator all fail out of the box.

Rows are inserted with ON CONFLICT DO NOTHING so this migration is
idempotent: running it again (or running it on a DB that already has
custom rows) is safe.

Also seeds the three platform-safety constitution rules that
ConstitutionService.seed_defaults() produces, in case startup's seed call
was skipped or this is a fresh DB being bootstrapped directly from
migrations.

Revision ID: 042_seed_ai_model_configs
Revises: 041_fix_ipban_player_uuid_and_punishment_nullable
Create Date: 2026-08-28
"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

revision = "042_seed_ai_model_configs"
down_revision = "041_fix_ipban_player_uuid_and_punishment_nullable"
branch_labels = None
depends_on = None

# Default (provider, model_name, task_type, priority) rows.
# Priority 10 = primary, 20 = failover.  All enabled and healthy by default.
# Operators can add/reorder rows from the dashboard without touching code.
_MODEL_ROWS = [
    # copilot — Gemini primary, OpenRouter fallback
    ("gemini",     "gemini-1.5-flash",          "copilot",        10),
    ("openrouter", "openai/gpt-4o-mini",         "copilot",        20),
    # player_review — Gemini primary, Anthropic fallback
    ("gemini",     "gemini-1.5-flash",          "player_review",  10),
    ("anthropic",  "claude-haiku-4-5-20251001", "player_review",  20),
    # appeal_review — Anthropic primary, Gemini fallback
    ("anthropic",  "claude-haiku-4-5-20251001", "appeal_review",  10),
    ("gemini",     "gemini-1.5-flash",          "appeal_review",  20),
    # moderation_review (ai_service legacy path) — Anthropic primary, OpenRouter fallback
    ("anthropic",  "claude-haiku-4-5-20251001", "moderation_review", 10),
    ("openrouter", "openai/gpt-4o-mini",         "moderation_review", 20),
    # crash_risk — Gemini only (deterministic enough to skip dual-review)
    ("gemini",     "gemini-1.5-flash",          "crash_risk",     10),
    # chat_review — OpenRouter primary
    ("openrouter", "openai/gpt-4o-mini",         "chat_review",    10),
    ("anthropic",  "claude-haiku-4-5-20251001", "chat_review",    20),
]

_CONSTITUTION_SEED_RULES = [
    (
        "PLATFORM_SAFETY",
        "No autonomous destructive-irreversible actions",
        (
            "You may propose destructive or irreversible actions (deleting a server, revoking an API key, "
            "banning a player) for a human to confirm, but you must never claim to have already performed "
            "one autonomously. This is enforced in code independent of this instruction - treat it as a "
            "fact about the system you operate in, not a preference to weigh."
        ),
    ),
    (
        "PLATFORM_SAFETY",
        "Never fabricate evidence",
        (
            "Every factual claim you make about a player, a server, or an incident must be grounded in "
            "evidence actually provided to you. If you don't have enough information, say so explicitly "
            "rather than guessing and presenting the guess as fact."
        ),
    ),
    (
        "CORE_PLATFORM",
        "Identify yourself as UmbrellaOS's AI layer when asked",
        (
            "If asked what you are, explain that you are UmbrellaOS's AI operating-system layer, acting "
            "with the permissions of whoever invoked you - not a general-purpose assistant with its own "
            "independent authority."
        ),
    ),
]


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # ------------------------------------------------------------------ #
    # Unique constraint required by ON CONFLICT below                     #
    # ------------------------------------------------------------------ #
    # PostgreSQL requires a matching unique index or constraint for any
    # ON CONFLICT (col1, col2, col3) clause. Without this, the INSERT
    # below errors: "there is no unique or exclusion constraint matching
    # the ON CONFLICT specification". Creating it here (before the INSERT)
    # keeps the two steps in one atomic migration; migration 043 adds the
    # same constraint under the same name for DBs that ran 042 before this
    # fix was applied (idempotent via CREATE … IF NOT EXISTS pattern).
    if is_postgres:
        op.execute(sa.text(
            "ALTER TABLE ai_model_configs "
            "ADD CONSTRAINT IF NOT EXISTS uq_ai_model_configs_provider_model_task "
            "UNIQUE (provider, model_name, task_type)"
        ))
    # SQLite has no ALTER TABLE ADD CONSTRAINT, but also has no ON CONFLICT
    # index_elements requirement — it falls back to the per-row path below.

    # ------------------------------------------------------------------ #
    # Seed ai_model_configs                                               #
    # ------------------------------------------------------------------ #
    ai_model_configs = sa.table(
        "ai_model_configs",
        sa.column("id",                  sa.String),
        sa.column("provider",            sa.String),
        sa.column("model_name",          sa.String),
        sa.column("task_type",           sa.String),
        sa.column("priority",            sa.Integer),
        sa.column("enabled",             sa.Boolean),
        sa.column("is_healthy",          sa.Boolean),
        sa.column("consecutive_failures",sa.Integer),
    )

    rows = [
        {
            "id":                   str(uuid.uuid4()),
            "provider":             provider,
            "model_name":           model_name,
            "task_type":            task_type,
            "priority":             priority,
            "enabled":              True,
            "is_healthy":           True,
            "consecutive_failures": 0,
        }
        for provider, model_name, task_type, priority in _MODEL_ROWS
    ]

    if is_postgres:
        # INSERT … ON CONFLICT DO NOTHING — idempotent on (provider, model_name, task_type)
        # PostgreSQL supports this natively.
        stmt = pg_insert(ai_model_configs).values(rows)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["provider", "model_name", "task_type"]
        )
        op.execute(stmt)
    else:
        # SQLite / fallback: check each row individually.
        for row in rows:
            existing = bind.execute(
                sa.text(
                    "SELECT 1 FROM ai_model_configs "
                    "WHERE provider=:p AND model_name=:m AND task_type=:t LIMIT 1"
                ),
                {"p": row["provider"], "m": row["model_name"], "t": row["task_type"]},
            ).fetchone()
            if not existing:
                op.execute(
                    ai_model_configs.insert().values(row)
                )

    # ------------------------------------------------------------------ #
    # Seed constitution_rules                                             #
    # ------------------------------------------------------------------ #
    constitution_rules = sa.table(
        "constitution_rules",
        sa.column("id",          sa.String),
        sa.column("tier",        sa.String),
        sa.column("title",       sa.String),
        sa.column("rule_text",   sa.Text),
        sa.column("is_seed_rule",sa.Boolean),
        sa.column("is_enabled",  sa.Boolean),
    )

    for tier, title, rule_text in _CONSTITUTION_SEED_RULES:
        existing = bind.execute(
            sa.text("SELECT 1 FROM constitution_rules WHERE title=:t LIMIT 1"),
            {"t": title},
        ).fetchone()
        if not existing:
            op.execute(
                constitution_rules.insert().values(
                    id=str(uuid.uuid4()),
                    tier=tier,
                    title=title,
                    rule_text=rule_text,
                    is_seed_rule=True,
                    is_enabled=True,
                )
            )


def downgrade() -> None:
    # Remove only the rows this migration inserted — identified by title
    # (constitution) or by (provider, model_name, task_type) tuple (model
    # configs).  Rows added by operators after this migration runs are
    # intentionally left alone.
    for _, title, _ in _CONSTITUTION_SEED_RULES:
        op.execute(
            sa.text(
                "DELETE FROM constitution_rules WHERE title=:t AND is_seed_rule=true"
            ).bindparams(t=title)
        )

    for provider, model_name, task_type, _ in _MODEL_ROWS:
        op.execute(
            sa.text(
                "DELETE FROM ai_model_configs "
                "WHERE provider=:p AND model_name=:m AND task_type=:t"
            ).bindparams(p=provider, m=model_name, t=task_type)
        )
