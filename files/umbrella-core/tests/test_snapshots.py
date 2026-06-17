"""
tests/test_snapshots.py — Snapshot API tests.

Tests for the snapshot system endpoints.
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import PlayerSnapshot, ReplaySession
from database import AsyncSessionLocal


@pytest.mark.asyncio
async def test_post_snapshots_with_full_payload_returns_201(client: AsyncClient):
    """POST /snapshots with full payload returns 201 with id."""
    payload = {
        "minecraft_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "trigger": "incident",
        "health": 20.0,
        "food": 18,
        "xp": 5.5,
        "inventory": {"item": "diamond_sword"},
        "armor": {"helmet": "diamond_helmet"},
        "offhand": {"item": "shield"},
        "x": 100.0,
        "y": 64.0,
        "z": 200.0,
        "yaw": 90.0,
        "pitch": 45.0,
        "world": "world",
        "dimension": "overworld",
    }
    response = await client.post(
        "/api/v1/snapshots",
        json=payload,
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["minecraft_uuid"] == payload["minecraft_uuid"]
    assert data["trigger"] == payload["trigger"]
    assert data["health"] == payload["health"]
    assert data["food"] == payload["food"]
    assert data["xp"] == payload["xp"]
    assert data["x"] == payload["x"]
    assert data["y"] == payload["y"]
    assert data["z"] == payload["z"]
    assert data["world"] == payload["world"]
    assert data["dimension"] == payload["dimension"]


@pytest.mark.asyncio
async def test_post_snapshots_with_only_required_fields_returns_201(client: AsyncClient):
    """POST /snapshots with only required fields (minecraft_uuid) returns 201."""
    payload = {"minecraft_uuid": "550e8400-e29b-41d4-a716-446655440000"}
    response = await client.post(
        "/api/v1/snapshots",
        json=payload,
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["minecraft_uuid"] == payload["minecraft_uuid"]
    assert data["trigger"] == "scheduled"  # default


@pytest.mark.asyncio
async def test_post_snapshots_with_invalid_trigger_returns_422(client: AsyncClient):
    """POST /snapshots with invalid trigger returns 422."""
    payload = {
        "minecraft_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "trigger": "invalid_trigger",
    }
    response = await client.post(
        "/api/v1/snapshots",
        json=payload,
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_snapshots_without_admin_key_returns_401(client: AsyncClient):
    """POST /snapshots without X-Admin-Key returns 401."""
    payload = {"minecraft_uuid": "550e8400-e29b-41d4-a716-446655440000"}
    response = await client.post("/api/v1/snapshots", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_snapshots_players_uuid_returns_list_newest_first(client: AsyncClient):
    """GET /snapshots/players/{uuid} returns list of snapshots newest first."""
    uuid = "550e8400-e29b-41d4-a716-446655440000"
    
    # Create three snapshots with different timestamps
    now = datetime.utcnow()
    for i in range(3):
        payload = {
            "minecraft_uuid": uuid,
            "trigger": "scheduled",
            "timestamp": (now - timedelta(minutes=i)).isoformat(),
        }
        await client.post(
            "/api/v1/snapshots",
            json=payload,
            headers={"X-Admin-Key": "test-secret-key"},
        )
    
    response = await client.get(
        f"/api/v1/snapshots/players/{uuid}",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Verify newest first (most recent timestamp should be first)
    timestamps = [s["timestamp"] for s in data]
    assert timestamps == sorted(timestamps, reverse=True)


@pytest.mark.asyncio
async def test_get_snapshots_players_uuid_with_trigger_filter_filters_correctly(client: AsyncClient):
    """GET /snapshots/players/{uuid}?trigger=incident filters correctly."""
    uuid = "550e8400-e29b-41d4-a716-446655440000"
    
    # Create snapshots with different triggers
    for trigger in ["scheduled", "incident", "quit"]:
        payload = {"minecraft_uuid": uuid, "trigger": trigger}
        await client.post(
            "/api/v1/snapshots",
            json=payload,
            headers={"X-Admin-Key": "test-secret-key"},
        )
    
    response = await client.get(
        f"/api/v1/snapshots/players/{uuid}?trigger=incident",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["trigger"] == "incident"


@pytest.mark.asyncio
async def test_get_snapshots_players_uuid_latest_returns_most_recent(client: AsyncClient):
    """GET /snapshots/players/{uuid}/latest returns the most recent snapshot."""
    uuid = "550e8400-e29b-41d4-a716-446655440000"
    
    # Create two snapshots
    now = datetime.utcnow()
    payload1 = {
        "minecraft_uuid": uuid,
        "trigger": "scheduled",
        "timestamp": (now - timedelta(minutes=5)).isoformat(),
    }
    payload2 = {
        "minecraft_uuid": uuid,
        "trigger": "incident",
        "timestamp": (now - timedelta(minutes=1)).isoformat(),
    }
    await client.post(
        "/api/v1/snapshots",
        json=payload1,
        headers={"X-Admin-Key": "test-secret-key"},
    )
    await client.post(
        "/api/v1/snapshots",
        json=payload2,
        headers={"X-Admin-Key": "test-secret-key"},
    )
    
    response = await client.get(
        f"/api/v1/snapshots/players/{uuid}/latest",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["trigger"] == "incident"  # most recent


@pytest.mark.asyncio
async def test_get_snapshots_players_unknown_uuid_latest_returns_404(client: AsyncClient):
    """GET /snapshots/players/{unknown_uuid}/latest returns 404."""
    response = await client.get(
        "/api/v1/snapshots/players/00000000-0000-0000-0000-000000000000/latest",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_snapshots_id_returns_snapshot_dict(client: AsyncClient):
    """GET /snapshots/{id} returns snapshot dict."""
    payload = {
        "minecraft_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "health": 20.0,
        "food": 18,
    }
    create_response = await client.post(
        "/api/v1/snapshots",
        json=payload,
        headers={"X-Admin-Key": "test-secret-key"},
    )
    snapshot_id = create_response.json()["id"]
    
    response = await client.get(
        f"/api/v1/snapshots/{snapshot_id}",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == snapshot_id
    assert data["health"] == 20.0
    assert data["food"] == 18


@pytest.mark.asyncio
async def test_get_snapshots_nonexistent_id_returns_404(client: AsyncClient):
    """GET /snapshots/{nonexistent_id} returns 404."""
    response = await client.get(
        "/api/v1/snapshots/00000000-0000-0000-0000-000000000000",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_snapshots_replay_replay_id_returns_snapshots_within_window(client: AsyncClient, db_session):
    """GET /snapshots/replay/{replay_id} returns snapshots within time window."""
    async with db_session() as db:
        # Create a replay session
        incident_at = datetime.utcnow()
        replay = ReplaySession(
            trigger="ban",
            triggered_by="staff",
            minecraft_uuid="550e8400-e29b-41d4-a716-446655440000",
            started_at=incident_at - timedelta(minutes=5),
            incident_at=incident_at,
        )
        db.add(replay)
        await db.commit()
        await db.refresh(replay)
        
        # Create snapshots within the window
        for offset in [-5, 0, 5]:  # minutes from incident_at
            snapshot = PlayerSnapshot(
                minecraft_uuid="550e8400-e29b-41d4-a716-446655440000",
                timestamp=incident_at + timedelta(minutes=offset),
                trigger="scheduled",
            )
            db.add(snapshot)
        
        # Create snapshot outside the window
        snapshot_outside = PlayerSnapshot(
            minecraft_uuid="550e8400-e29b-41d4-a716-446655440000",
            timestamp=incident_at + timedelta(minutes=15),
            trigger="scheduled",
        )
        db.add(snapshot_outside)
        await db.commit()
    
    response = await client.get(
        f"/api/v1/snapshots/replay/{replay.id}",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3  # only snapshots within 10-minute window


@pytest.mark.asyncio
async def test_post_snapshots_with_replay_id_links_to_replay_session(client: AsyncClient, db_session):
    """POST /snapshots with replay_id links snapshot to that replay session."""
    async with db_session() as db:
        # Create a replay session
        replay = ReplaySession(
            trigger="ban",
            triggered_by="staff",
            minecraft_uuid="550e8400-e29b-41d4-a716-446655440000",
            started_at=datetime.utcnow() - timedelta(minutes=5),
            incident_at=datetime.utcnow(),
        )
        db.add(replay)
        await db.commit()
        await db.refresh(replay)
    
    payload = {
        "minecraft_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "replay_id": replay.id,
    }
    response = await client.post(
        "/api/v1/snapshots",
        json=payload,
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["replay_id"] == replay.id
    
    # Verify in database
    async with db_session() as db:
        result = await db.execute(
            select(PlayerSnapshot).where(PlayerSnapshot.id == data["id"])
        )
        snapshot = result.scalar_one()
        assert snapshot.replay_id == replay.id


@pytest.mark.asyncio
async def test_multiple_snapshots_for_same_player_returned_newest_first(client: AsyncClient):
    """Multiple snapshots for same player are returned newest first."""
    uuid = "550e8400-e29b-41d4-a716-446655440000"
    
    # Create multiple snapshots
    now = datetime.utcnow()
    for i in range(5):
        payload = {
            "minecraft_uuid": uuid,
            "trigger": "scheduled",
            "timestamp": (now - timedelta(hours=i)).isoformat(),
        }
        await client.post(
            "/api/v1/snapshots",
            json=payload,
            headers={"X-Admin-Key": "test-secret-key"},
        )
    
    response = await client.get(
        f"/api/v1/snapshots/players/{uuid}",
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    # Verify newest first
    timestamps = [s["timestamp"] for s in data]
    assert timestamps == sorted(timestamps, reverse=True)
