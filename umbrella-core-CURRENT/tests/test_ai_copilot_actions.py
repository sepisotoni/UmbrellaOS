"""Integration tests for Copilot action proposals."""

import json

import pytest
from sqlalchemy import select

from models import AITask, Player, Punishment
from services.ai.orchestrator import OrchestrationResult


def _result(text: str) -> OrchestrationResult:
    return OrchestrationResult(
        text=text,
        confidence=1.0,
        escalated=False,
        primary_provider="test",
        primary_model="test-model",
        secondary_provider=None,
        secondary_model=None,
        dual_review_agreement=None,
        decision_log_id="test-decision",
    )


@pytest.mark.asyncio
async def test_copilot_returns_confirmation_card_data_without_executing(
    client, db_session, monkeypatch
):
    async with db_session() as db:
        player = Player(
            uuid="dddddddd-dddd-dddd-dddd-dddddddddddd",
            username="ChatProposalTarget",
        )
        db.add(player)
        await db.commit()
        player_uuid = player.uuid

    calls = 0

    async def fake_run(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            tool_call = [
                {
                    "tool": "propose_moderation_action",
                    "action": "tempban",
                    "player_uuid": player_uuid,
                    "reason": "Repeated cheating",
                    "duration_hours": 48,
                }
            ]
            return _result(f"```json\n{json.dumps(tool_call)}\n```")
        return _result("A 48-hour ban is ready for staff confirmation.")

    monkeypatch.setattr("api.routers.ai_copilot.Orchestrator.run", fake_run)
    response = await client.post(
        "/api/v1/ai/copilot",
        json={"message": "Suspend ChatProposalTarget for 48 hours for cheating"},
        headers={"X-Admin-Key": "test-secret-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["pending_actions"][0]["action"] == "tempban"
    assert data["pending_actions"][0]["player_uuid"] == player_uuid
    assert data["pending_actions"][0]["duration_hours"] == 48
    assert data["pending_actions"][0]["confirmation_required"] is True
    async with db_session() as db:
        task = await db.scalar(
            select(AITask).where(AITask.task_type == "copilot_moderation_action")
        )
        punishment = await db.scalar(
            select(Punishment).where(Punishment.player_uuid == player_uuid)
        )
        assert task.status == "pending"
        assert punishment is None
