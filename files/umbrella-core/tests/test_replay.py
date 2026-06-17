"""
tests/test_replay.py — Tests for replay endpoints.

POST /api/v1/replay/sessions
GET  /api/v1/replay/sessions
GET  /api/v1/replay/sessions/{replay_id}
POST /api/v1/replay/sessions/{replay_id}/events
POST /api/v1/replay/sessions/{replay_id}/finalize
GET  /api/v1/replay/sessions/{replay_id}/events
"""
import pytest
from tests.conftest import ADMIN_HEADERS, WRONG_HEADERS


@pytest.mark.asyncio
async def test_post_replay_sessions_creates_session_returns_201(client):
    """POST /replay/sessions creates session and returns 201 with id."""
    payload = {
        "trigger": "ban",
        "triggered_by": "123456789012345678",
        "minecraft_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "incident_at": "2024-01-01T12:00:00Z",
    }
    response = await client.post("/api/v1/replay/sessions", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["trigger"] == "ban"
    assert data["minecraft_uuid"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.mark.asyncio
async def test_post_replay_sessions_with_invalid_trigger_still_creates(client):
    """POST /replay/sessions with invalid trigger still creates (no strict enum on create)."""
    payload = {
        "trigger": "invalid_trigger",
        "triggered_by": "123456789012345678",
        "minecraft_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
        "incident_at": "2024-01-01T12:00:00Z",
    }
    response = await client.post("/api/v1/replay/sessions", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 201
    data = response.json()
    assert data["trigger"] == "invalid_trigger"


@pytest.mark.asyncio
async def test_get_replay_sessions_returns_list(client):
    """GET /replay/sessions returns list."""
    # Create a session first
    payload = {
        "trigger": "mute",
        "triggered_by": "123456789012345678",
        "minecraft_uuid": "cccccccc-dddd-eeee-ffff-aaaaaaaaaaaa",
        "incident_at": "2024-01-01T12:00:00Z",
    }
    await client.post("/api/v1/replay/sessions", json=payload, headers=ADMIN_HEADERS)
    
    response = await client.get("/api/v1/replay/sessions", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_replay_sessions_with_minecraft_uuid_filter(client):
    """GET /replay/sessions?minecraft_uuid=<uuid> filters correctly."""
    uuid = "dddddddd-eeee-ffff-aaaa-bbbbbbbbbbbb"
    
    # Create session for specific player
    payload1 = {
        "trigger": "ban",
        "triggered_by": "123456789012345678",
        "minecraft_uuid": uuid,
        "incident_at": "2024-01-01T12:00:00Z",
    }
    await client.post("/api/v1/replay/sessions", json=payload1, headers=ADMIN_HEADERS)
    
    # Create session for different player
    payload2 = {
        "trigger": "ban",
        "triggered_by": "123456789012345678",
        "minecraft_uuid": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        "incident_at": "2024-01-01T12:00:00Z",
    }
    await client.post("/api/v1/replay/sessions", json=payload2, headers=ADMIN_HEADERS)
    
    response = await client.get(f"/api/v1/replay/sessions?minecraft_uuid={uuid}", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    
    # All returned sessions should be for the specific player
    for session in data:
        assert session["minecraft_uuid"] == uuid


@pytest.mark.asyncio
async def test_get_replay_sessions_id_returns_session_dict(client):
    """GET /replay/sessions/{id} returns session dict."""
    # Create a session
    payload = {
        "trigger": "anticheat",
        "triggered_by": "123456789012345678",
        "minecraft_uuid": "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "incident_at": "2024-01-01T12:00:00Z",
    }
    create_response = await client.post("/api/v1/replay/sessions", json=payload, headers=ADMIN_HEADERS)
    session_id = create_response.json()["id"]
    
    response = await client.get(f"/api/v1/replay/sessions/{session_id}", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["trigger"] == "anticheat"


@pytest.mark.asyncio
async def test_get_replay_sessions_nonexistent_id_returns_404(client):
    """GET /replay/sessions/{nonexistent_id} returns 404."""
    response = await client.get("/api/v1/replay/sessions/nonexistent-id", headers=ADMIN_HEADERS)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_replay_sessions_events_with_valid_events_returns_inserted(client):
    """POST /replay/sessions/{id}/events with valid events returns { inserted: N }."""
    # Create a session
    payload = {
        "trigger": "report",
        "triggered_by": "123456789012345678",
        "minecraft_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "incident_at": "2024-01-01T12:00:00Z",
    }
    create_response = await client.post("/api/v1/replay/sessions", json=payload, headers=ADMIN_HEADERS)
    session_id = create_response.json()["id"]
    
    # Ingest events
    events_payload = {
        "events": [
            {
                "minecraft_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "event_type": "movement",
                "event_data_json": '{"x": 100, "y": 64, "z": 200}',
                "timestamp": "2024-01-01T11:59:00Z",
                "world": "world",
            },
            {
                "minecraft_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "event_type": "combat",
                "event_data_json": '{"damage": 5}',
                "timestamp": "2024-01-01T12:00:00Z",
                "world": "world",
            },
        ]
    }
    response = await client.post(
        f"/api/v1/replay/sessions/{session_id}/events",
        json=events_payload,
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert "inserted" in data
    assert data["inserted"] == 2


@pytest.mark.asyncio
async def test_post_replay_sessions_events_increments_event_count(client):
    """POST /replay/sessions/{id}/events increments event_count on the session."""
    # Create a session
    payload = {
        "trigger": "manual",
        "triggered_by": "123456789012345678",
        "minecraft_uuid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "incident_at": "2024-01-01T12:00:00Z",
    }
    create_response = await client.post("/api/v1/replay/sessions", json=payload, headers=ADMIN_HEADERS)
    session_id = create_response.json()["id"]
    
    # Get initial event count
    session_response = await client.get(f"/api/v1/replay/sessions/{session_id}", headers=ADMIN_HEADERS)
    initial_count = session_response.json()["event_count"]
    
    # Ingest events
    events_payload = {
        "events": [
            {
                "minecraft_uuid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "event_type": "movement",
                "event_data_json": '{"x": 100, "y": 64, "z": 200}',
                "timestamp": "2024-01-01T11:59:00Z",
            },
        ]
    }
    await client.post(
        f"/api/v1/replay/sessions/{session_id}/events",
        json=events_payload,
        headers=ADMIN_HEADERS,
    )
    
    # Get updated event count
    updated_session_response = await client.get(f"/api/v1/replay/sessions/{session_id}", headers=ADMIN_HEADERS)
    updated_count = updated_session_response.json()["event_count"]
    
    # Event count should have increased
    assert updated_count > initial_count


@pytest.mark.asyncio
async def test_post_replay_sessions_events_with_invalid_event_type_skips(client):
    """POST /replay/sessions/{id}/events with invalid event_type entries skips them."""
    # Create a session
    payload = {
        "trigger": "ban",
        "triggered_by": "123456789012345678",
        "minecraft_uuid": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "incident_at": "2024-01-01T12:00:00Z",
    }
    create_response = await client.post("/api/v1/replay/sessions", json=payload, headers=ADMIN_HEADERS)
    session_id = create_response.json()["id"]
    
    # Ingest events with invalid event type
    events_payload = {
        "events": [
            {
                "minecraft_uuid": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "event_type": "movement",
                "event_data_json": '{"x": 100, "y": 64, "z": 200}',
                "timestamp": "2024-01-01T11:59:00Z",
            },
            {
                "minecraft_uuid": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "event_type": "invalid_type",
                "event_data_json": '{"data": "test"}',
                "timestamp": "2024-01-01T12:00:00Z",
            },
        ]
    }
    response = await client.post(
        f"/api/v1/replay/sessions/{session_id}/events",
        json=events_payload,
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    # Only the valid event should be inserted
    assert data["inserted"] == 1


@pytest.mark.asyncio
async def test_get_replay_sessions_events_returns_events_ordered_by_timestamp_asc(client):
    """GET /replay/sessions/{id}/events returns events ordered by timestamp ASC."""
    # Create a session
    payload = {
        "trigger": "ban",
        "triggered_by": "123456789012345678",
        "minecraft_uuid": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "incident_at": "2024-01-01T12:00:00Z",
    }
    create_response = await client.post("/api/v1/replay/sessions", json=payload, headers=ADMIN_HEADERS)
    session_id = create_response.json()["id"]
    
    # Ingest events in reverse timestamp order
    events_payload = {
        "events": [
            {
                "minecraft_uuid": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "event_type": "movement",
                "event_data_json": '{"x": 200}',
                "timestamp": "2024-01-01T12:00:02Z",
            },
            {
                "minecraft_uuid": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "event_type": "movement",
                "event_data_json": '{"x": 100}',
                "timestamp": "2024-01-01T12:00:00Z",
            },
            {
                "minecraft_uuid": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "event_type": "movement",
                "event_data_json": '{"x": 150}',
                "timestamp": "2024-01-01T12:00:01Z",
            },
        ]
    }
    await client.post(
        f"/api/v1/replay/sessions/{session_id}/events",
        json=events_payload,
        headers=ADMIN_HEADERS,
    )
    
    response = await client.get(f"/api/v1/replay/sessions/{session_id}/events", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    
    # Events should be ordered by timestamp ASC
    timestamps = [event["timestamp"] for event in data]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_get_replay_sessions_events_with_event_type_filter(client):
    """GET /replay/sessions/{id}/events?event_type=movement filters correctly."""
    # Create a session
    payload = {
        "trigger": "ban",
        "triggered_by": "123456789012345678",
        "minecraft_uuid": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        "incident_at": "2024-01-01T12:00:00Z",
    }
    create_response = await client.post("/api/v1/replay/sessions", json=payload, headers=ADMIN_HEADERS)
    session_id = create_response.json()["id"]
    
    # Ingest events of different types
    events_payload = {
        "events": [
            {
                "minecraft_uuid": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                "event_type": "movement",
                "event_data_json": '{"x": 100}',
                "timestamp": "2024-01-01T11:59:00Z",
            },
            {
                "minecraft_uuid": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                "event_type": "combat",
                "event_data_json": '{"damage": 5}',
                "timestamp": "2024-01-01T12:00:00Z",
            },
        ]
    }
    await client.post(
        f"/api/v1/replay/sessions/{session_id}/events",
        json=events_payload,
        headers=ADMIN_HEADERS,
    )
    
    response = await client.get(
        f"/api/v1/replay/sessions/{session_id}/events?event_type=movement",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    
    # All returned events should be movement type
    for event in data:
        assert event["event_type"] == "movement"


@pytest.mark.asyncio
async def test_post_replay_sessions_finalize_sets_ended_at(client):
    """POST /replay/sessions/{id}/finalize sets ended_at and returns 200."""
    # Create a session
    payload = {
        "trigger": "ban",
        "triggered_by": "123456789012345678",
        "minecraft_uuid": "ffffffff-ffff-ffff-ffff-fffffffffffe",
        "incident_at": "2024-01-01T12:00:00Z",
    }
    create_response = await client.post("/api/v1/replay/sessions", json=payload, headers=ADMIN_HEADERS)
    session_id = create_response.json()["id"]
    
    # Finalize the session
    response = await client.post(
        f"/api/v1/replay/sessions/{session_id}/finalize",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ended_at"] is not None


@pytest.mark.asyncio
async def test_post_replay_sessions_finalize_nonexistent_id_returns_404(client):
    """POST /replay/sessions/{id}/finalize on nonexistent id returns 404."""
    response = await client.post(
        "/api/v1/replay/sessions/nonexistent-id/finalize",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_replay_sessions_without_admin_key_returns_401(client):
    """POST /replay/sessions without X-Admin-Key returns 401."""
    payload = {
        "trigger": "ban",
        "triggered_by": "123456789012345678",
        "minecraft_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "incident_at": "2024-01-01T12:00:00Z",
    }
    response = await client.post("/api/v1/replay/sessions", json=payload)
    assert response.status_code == 401
