"""
tests/test_moderation_intelligence.py - Tests for
services/moderation_intelligence/service.py and repository.py.

ModelRouter.generate is monkeypatched the same way test_orchestrator.py
does it - these tests exercise the moderation analysis pipeline's own
logic (evidence gathering, escalation decisions, the two bug fixes below),
not the orchestrator/router themselves.
"""
from datetime import datetime, timedelta, timezone

import pytest

from config import get_settings
from models.discord import ChatMessage
from models.moderation_intelligence import (
    ModerationAction,
    ModerationActionType,
    RecommendedAction,
    ReportStatus,
)
from services.ai.base import GenerationResult
from services.ai.model_router import ModelRouter, RoutedGeneration
from services.moderation_intelligence.repository import ModerationIntelRepository
from services.moderation_intelligence.service import ModerationIntelligenceService, _moderation_agreement, _safe_parse


def _routed(provider: str, text: str) -> RoutedGeneration:
    return RoutedGeneration(
        result=GenerationResult(text=text, model_name=f"{provider}-model", latency_ms=10),
        provider=provider,
        model_name=f"{provider}-model",
    )


def _patch_generate(monkeypatch, *texts):
    responses = iter([_routed("anthropic", texts[0])] + [_routed("openrouter", t) for t in texts[1:]])

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        return next(responses)

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)


@pytest.mark.asyncio
async def test_analyze_report_auto_resolves_on_high_confidence_agreement(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "dual_review_enabled", True)
    text = '{"risk_score": 0.1, "recommended_action": "none", "evidence_summary": "Nothing concerning found."}'
    _patch_generate(monkeypatch, text, text)

    async with db_session() as db:
        report = await ModerationIntelRepository.create_report(
            db, reported_user_id="user-1", reporter_id="reporter-1", channel_id="chan-1",
            reported_message_id=None, reason="Being rude",
        )
        result = await ModerationIntelligenceService.analyze_report(db, report)
        await db.commit()

        assert result["recommended_action"] == "none"
        assert result["escalated"] is False

        refreshed = await db.get(type(report), report.id)
        assert refreshed.status == ReportStatus.AUTO_RESOLVED


@pytest.mark.asyncio
async def test_analyze_report_escalates_on_disagreement(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "dual_review_enabled", True)
    _patch_generate(
        monkeypatch,
        '{"risk_score": 0.8, "recommended_action": "timeout", "evidence_summary": "Looks bad."}',
        '{"risk_score": 0.1, "recommended_action": "none", "evidence_summary": "Looks fine."}',
    )

    async with db_session() as db:
        report = await ModerationIntelRepository.create_report(
            db, reported_user_id="user-2", reporter_id="reporter-1", channel_id="chan-1",
            reported_message_id=None, reason="Reported for spam",
        )
        result = await ModerationIntelligenceService.analyze_report(db, report)
        await db.commit()

        assert result["escalated"] is True
        refreshed = await db.get(type(report), report.id)
        assert refreshed.status == ReportStatus.ESCALATED


@pytest.mark.asyncio
async def test_analyze_report_falls_back_to_escalate_on_invalid_recommended_action(db_session, monkeypatch):
    """Bug B, fixed: the source crashed with an uncaught ValueError when
    the model returned an action outside the five allowed values. This
    must instead fall back to ESCALATE, not raise."""
    monkeypatch.setattr(get_settings(), "dual_review_enabled", False)
    text = '{"risk_score": 0.9, "recommended_action": "ban", "evidence_summary": "Model ignored instructions."}'
    _patch_generate(monkeypatch, text)

    async with db_session() as db:
        report = await ModerationIntelRepository.create_report(
            db, reported_user_id="user-3", reporter_id="reporter-1", channel_id="chan-1",
            reported_message_id=None, reason="Severe report",
        )
        # Must not raise:
        result = await ModerationIntelligenceService.analyze_report(db, report)
        await db.commit()

        assert result["recommended_action"] == RecommendedAction.ESCALATE.value
        assert result["escalated"] is True


@pytest.mark.asyncio
async def test_moderation_agreement_ignores_code_fences():
    """Bug C, fixed: the source's agreement check didn't strip markdown
    fences (unlike _safe_parse), so a fenced response was scored as
    disagreement purely due to formatting."""
    fenced = '```json\n{"recommended_action": "warn"}\n```'
    plain = '{"recommended_action": "warn", "evidence_summary": "differently worded"}'
    assert _moderation_agreement(fenced, plain) == 1.0


@pytest.mark.asyncio
async def test_safe_parse_strips_fences_and_never_raises():
    assert _safe_parse('```json\n{"a": 1}\n```') == {"a": 1}
    assert _safe_parse("not json at all") == {}


@pytest.mark.asyncio
async def test_check_repeat_offender_creates_report_once_threshold_crossed(db_session):
    settings = get_settings()
    async with db_session() as db:
        now = datetime.now(timezone.utc)
        for _ in range(settings.repeat_offender_warning_count):
            db.add(
                ModerationAction(
                    user_id="user-4", moderator_id="staff-1", action_type=ModerationActionType.WARN,
                    created_at=now,
                )
            )
        await db.flush()

        report = await ModerationIntelligenceService.check_repeat_offender(db, "user-4")
        await db.commit()

        assert report is not None
        assert report.source == "heuristic:repeat_offender"
        assert report.reported_user_id == "user-4"


@pytest.mark.asyncio
async def test_check_repeat_offender_returns_none_below_threshold(db_session):
    async with db_session() as db:
        db.add(
            ModerationAction(
                user_id="user-5", moderator_id="staff-1", action_type=ModerationActionType.WARN,
                created_at=datetime.now(timezone.utc),
            )
        )
        await db.flush()

        report = await ModerationIntelligenceService.check_repeat_offender(db, "user-5")
        assert report is None


@pytest.mark.asyncio
async def test_check_repeat_offender_ignores_warnings_outside_lookback_window(db_session):
    settings = get_settings()
    async with db_session() as db:
        old = datetime.now(timezone.utc) - timedelta(hours=settings.repeat_offender_lookback_hours + 1)
        for _ in range(settings.repeat_offender_warning_count):
            db.add(
                ModerationAction(
                    user_id="user-6", moderator_id="staff-1", action_type=ModerationActionType.WARN,
                    created_at=old,
                )
            )
        await db.flush()

        report = await ModerationIntelligenceService.check_repeat_offender(db, "user-6")
        assert report is None


@pytest.mark.asyncio
async def test_gather_evidence_includes_recent_messages(db_session):
    async with db_session() as db:
        db.add(ChatMessage(source="discord", discord_id="user-7", discord_channel_id="chan-1", message="hello there", timestamp=datetime.now(timezone.utc)))
        await db.flush()

        evidence = await ModerationIntelligenceService._gather_evidence(db, "user-7")
        assert "hello there" in evidence
        assert "Recent warning count" in evidence
