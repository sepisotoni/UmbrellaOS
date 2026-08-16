"""
tests/test_orchestrator.py - Tests for services/ai/orchestrator.py.

ModelRouter.generate is monkeypatched to return scripted RoutedGeneration
results (agreeing / disagreeing / single-available), so these tests
exercise the orchestrator's own dual-review/confidence/escalation logic -
the router itself is already independently tested
(tests/test_model_router.py).
"""
import pytest

from config import get_settings
from models.ai import AIDecisionLog
from services.ai.base import GenerationResult
from services.ai.model_router import ModelRouter, NoAvailableModelError, RoutedGeneration
from services.ai.orchestrator import Orchestrator


def _routed(provider: str, text: str) -> RoutedGeneration:
    return RoutedGeneration(
        result=GenerationResult(text=text, model_name=f"{provider}-model", latency_ms=10),
        provider=provider,
        model_name=f"{provider}-model",
    )


@pytest.mark.asyncio
async def test_single_review_when_dual_review_disabled(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "dual_review_enabled", False)

    call_count = {"n": 0}

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        call_count["n"] += 1
        return _routed("anthropic", "the answer")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        result = await Orchestrator.run(db, "chat", "what is the server status?")
        await db.commit()

        assert call_count["n"] == 1  # only the primary call, no secondary
        assert result.secondary_provider is None
        assert result.confidence == 1.0
        assert result.escalated is False


@pytest.mark.asyncio
async def test_dual_review_agreement_produces_high_confidence(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "dual_review_enabled", True)

    responses = iter([
        _routed("anthropic", "The server is running normally with 42 players online."),
        _routed("openrouter", "The server is running normally with 42 players online."),
    ])

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        return next(responses)

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        result = await Orchestrator.run(db, "chat", "what is the server status?")
        await db.commit()

        assert result.dual_review_agreement is True
        assert result.confidence > 0.9
        assert result.escalated is False
        assert result.secondary_provider == "openrouter"


@pytest.mark.asyncio
async def test_agreement_fn_overrides_default_text_similarity(db_session, monkeypatch):
    """Two responses that would score LOW on raw text similarity (very
    different wording/length) but agree on a structured field - the
    default _similarity would likely call this a disagreement and
    escalate; a custom agreement_fn comparing just the structured field
    should correctly call it agreement instead."""
    settings = get_settings()
    monkeypatch.setattr(settings, "dual_review_enabled", True)

    responses = iter([
        _routed("anthropic", '{"recommended_action": "warn", "evidence_summary": "Brief note."}'),
        _routed(
            "openrouter",
            '{"recommended_action": "warn", "evidence_summary": '
            '"A much longer, differently worded explanation covering the same underlying finding in more detail."}',
        ),
    ])

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        return next(responses)

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    def by_recommended_action(text_a: str, text_b: str) -> float:
        import json
        a = json.loads(text_a).get("recommended_action")
        b = json.loads(text_b).get("recommended_action")
        return 1.0 if a == b else 0.0

    async with db_session() as db:
        result = await Orchestrator.run(db, "moderation_review", "analyze this report", agreement_fn=by_recommended_action)
        await db.commit()

        assert result.dual_review_agreement is True
        assert result.confidence == 1.0
        assert result.escalated is False


@pytest.mark.asyncio
async def test_dual_review_disagreement_escalates(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "dual_review_enabled", True)

    responses = iter([
        _routed("anthropic", "The server crashed due to an out-of-memory error at 3am."),
        _routed("openrouter", "Everything looks completely fine, no issues detected."),
    ])

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        return next(responses)

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        result = await Orchestrator.run(db, "chat", "what happened last night?")
        await db.commit()

        assert result.dual_review_agreement is False
        assert result.escalated is True


@pytest.mark.asyncio
async def test_secondary_excludes_primary_provider(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "dual_review_enabled", True)

    captured_excludes = []

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        captured_excludes.append(exclude_providers)
        provider = "anthropic" if exclude_providers is None else "openrouter"
        return _routed(provider, "same answer")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        await Orchestrator.run(db, "chat", "task")

    assert captured_excludes[0] is None  # primary call, no exclusion
    assert captured_excludes[1] == {"anthropic"}  # secondary explicitly excludes the primary's provider


@pytest.mark.asyncio
async def test_only_one_provider_available_reduces_confidence_and_still_completes(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "dual_review_enabled", True)
    monkeypatch.setattr(settings, "confidence_escalation_threshold", 0.6)

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        if exclude_providers:
            raise NoAvailableModelError("only one provider configured")
        return _routed("anthropic", "the only answer")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        result = await Orchestrator.run(db, "chat", "task")
        await db.commit()

        assert result.text == "the only answer"
        assert result.confidence == 0.5
        assert result.escalated is True  # 0.5 < 0.6 threshold


@pytest.mark.asyncio
async def test_no_provider_available_at_all_propagates_error(db_session, monkeypatch):
    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        raise NoAvailableModelError("nothing configured")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        with pytest.raises(NoAvailableModelError):
            await Orchestrator.run(db, "chat", "task")


@pytest.mark.asyncio
async def test_every_call_writes_a_decision_log(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "dual_review_enabled", False)

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        return _routed("anthropic", "an answer")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        result = await Orchestrator.run(db, "chat", "task", requested_by="staff:123")
        await db.commit()

        log = await db.get(AIDecisionLog, result.decision_log_id)
        assert log is not None
        assert log.task_type == "chat"
        assert log.requested_by == "staff:123"
        assert log.primary_provider == "anthropic"


@pytest.mark.asyncio
async def test_explicit_require_dual_review_overrides_global_setting(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "dual_review_enabled", True)  # global default is ON

    call_count = {"n": 0}

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        call_count["n"] += 1
        return _routed("anthropic", "answer")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        # This specific call opts out despite the global default.
        await Orchestrator.run(db, "chat", "task", require_dual_review=False)

    assert call_count["n"] == 1
