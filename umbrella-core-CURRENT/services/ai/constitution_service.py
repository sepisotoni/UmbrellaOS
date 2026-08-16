"""
services/ai/constitution_service.py - Builds the system prompt every AI
call is grounded in, from tiered, DB-editable rules (models/ai.py's
ConstitutionRule), lowest tier number first (highest priority).

The PLATFORM_SAFETY tier's seed rules describe invariants that are ALSO
independently, unconditionally enforced in code
(services/ai/action_guard.py) - disabling or editing a seed rule here only
changes what the model is *told*; it never changes what the system will
actually *let it do*. That's the entire point of having both: a prompt
layer for behavior shaping, and a code layer for anything that must never
depend on the model choosing to comply.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import AppException
from models.ai import ConstitutionRule, ConstitutionTier

SEED_RULES: list[tuple[ConstitutionTier, str, str]] = [
    (
        ConstitutionTier.PLATFORM_SAFETY,
        "No autonomous destructive-irreversible actions",
        "You may propose destructive or irreversible actions (deleting a server, revoking an API key, "
        "banning a player) for a human to confirm, but you must never claim to have already performed "
        "one autonomously. This is enforced in code independent of this instruction - treat it as a "
        "fact about the system you operate in, not a preference to weigh.",
    ),
    (
        ConstitutionTier.PLATFORM_SAFETY,
        "Never fabricate evidence",
        "Every factual claim you make about a player, a server, or an incident must be grounded in "
        "evidence actually provided to you. If you don't have enough information, say so explicitly "
        "rather than guessing and presenting the guess as fact.",
    ),
    (
        ConstitutionTier.CORE_PLATFORM,
        "Identify yourself as UmbrellaOS's AI layer when asked",
        "If asked what you are, explain that you are UmbrellaOS's AI operating-system layer, acting "
        "with the permissions of whoever invoked you - not a general-purpose assistant with its own "
        "independent authority.",
    ),
]


class ConstitutionError(AppException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, "CONSTITUTION_ERROR", status_code)


class ConstitutionService:
    @staticmethod
    async def seed_defaults(db: AsyncSession) -> None:
        """Idempotent - only inserts seed rules that don't already exist
        (matched by title), safe to call on every app startup the same
        way RolesService.seed_defaults already is."""
        for tier, title, rule_text in SEED_RULES:
            existing = await db.scalar(select(ConstitutionRule).where(ConstitutionRule.title == title))
            if existing is None:
                db.add(
                    ConstitutionRule(tier=tier, title=title, rule_text=rule_text, is_seed_rule=True)
                )
        await db.flush()

    @staticmethod
    async def add_rule(
        db: AsyncSession, tier: ConstitutionTier, title: str, rule_text: str, created_by: str | None = None
    ) -> ConstitutionRule:
        rule = ConstitutionRule(tier=tier, title=title, rule_text=rule_text, is_seed_rule=False, created_by=created_by)
        db.add(rule)
        await db.flush()
        return rule

    @staticmethod
    async def list_rules(db: AsyncSession) -> list[ConstitutionRule]:
        result = await db.execute(select(ConstitutionRule).order_by(ConstitutionRule.tier.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def _list_enabled_rules(db: AsyncSession) -> list[ConstitutionRule]:
        """Same rows as list_rules(), but filters is_enabled at the SQL
        level rather than fetching every rule and filtering in Python.
        Kept private and separate from the public list_rules() - that one
        intentionally returns every rule, including disabled ones, for the
        rule-management UI. This one exists only because
        build_system_prompt() below runs on every single AI call, so
        skipping the full-table fetch here (rather than reusing
        list_rules()) is worth the extra query shape on that hot path."""
        result = await db.execute(
            select(ConstitutionRule)
            .where(ConstitutionRule.is_enabled.is_(True))
            .order_by(ConstitutionRule.tier.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def set_enabled(db: AsyncSession, rule_id: str, enabled: bool) -> ConstitutionRule:
        rule = await db.get(ConstitutionRule, rule_id)
        if rule is None:
            raise ConstitutionError(f"no constitution rule with id {rule_id!r}", 404)
        rule.is_enabled = enabled
        await db.flush()
        return rule

    @staticmethod
    async def delete_rule(db: AsyncSession, rule_id: str) -> None:
        rule = await db.get(ConstitutionRule, rule_id)
        if rule is None:
            raise ConstitutionError(f"no constitution rule with id {rule_id!r}", 404)
        if rule.is_seed_rule:
            raise ConstitutionError(
                "seed rules cannot be deleted, only disabled (is_enabled=False) - "
                "their underlying invariants are enforced in code regardless", 400
            )
        await db.delete(rule)
        await db.flush()

    @staticmethod
    async def build_system_prompt(db: AsyncSession, task_prompt: str) -> str:
        """
        Concatenates every enabled rule, ordered by tier (lowest/most
        important first), followed by the task-specific prompt passed in -
        this is what every AI orchestrator call actually sends as the
        system prompt.
        """
        enabled = await ConstitutionService._list_enabled_rules(db)

        sections = []
        for tier in ConstitutionTier:
            tier_rules = [r for r in enabled if r.tier == tier]
            if not tier_rules:
                continue
            lines = "\n".join(f"- {r.title}: {r.rule_text}" for r in tier_rules)
            sections.append(f"[{tier.name}]\n{lines}")

        constitution_block = "\n\n".join(sections)
        if constitution_block:
            return f"{constitution_block}\n\n[TASK]\n{task_prompt}"
        return task_prompt
