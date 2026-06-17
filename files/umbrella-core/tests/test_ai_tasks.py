"""
tests/test_ai_tasks.py — AI moderation task API tests.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from models import AITask, Player, Setting
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_post_ai_review_player_creates_task(client: AsyncClient, db_session):
    """POST /ai/review/player/{uuid} creates AITask."""
    # First, set up the Anthropic API key in settings
    async with db_session() as db:
        existing = await db.scalar(select(Setting).where(Setting.key == "ai.anthropic_api_key"))
        if existing:
            existing.value = "test-key"
        else:
            setting = Setting(key="ai.anthropic_api_key", value="test-key", category="ai", description="Test", sensitive=False, requires_restart=False)
            db.add(setting)
        await db.commit()
    
    # Create a player
    async with db_session() as db:
        player = Player(
            uuid="00000000-0000-0000-0000-000000000001",
            username="TestPlayer",
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
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
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48),
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
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48),
            ai_summary="Test summary 1",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
        )
        task2 = AITask(
            task_type="appeal_review",
            status="approved",
            player_uuid="00000000-0000-0000-0000-000000000002",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48),
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
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_get_ai_tasks_status_pending_filters_correctly(client: AsyncClient, db_session):
    """GET /ai/tasks?status=pending filters correctly."""
    # Create AI tasks with different statuses
    async with db_session() as db:
        task1 = AITask(
            task_type="moderation_review",
            status="pending",
            player_uuid="00000000-0000-0000-0000-000000000001",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48),
            ai_summary="Test summary 1",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
        )
        task2 = AITask(
            task_type="appeal_review",
            status="approved",
            player_uuid="00000000-0000-0000-0000-000000000002",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48),
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
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48),
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
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48),
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
        json={"action_taken": "Banned for 7 days", "reviewed_by": "staff123"},
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["reviewed_by"] == "staff123"
    assert data["action_taken"] == "Banned for 7 days"


@pytest.mark.asyncio
async def test_post_ai_tasks_id_deny_updates_status(client: AsyncClient, db_session):
    """POST /ai/tasks/{id}/deny updates status."""
    # Create a pending AI task
    async with db_session() as db:
        task = AITask(
            task_type="moderation_review",
            status="pending",
            player_uuid="00000000-0000-0000-0000-000000000001",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48),
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
        json={"reviewed_by": "staff123", "reason": "False positive"},
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "denied"
    assert data["reviewed_by"] == "staff123"


@pytest.mark.asyncio
async def test_approved_task_cannot_be_approved_again(client: AsyncClient, db_session):
    """Approved task cannot be approved again (400)."""
    # Create an approved AI task
    async with db_session() as db:
        task = AITask(
            task_type="moderation_review",
            status="approved",
            player_uuid="00000000-0000-0000-0000-000000000001",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48),
            ai_summary="Test summary",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
            reviewed_by="staff123",
            reviewed_at=datetime.utcnow(),
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
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48),
            ai_summary="Test summary",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
            reviewed_by="staff123",
            reviewed_at=datetime.utcnow(),
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
        existing = await db.scalar(select(Setting).where(Setting.key == "ai.anthropic_api_key"))
        if existing:
            existing.value = "test-key"
        else:
            setting = Setting(key="ai.anthropic_api_key", value="test-key", category="ai", description="Test", sensitive=False, requires_restart=False)
            db.add(setting)
        await db.commit()
    
    # Create a player and appeal
    async with db_session() as db:
        player = Player(
            uuid="00000000-0000-0000-0000-000000000002",
            username="TestPlayer2",
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
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
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48),
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
async def test_get_ai_tasks_task_type_filters_correctly(client: AsyncClient, db_session):
    """GET /ai/tasks?task_type filters correctly."""
    # Create AI tasks with different types
    async with db_session() as db:
        task1 = AITask(
            task_type="moderation_review",
            status="pending",
            player_uuid="00000000-0000-0000-0000-000000000001",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48),
            ai_summary="Test summary 1",
            ai_recommendation="ban",
            ai_confidence=0.9,
            evidence='{"test": "data"}',
        )
        task2 = AITask(
            task_type="appeal_review",
            status="pending",
            player_uuid="00000000-0000-0000-0000-000000000002",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48),
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
