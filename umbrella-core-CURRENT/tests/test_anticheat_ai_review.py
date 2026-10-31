"""Regression coverage for configured anticheat AI routing and fallback."""

from types import SimpleNamespace

import pytest

from services import anticheat_service
from services.ai.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_anticheat_confidence_routes_through_configured_provider(
    db_session, monkeypatch
):
    seen = {}

    async def fake_run(
        *, db, task_type, task_prompt, system_instructions,
        requested_by, require_dual_review
    ):
        seen.update(
            task_type=task_type,
            task_prompt=task_prompt,
            system_instructions=system_instructions,
            require_dual_review=require_dual_review,
        )
        return SimpleNamespace(text='{"confidence": 0.84, "reason": "repeatable pattern"}')

    monkeypatch.setattr(Orchestrator, "run", fake_run)

    async with db_session() as db:
        confidence, reason = await anticheat_service._ai_confidence_review(
            db, "Fly", "unexpected elevation", 11, "Steve", 2
        )

    assert confidence == pytest.approx(0.84)
    assert reason == "repeatable pattern"
    assert seen["task_type"] == "moderation_review"
    assert seen["require_dual_review"] is False
    assert "Fly" in seen["task_prompt"]
    assert "unexpected elevation" not in seen["system_instructions"]
    assert "JSON object" in seen["system_instructions"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "output",
    [
        "not valid json",
        '{"confidence": "not-a-number"}',
        '{"confidence": "NaN"}',
        '{"confidence": "Infinity"}',
        None,
    ],
)
async def test_anticheat_confidence_uses_vl_fallback_when_ai_fails(
    db_session, monkeypatch, output
):
    async def fake_run(**kwargs):
        if output is None:
            raise RuntimeError("provider unavailable")
        return SimpleNamespace(text=output)

    monkeypatch.setattr(Orchestrator, "run", fake_run)

    async with db_session() as db:
        confidence, reason = await anticheat_service._ai_confidence_review(
            db, "Fly", "test", 4, "Steve", 0
        )

    assert confidence == pytest.approx(0.7)
    assert reason == "vl_math_fallback"


@pytest.mark.asyncio
async def test_anticheat_database_failure_is_not_silently_swallowed(
    db_session, monkeypatch
):
    from sqlalchemy.exc import OperationalError

    async def fake_run(**kwargs):
        raise OperationalError("SELECT 1", {}, RuntimeError("connection unavailable"))

    monkeypatch.setattr(Orchestrator, "run", fake_run)

    async with db_session() as db:
        with pytest.raises(OperationalError):
            await anticheat_service._ai_confidence_review(
                db, "Fly", "test", 4, "Steve", 0
            )
