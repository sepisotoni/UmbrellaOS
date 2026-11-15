"""
tests/test_ai_tasks.py — AI moderation task API tests.
"""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from models import AITask, AuditLog, Player, Punishment, Session, Setting, User
from models.permissions import Role
from datetime import datetime, timezone, timedelta


@pytest.mark.asyncio
async def test_post_ai_review_player_creates_task(client: AsyncClient, db_session):
    """POST /ai/review/player/{uuid} creates AITask."""
    # First, set up the Anthropic API key in settings
    async with db_session() as db:
        existing = await db.scalar(
            select(Setting).where(Setting.key == "ai.anthropic_api_key")
        )
        if existing:
            existing.value = "test-key"
        else:
            setting = Setting(
                key="ai.anthropic_api_key",
                value="test-key",
                category="ai",
                description="Test",
                sensitive=False,
                requires_restart=False,
            )
            db.add(setting)
        await db.commit()

    # Create a player
    async with db_session() as db:
        player = Player(
            uuid="00000000-0000-0000-0000-000000000001",
            username="TestPlayer",
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
        )
        db.add(player)
        await db.commit()

    # Mock the AI service call by patching it
    import services.ai_service

    original_review_flagged_player = services.ai_service.review_flagged_player

    async def mock_review_flagged_player(player_uuid, db):
        return AITask(
            task_type="moderation_review",
            status="pending",
            player_uuid=player_uuid,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            ai_summary="Test summary",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
        )

    services.ai_service.review_flagged_player = mock_review_flagged_player

    try:
        response = await client.post(
            "/api/v1/ai/review/player/00000000-0000-0000-0000-000000000001",
            headers={"X-Admin-Key": "test-secret-key"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["task_type"] == "moderation_review"
        assert data["status"] == "pending"
        assert data["player_uuid"] == "00000000-0000-0000-0000-000000000001"
        assert data["ai_summary"] == "Test summary"
        assert data["ai_recommendation"] == "ban"
        assert data["ai_confidence"] == 0.9
    finally:
        services.ai_service.review_flagged_player = original_review_flagged_player


@pytest.mark.asyncio
async def test_get_ai_tasks_returns_list(client: AsyncClient, db_session):
    """GET /ai/tasks returns list."""
    # Create some AI tasks
    async with db_session() as db:
        task1 = AITask(
            task_type="moderation_review",
            status="pending",
            player_uuid="00000000-0000-0000-0000-000000000001",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            ai_summary="Test summary 1",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
        )
        task2 = AITask(
            task_type="appeal_review",
            status="approved",
            player_uuid="00000000-0000-0000-0000-000000000002",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            ai_summary="Test summary 2",
            ai_recommendation="approve",
            ai_confidence=0.8,
            evidence='{"test": "data"}',
        )
        db.add(task1)
        db.add(task2)
        await db.commit()

    response = await client.get(
        "/api/v1/ai/tasks",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_get_ai_tasks_status_pending_filters_correctly(
    client: AsyncClient, db_session
):
    """GET /ai/tasks?status=pending filters correctly."""
    # Create AI tasks with different statuses
    async with db_session() as db:
        task1 = AITask(
            task_type="moderation_review",
            status="pending",
            player_uuid="00000000-0000-0000-0000-000000000001",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            ai_summary="Test summary 1",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
        )
        task2 = AITask(
            task_type="appeal_review",
            status="approved",
            player_uuid="00000000-0000-0000-0000-000000000002",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            ai_summary="Test summary 2",
            ai_recommendation="approve",
            ai_confidence=0.8,
            evidence='{"test": "data"}',
        )
        db.add(task1)
        db.add(task2)
        await db.commit()

    response = await client.get(
        "/api/v1/ai/tasks?status=pending",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(task["status"] == "pending" for task in data)


@pytest.mark.asyncio
async def test_get_ai_task_id_returns_full_task(client: AsyncClient, db_session):
    """GET /ai/tasks/{id} returns full task."""
    # Create an AI task
    async with db_session() as db:
        task = AITask(
            task_type="moderation_review",
            status="pending",
            player_uuid="00000000-0000-0000-0000-000000000001",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            ai_summary="Test summary",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

    response = await client.get(
        f"/api/v1/ai/tasks/{task.id}",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task.id
    assert data["task_type"] == "moderation_review"
    assert data["evidence"] is not None


@pytest.mark.asyncio
async def test_post_ai_tasks_id_approve_updates_status(client: AsyncClient, db_session):
    """POST /ai/tasks/{id}/approve updates status."""
    # Create a pending AI task
    async with db_session() as db:
        task = AITask(
            task_type="moderation_review",
            status="pending",
            player_uuid="00000000-0000-0000-0000-000000000001",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            ai_summary="Test summary",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

    response = await client.post(
        f"/api/v1/ai/tasks/{task.id}/approve",
        json={"action_taken": "Banned for 7 days", "reviewed_by": "forged-staff"},
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["reviewed_by"] == "admin-key"
    assert data["action_taken"] == "Banned for 7 days"
    async with db_session() as db:
        audit = await db.scalar(
            select(AuditLog).where(
                AuditLog.action == "ai_task.approved",
                AuditLog.target == str(task.id),
            )
        )
        assert audit.actor == "admin-key"


@pytest.mark.asyncio
async def test_post_ai_tasks_id_deny_updates_status(client: AsyncClient, db_session):
    """POST /ai/tasks/{id}/deny updates status."""
    # Create a pending AI task
    async with db_session() as db:
        task = AITask(
            task_type="moderation_review",
            status="pending",
            player_uuid="00000000-0000-0000-0000-000000000001",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            ai_summary="Test summary",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

    response = await client.post(
        f"/api/v1/ai/tasks/{task.id}/deny",
        json={"reviewed_by": "forged-staff", "reason": "False positive"},
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "denied"
    assert data["reviewed_by"] == "admin-key"


@pytest.mark.asyncio
async def test_approved_task_cannot_be_approved_again(client: AsyncClient, db_session):
    """Approved task cannot be approved again (400)."""
    # Create an approved AI task
    async with db_session() as db:
        task = AITask(
            task_type="moderation_review",
            status="approved",
            player_uuid="00000000-0000-0000-0000-000000000001",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            ai_summary="Test summary",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
            reviewed_by="staff123",
            reviewed_at=datetime.now(timezone.utc),
            action_taken="Banned",
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

    response = await client.post(
        f"/api/v1/ai/tasks/{task.id}/approve",
        json={"action_taken": "Banned again", "reviewed_by": "staff456"},
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_denied_task_cannot_be_denied_again(client: AsyncClient, db_session):
    """Denied task cannot be denied again (400)."""
    # Create a denied AI task
    async with db_session() as db:
        task = AITask(
            task_type="moderation_review",
            status="denied",
            player_uuid="00000000-0000-0000-0000-000000000001",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            ai_summary="Test summary",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
            reviewed_by="staff123",
            reviewed_at=datetime.now(timezone.utc),
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

    response = await client.post(
        f"/api/v1/ai/tasks/{task.id}/deny",
        json={"reviewed_by": "staff456", "reason": "Another reason"},
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_unauthenticated_requests_return_401(client: AsyncClient):
    """Unauthenticated requests return 401."""
    response = await client.get("/api/v1/ai/tasks")
    assert response.status_code == 401

    response = await client.get("/api/v1/ai/tasks/1")
    assert response.status_code == 401

    response = await client.post("/api/v1/ai/tasks/1/approve", json={})
    assert response.status_code == 401

    response = await client.post("/api/v1/ai/tasks/1/deny", json={})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_ai_review_appeal_creates_task(client: AsyncClient, db_session):
    """POST /ai/review/appeal/{appeal_id} creates AITask."""
    # Set up the Anthropic API key in settings
    async with db_session() as db:
        existing = await db.scalar(
            select(Setting).where(Setting.key == "ai.anthropic_api_key")
        )
        if existing:
            existing.value = "test-key"
        else:
            setting = Setting(
                key="ai.anthropic_api_key",
                value="test-key",
                category="ai",
                description="Test",
                sensitive=False,
                requires_restart=False,
            )
            db.add(setting)
        await db.commit()

    # Create a player and appeal
    async with db_session() as db:
        player = Player(
            uuid="00000000-0000-0000-0000-000000000002",
            username="TestPlayer2",
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
        )
        db.add(player)
        await db.commit()
        await db.refresh(player)

        from models import Punishment

        punishment = Punishment(
            id="appeal-001",
            player_uuid=player.uuid,
            type="ban",
            reason="Test ban",
            active=True,
        )
        db.add(punishment)
        await db.commit()
        await db.refresh(punishment)

        from models import Appeal

        appeal = Appeal(
            id="appeal-001",
            punishment_id=punishment.id,
            player_uuid=player.uuid,
            status="pending",
            message="Please unban me",
        )
        db.add(appeal)
        await db.commit()

    # Mock the AI service call
    import services.ai_service

    original_review_appeal = services.ai_service.review_appeal

    async def mock_review_appeal(appeal_id, db):
        return AITask(
            task_type="appeal_review",
            status="pending",
            player_uuid="00000000-0000-0000-0000-000000000002",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            ai_summary="Appeal summary",
            ai_recommendation="approve",
            ai_confidence=0.85,
            evidence='{"test": "data"}',
        )

    services.ai_service.review_appeal = mock_review_appeal

    try:
        response = await client.post(
            "/api/v1/ai/review/appeal/appeal-001",
            headers={"X-Admin-Key": "test-secret-key"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["task_type"] == "appeal_review"
        assert data["status"] == "pending"
        assert data["ai_summary"] == "Appeal summary"
    finally:
        services.ai_service.review_appeal = original_review_appeal


@pytest.mark.asyncio
async def test_get_ai_tasks_task_type_filters_correctly(
    client: AsyncClient, db_session
):
    """GET /ai/tasks?task_type filters correctly."""
    # Create AI tasks with different types
    async with db_session() as db:
        task1 = AITask(
            task_type="moderation_review",
            status="pending",
            player_uuid="00000000-0000-0000-0000-000000000001",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            ai_summary="Test summary 1",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
        )
        task2 = AITask(
            task_type="appeal_review",
            status="pending",
            player_uuid="00000000-0000-0000-0000-000000000002",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            ai_summary="Test summary 2",
            ai_recommendation="approve",
            ai_confidence=0.8,
            evidence='{"test": "data"}',
        )
        db.add(task1)
        db.add(task2)
        await db.commit()

    response = await client.get(
        "/api/v1/ai/tasks?task_type=moderation_review",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert all(task["task_type"] == "moderation_review" for task in data)


@pytest.mark.asyncio
async def test_get_ai_task_id_returns_404_for_nonexistent(client: AsyncClient):
    """GET /ai/tasks/{id} returns 404 for non-existent task."""
    response = await client.get(
        "/api/v1/ai/tasks/99999",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 404


async def _create_pending_copilot_action(
    db_session, *, expires_at=None, action="tempban", duration_hours=48
):
    async with db_session() as db:
        player = await db.get(Player, "99999999-9999-9999-9999-999999999999")
        if player is None:
            player = Player(
                uuid="99999999-9999-9999-9999-999999999999",
                username="ActionTarget",
            )
            db.add(player)
        action_expiry = (
            datetime.now(timezone.utc) + timedelta(hours=duration_hours)
            if action == "tempban"
            else None
        )
        proposal = {
            "action": action,
            "player_uuid": player.uuid,
            "player_name": player.username,
            "reason": "Repeated cheating",
            "duration_hours": duration_hours if action == "tempban" else None,
            "expires_at": action_expiry.isoformat() if action_expiry else None,
        }
        task = AITask(
            task_type="copilot_moderation_action",
            status="pending",
            player_uuid=player.uuid,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at or datetime.now(timezone.utc) + timedelta(minutes=5),
            ai_summary=f"Copilot proposes {action} for ActionTarget",
            ai_recommendation=action,
            ai_confidence=0.0,
            evidence=json.dumps({"copilot_action": proposal}),
        )
        db.add(task)
        if action == "unban":
            db.add(
                Punishment(
                    player_uuid=player.uuid,
                    type="ban",
                    reason="Previous ban",
                    active=True,
                )
            )
        await db.commit()
        return task.id, player.uuid


async def _copilot_action_headers(db_session, *, role_name="owner"):
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == role_name))
        user = User(
            discord_id=f"copilot-action-{role_name}",
            username=f"CopilotAction{role_name}",
            role_id=role.id,
        )
        db.add(user)
        await db.flush()
        db.add(
            Session(
                user_id=user.id,
                token=f"copilot-action-token-{role_name}",
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        await db.commit()
    return {"Authorization": f"Bearer copilot-action-token-{role_name}"}


@pytest.mark.asyncio
async def test_copilot_action_requires_explicit_confirmation(client, db_session):
    task_id, player_uuid = await _create_pending_copilot_action(db_session)

    response = await client.post(
        f"/api/v1/ai/tasks/{task_id}/execute",
        json={"confirm": False},
        headers={"X-Admin-Key": "test-secret-key"},
    )

    assert response.status_code == 422
    async with db_session() as db:
        task = await db.get(AITask, task_id)
        punishment = await db.scalar(
            select(Punishment).where(Punishment.player_uuid == player_uuid)
        )
        assert task.status == "pending"
        assert punishment is None


@pytest.mark.asyncio
async def test_machine_admin_key_cannot_confirm_copilot_action(client, db_session):
    task_id, player_uuid = await _create_pending_copilot_action(db_session)

    response = await client.post(
        f"/api/v1/ai/tasks/{task_id}/execute",
        json={"confirm": True},
        headers={"X-Admin-Key": "test-secret-key"},
    )

    assert response.status_code == 403
    async with db_session() as db:
        task = await db.get(AITask, task_id)
        punishment = await db.scalar(
            select(Punishment).where(Punishment.player_uuid == player_uuid)
        )
        assert task.status == "pending"
        assert punishment is None


@pytest.mark.asyncio
async def test_copilot_action_cannot_use_legacy_approve_endpoint(client, db_session):
    task_id, player_uuid = await _create_pending_copilot_action(db_session)

    response = await client.post(
        f"/api/v1/ai/tasks/{task_id}/approve",
        json={"action_taken": "approved"},
        headers={"X-Admin-Key": "test-secret-key"},
    )

    assert response.status_code == 409
    async with db_session() as db:
        task = await db.get(AITask, task_id)
        punishment = await db.scalar(
            select(Punishment).where(Punishment.player_uuid == player_uuid)
        )
        assert task.status == "pending"
        assert punishment is None


@pytest.mark.asyncio
async def test_copilot_action_executes_only_after_explicit_confirmation(
    client, db_session
):
    task_id, player_uuid = await _create_pending_copilot_action(db_session)
    owner_headers = await _copilot_action_headers(db_session)

    response = await client.post(
        f"/api/v1/ai/tasks/{task_id}/execute",
        json={"confirm": True},
        headers=owner_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "approved"
    assert response.json()["action"] == "tempban"
    async with db_session() as db:
        task = await db.get(AITask, task_id)
        punishment = await db.scalar(
            select(Punishment).where(Punishment.player_uuid == player_uuid)
        )
        audit = await db.scalar(
            select(AuditLog).where(
                AuditLog.action == "ai_action.executed",
                AuditLog.target == str(task_id),
            )
        )
        assert task.status == "approved"
        assert punishment.type == "tempban"
        assert punishment.active is True
        assert punishment.expires_at is not None
        assert audit is not None


@pytest.mark.asyncio
async def test_copilot_permanent_ban_and_unban_execute_after_confirmation(
    client, db_session
):
    owner_headers = await _copilot_action_headers(db_session)
    task_id, player_uuid = await _create_pending_copilot_action(
        db_session, action="ban"
    )

    ban_response = await client.post(
        f"/api/v1/ai/tasks/{task_id}/execute",
        json={"confirm": True},
        headers=owner_headers,
    )

    assert ban_response.status_code == 200
    async with db_session() as db:
        ban = await db.scalar(select(Punishment).where(Punishment.player_uuid == player_uuid))
        assert ban.type == "ban"
        assert ban.expires_at is None
        assert ban.active is True

    unban_task_id, _ = await _create_pending_copilot_action(
        db_session, action="unban"
    )
    unban_response = await client.post(
        f"/api/v1/ai/tasks/{unban_task_id}/execute",
        json={"confirm": True},
        headers=owner_headers,
    )

    assert unban_response.status_code == 200
    async with db_session() as db:
        bans = list(
            (
                await db.scalars(
                    select(Punishment).where(Punishment.player_uuid == player_uuid)
                )
            ).all()
        )
        assert bans
        assert all(not ban.active and ban.status == "REVOKED" for ban in bans)


@pytest.mark.asyncio
async def test_expired_copilot_action_cannot_execute(client, db_session):
    task_id, player_uuid = await _create_pending_copilot_action(
        db_session, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    owner_headers = await _copilot_action_headers(db_session)

    response = await client.post(
        f"/api/v1/ai/tasks/{task_id}/execute",
        json={"confirm": True},
        headers=owner_headers,
    )

    assert response.status_code == 410
    async with db_session() as db:
        task = await db.get(AITask, task_id)
        punishment = await db.scalar(
            select(Punishment).where(Punishment.player_uuid == player_uuid)
        )
        assert task.status == "expired"
        assert punishment is None


@pytest.mark.asyncio
async def test_copilot_action_requires_live_action_permission(client, db_session):
    task_id, player_uuid = await _create_pending_copilot_action(db_session)
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == "member"))
        user = User(
            discord_id="action-no-permission",
            username="ActionNoPermission",
            role_id=role.id,
        )
        db.add(user)
        await db.flush()
        db.add(
            Session(
                user_id=user.id,
                token="action-no-permission-token",
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        await db.commit()

    response = await client.post(
        f"/api/v1/ai/tasks/{task_id}/execute",
        json={"confirm": True},
        headers={"Authorization": "Bearer action-no-permission-token"},
    )

    assert response.status_code == 403
    async with db_session() as db:
        task = await db.get(AITask, task_id)
        punishment = await db.scalar(
            select(Punishment).where(Punishment.player_uuid == player_uuid)
        )
        assert task.status == "pending"
        assert punishment is None


@pytest.mark.asyncio
async def test_copilot_action_can_be_declined_without_execution(client, db_session):
    task_id, player_uuid = await _create_pending_copilot_action(db_session)
    owner_headers = await _copilot_action_headers(db_session)

    response = await client.post(
        f"/api/v1/ai/tasks/{task_id}/decline",
        headers=owner_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "denied"
    async with db_session() as db:
        task = await db.get(AITask, task_id)
        punishment = await db.scalar(
            select(Punishment).where(Punishment.player_uuid == player_uuid)
        )
        audit = await db.scalar(
            select(AuditLog).where(
                AuditLog.action == "ai_action.declined",
                AuditLog.target == str(task_id),
            )
        )
        assert task.status == "denied"
        assert punishment is None
        assert audit is not None


@pytest.mark.asyncio
async def test_expired_proposals_are_removed_from_pending_task_list(client, db_session):
    task_id, _ = await _create_pending_copilot_action(
        db_session, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
    )

    response = await client.get(
        "/api/v1/ai/tasks?status=pending",
        headers={"X-Admin-Key": "test-secret-key"},
    )

    assert response.status_code == 200
    assert all(task["id"] != task_id for task in response.json())
    async with db_session() as db:
        task = await db.get(AITask, task_id)
        assert task.status == "expired"
