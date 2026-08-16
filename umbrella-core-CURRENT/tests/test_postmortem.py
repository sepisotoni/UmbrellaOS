"""
tests/test_postmortem.py — Tests for
services/operational_intelligence/postmortem.py.
"""
import datetime as dt

import pytest

from api.middleware.errors import ResourceNotFoundException
from config import get_settings
from models.audit_log import AuditLog
from services.ai.base import GenerationResult
from services.ai.model_router import ModelRouter, RoutedGeneration
from services.allocation_service import AllocationService
from services.node_service import NodeService
from services.server_template_service import ServerTemplateService
from services.operational_intelligence.postmortem import draft_postmortem


def _routed(provider: str, text: str) -> RoutedGeneration:
    return RoutedGeneration(
        result=GenerationResult(text=text, model_name=f"{provider}-model", latency_ms=10),
        provider=provider,
        model_name=f"{provider}-model",
    )


async def _setup_server(db_session, *, crash_count=0, last_crash_at=None):
    from services.server_service import ServerService

    async with db_session() as db:
        node, _ = await NodeService.register_node(db, "node-pm", "https://node-pm:8443")
        template = await ServerTemplateService.create_template(
            db, "Paper", image="itzg/minecraft-server:java21", startup_command=["start"], default_env={"EULA": "TRUE"},
        )
        await db.commit()
        node_id, template_id = node.id, template.id

    async with db_session() as db:
        allocation = await AllocationService.create_allocation(db, node_id, 25565)
        await db.commit()
        allocation_id = allocation.id

    class _FakeDaemonClient:
        async def create(self, server_id, **kwargs):
            from services.daemon_client import ContainerState
            return ContainerState(server_id=server_id, runtime_id="docker-fake", status="created",
                                   started_at=None, finished_at=None, exit_code=None, oom_killed=False)

    async with db_session() as db:
        server = await ServerService.create_server(
            db, "Survival", node_id, template_id, [allocation_id], daemon_client=_FakeDaemonClient(),
        )
        server.crash_count = crash_count
        server.last_crash_at = last_crash_at
        await db.commit()
        return server.id


@pytest.mark.asyncio
async def test_draft_postmortem_raises_for_unknown_server(db_session):
    async with db_session() as db:
        with pytest.raises(ResourceNotFoundException):
            await draft_postmortem(db, "does-not-exist")


@pytest.mark.asyncio
async def test_draft_postmortem_with_no_crash_history(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "dual_review_enabled", False)
    server_id = await _setup_server(db_session)

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        assert "No crash has been recorded" in user_prompt
        return _routed("anthropic", "No incident to report - this server has no recorded crashes.")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        result = await draft_postmortem(db, server_id)
        assert result["status"] == "draft"
        assert "No incident to report" in result["draft"]


@pytest.mark.asyncio
async def test_draft_postmortem_includes_crash_and_audit_context(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "dual_review_enabled", False)
    crash_time = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=30)
    server_id = await _setup_server(db_session, crash_count=2, last_crash_at=crash_time)

    async with db_session() as db:
        db.add(
            AuditLog(
                actor="admin-key", actor_type="staff", action="settings.update",
                target="hosting.max_players", created_at=crash_time - dt.timedelta(minutes=10),
            )
        )
        await db.commit()

    captured_prompt = {}

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        captured_prompt["text"] = user_prompt
        return _routed("anthropic", "The crash likely followed a settings change shortly before.")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        result = await draft_postmortem(db, server_id, requested_by="admin-1")
        assert result["status"] == "draft"
        assert "settings change" in result["draft"]
        assert "Crash count (consecutive, unattended): 2" in result["evidence"]
        assert "settings.update" in captured_prompt["text"]


@pytest.mark.asyncio
async def test_draft_postmortem_escalated_writes_staff_escalation_and_publishes_event(db_session, monkeypatch):
    """Phase 7, Decision 1's proof case, second call site: draft_postmortem
    had the exact same gap as answer_operational_query - see
    services/operational_intelligence/postmortem.py's module docstring."""
    from sqlalchemy import select

    from models.events import Event
    from models.moderation_intelligence import StaffEscalation

    monkeypatch.setattr(get_settings(), "dual_review_enabled", False)
    monkeypatch.setattr(get_settings(), "confidence_escalation_threshold", 1.5)
    server_id = await _setup_server(db_session)

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        return _routed("anthropic", "Cause unclear, needs a human to check.")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        result = await draft_postmortem(db, server_id)
        assert result["escalated"] is True
        await db.commit()

    async with db_session() as db:
        escalations = list((await db.execute(
            select(StaffEscalation).where(StaffEscalation.source == "operational")
        )).scalars().all())
        assert len(escalations) == 1
        assert escalations[0].resolved is False

        events = list((await db.execute(
            select(Event).where(Event.topic == "staff_escalation.created")
        )).scalars().all())
        assert len(events) == 1
        import json
        payload = json.loads(events[0].payload_json)
        assert payload["escalation_id"] == escalations[0].id
        assert payload["source"] == "operational"
        assert payload["server_id"] == server_id


@pytest.mark.asyncio
async def test_draft_postmortem_not_escalated_writes_no_staff_escalation(db_session, monkeypatch):
    from sqlalchemy import select

    from models.moderation_intelligence import StaffEscalation

    monkeypatch.setattr(get_settings(), "dual_review_enabled", False)
    server_id = await _setup_server(db_session)

    async def fake_generate(db, task_type, system_prompt, user_prompt, max_tokens=1024, temperature=0.7, exclude_providers=None):
        return _routed("anthropic", "Confident diagnosis.")

    monkeypatch.setattr(ModelRouter, "generate", fake_generate)

    async with db_session() as db:
        result = await draft_postmortem(db, server_id)
        assert result["escalated"] is False
        await db.commit()

    async with db_session() as db:
        escalations = list((await db.execute(
            select(StaffEscalation).where(StaffEscalation.source == "operational")
        )).scalars().all())
        assert escalations == []
