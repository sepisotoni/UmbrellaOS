"""
tests/test_constitution_service.py - Tests for services/ai/constitution_service.py.
"""
import pytest

from models.ai import ConstitutionTier
from services.ai.constitution_service import ConstitutionError, ConstitutionService


@pytest.mark.asyncio
async def test_seed_defaults_inserts_seed_rules(db_session):
    async with db_session() as db:
        await ConstitutionService.seed_defaults(db)
        await db.commit()

    async with db_session() as db:
        rules = await ConstitutionService.list_rules(db)
        titles = {r.title for r in rules}
        assert "No autonomous destructive-irreversible actions" in titles
        assert all(r.is_seed_rule for r in rules)


@pytest.mark.asyncio
async def test_seed_defaults_is_idempotent(db_session):
    async with db_session() as db:
        await ConstitutionService.seed_defaults(db)
        await db.commit()

    async with db_session() as db:
        await ConstitutionService.seed_defaults(db)  # a "second boot"
        await db.commit()

    async with db_session() as db:
        rules = await ConstitutionService.list_rules(db)
        titles = [r.title for r in rules]
        assert len(titles) == len(set(titles))  # no duplicates from running seeding twice


@pytest.mark.asyncio
async def test_add_custom_rule(db_session):
    async with db_session() as db:
        rule = await ConstitutionService.add_rule(
            db, ConstitutionTier.SERVER, "Be concise in this Discord channel", "Keep responses under 3 sentences."
        )
        await db.commit()
        assert rule.is_seed_rule is False
        assert rule.tier == ConstitutionTier.SERVER


@pytest.mark.asyncio
async def test_set_enabled_toggles_a_rule(db_session):
    async with db_session() as db:
        rule = await ConstitutionService.add_rule(db, ConstitutionTier.TASK, "Custom", "text")
        await db.commit()
        rule_id = rule.id

    async with db_session() as db:
        updated = await ConstitutionService.set_enabled(db, rule_id, False)
        await db.commit()
        assert updated.is_enabled is False


@pytest.mark.asyncio
async def test_delete_rule_refuses_seed_rules(db_session):
    async with db_session() as db:
        await ConstitutionService.seed_defaults(db)
        await db.commit()

    async with db_session() as db:
        rules = await ConstitutionService.list_rules(db)
        seed_rule_id = rules[0].id
        with pytest.raises(ConstitutionError, match="cannot be deleted"):
            await ConstitutionService.delete_rule(db, seed_rule_id)


@pytest.mark.asyncio
async def test_delete_rule_allows_custom_rules(db_session):
    async with db_session() as db:
        rule = await ConstitutionService.add_rule(db, ConstitutionTier.TASK, "Custom", "text")
        await db.commit()
        rule_id = rule.id

    async with db_session() as db:
        await ConstitutionService.delete_rule(db, rule_id)
        await db.commit()

    async with db_session() as db:
        rules = await ConstitutionService.list_rules(db)
        assert rule_id not in {r.id for r in rules}


@pytest.mark.asyncio
async def test_build_system_prompt_includes_enabled_rules_in_tier_order(db_session):
    async with db_session() as db:
        await ConstitutionService.add_rule(db, ConstitutionTier.TASK, "Task rule", "task text")
        await ConstitutionService.add_rule(db, ConstitutionTier.PLATFORM_SAFETY, "Safety rule", "safety text")
        await db.commit()

        prompt = await ConstitutionService.build_system_prompt(db, "Summarize this incident.")

        safety_pos = prompt.index("Safety rule")
        task_pos = prompt.index("Task rule")
        assert safety_pos < task_pos  # PLATFORM_SAFETY (0) must appear before TASK (4)
        assert "Summarize this incident." in prompt


@pytest.mark.asyncio
async def test_build_system_prompt_excludes_disabled_rules(db_session):
    async with db_session() as db:
        rule = await ConstitutionService.add_rule(db, ConstitutionTier.TASK, "Disabled rule", "should not appear")
        await ConstitutionService.set_enabled(db, rule.id, False)
        await db.commit()

        prompt = await ConstitutionService.build_system_prompt(db, "task")
        assert "should not appear" not in prompt


@pytest.mark.asyncio
async def test_build_system_prompt_with_no_rules_returns_just_the_task_prompt(db_session):
    async with db_session() as db:
        prompt = await ConstitutionService.build_system_prompt(db, "just the task")
        assert prompt == "just the task"


@pytest.mark.asyncio
async def test_set_enabled_raises_for_unknown_rule(db_session):
    async with db_session() as db:
        with pytest.raises(ConstitutionError):
            await ConstitutionService.set_enabled(db, "00000000-0000-0000-0000-000000000000", False)
