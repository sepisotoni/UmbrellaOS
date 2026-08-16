"""
tests/test_nl_query.py — Tests for
services/operational_intelligence/nl_query.py.
"""
import datetime as dt

import pytest

from config import get_settings
from models.audit_log import AuditLog
from models.server_metrics import ServerMetricSnapshot
from services.ai.base import GenerationResult
from services.ai.model_router import ModelRouter, RoutedGeneration
from services.operational_intelligence.nl_query import answer_operational_query


def _routed(provider: str, text: str) -> RoutedGeneration:
    return RoutedGeneration(
        result=GenerationResult(text=text, model_name=f"{provider}-model", latency_ms=10),
        provider=provider,
        model_name=f"{provider}-model",
    )


@pytest.mark.asyncio
async def test_answer_grounds_response_in_window_evidence(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "dual_review_enabled", False)

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        # Confirm the actual TPS numbers made it into the prompt fed to the model.
        assert "12.0" in user_prompt or "TPS ranged" in user_prompt
        return _routed("anthropic", "TPS dropped due to a plugin reload at that time.")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        window_start = dt.datetime(2026, 6, 1, 14, 55, tzinfo=dt.timezone.utc)
        window_end = dt.datetime(2026, 6, 1, 15, 5, tzinfo=dt.timezone.utc)

        db.add(ServerMetricSnapshot(server_id="srv-1", tps=20.0, online_count=10, recorded_at=window_start))
        db.add(ServerMetricSnapshot(server_id="srv-1", tps=12.0, online_count=10, recorded_at=window_start + dt.timedelta(minutes=5)))
        db.add(AuditLog(actor="plugin", actor_type="plugin", action="plugin.reload", target="WorldEdit", created_at=window_start + dt.timedelta(minutes=4)))
        await db.flush()

        result = await answer_operational_query(
            db, server_id="srv-1", question="Why did the server lag at 3pm?",
            window_start=window_start, window_end=window_end,
        )
        assert "plugin reload" in result["answer"]
        assert "12.0" in result["evidence"]
        assert "plugin.reload" in result["evidence"]


@pytest.mark.asyncio
async def test_answer_handles_empty_window_gracefully(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "dual_review_enabled", False)

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        assert "No server metric snapshots" in user_prompt
        return _routed("anthropic", "No data is available for that window.")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        window_start = dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc)
        window_end = dt.datetime(2020, 1, 1, 0, 10, tzinfo=dt.timezone.utc)

        result = await answer_operational_query(
            db, server_id="srv-empty", question="Why did it lag?",
            window_start=window_start, window_end=window_end,
        )
        assert "No data is available" in result["answer"]


@pytest.mark.asyncio
async def test_answer_escalated_writes_staff_escalation_and_publishes_event(db_session, monkeypatch):
    """Phase 7, Decision 1's proof case: this used to only set
    result["escalated"] and go nowhere - confirmed by grep during Phase 6,
    only services/moderation_intelligence/*.py wrote to StaffEscalation.
    Now it must actually write a StaffEscalation row and an outbox event,
    in the same transaction."""
    from sqlalchemy import select

    from models.events import Event
    from models.moderation_intelligence import StaffEscalation

    monkeypatch.setattr(get_settings(), "dual_review_enabled", False)
    # Force escalation without needing real dual-review disagreement -
    # confidence is always 1.0 with dual review off, so raising the
    # threshold above that guarantees `escalated = confidence < threshold`.
    monkeypatch.setattr(get_settings(), "confidence_escalation_threshold", 1.5)

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        return _routed("anthropic", "Uncertain answer, needs a human to check.")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        window_start = dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc)
        window_end = dt.datetime(2020, 1, 1, 0, 10, tzinfo=dt.timezone.utc)

        result = await answer_operational_query(
            db, server_id="srv-escalate", question="Why did it lag?",
            window_start=window_start, window_end=window_end,
        )
        assert result["escalated"] is True
        await db.commit()

    async with db_session() as db:
        escalations = list((await db.execute(
            select(StaffEscalation).where(StaffEscalation.source == "operational")
        )).scalars().all())
        assert len(escalations) == 1
        assert "srv-escalate" in escalations[0].summary
        assert escalations[0].resolved is False

        events = list((await db.execute(
            select(Event).where(Event.topic == "staff_escalation.created")
        )).scalars().all())
        assert len(events) == 1
        import json
        payload = json.loads(events[0].payload_json)
        assert payload["escalation_id"] == escalations[0].id
        assert payload["source"] == "operational"
        assert payload["server_id"] == "srv-escalate"


@pytest.mark.asyncio
async def test_answer_not_escalated_writes_no_staff_escalation(db_session, monkeypatch):
    from sqlalchemy import select

    from models.moderation_intelligence import StaffEscalation

    monkeypatch.setattr(get_settings(), "dual_review_enabled", False)
    # Default threshold (0.6) is comfortably below the 1.0 confidence
    # dual-review-off always produces, so this must NOT escalate.

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        return _routed("anthropic", "Confident answer.")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        window_start = dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc)
        window_end = dt.datetime(2020, 1, 1, 0, 10, tzinfo=dt.timezone.utc)

        result = await answer_operational_query(
            db, server_id="srv-fine", question="Why did it lag?",
            window_start=window_start, window_end=window_end,
        )
        assert result["escalated"] is False
        await db.commit()

    async with db_session() as db:
        escalations = list((await db.execute(
            select(StaffEscalation).where(StaffEscalation.source == "operational")
        )).scalars().all())
        assert escalations == []
