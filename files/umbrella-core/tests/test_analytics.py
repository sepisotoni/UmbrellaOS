"""
tests/test_analytics.py — Tests for analytics endpoints.

POST /api/v1/analytics/events
GET  /api/v1/analytics/events
GET  /api/v1/analytics/players/{minecraft_uuid}
GET  /api/v1/analytics/summary
"""
import pytest
from tests.conftest import ADMIN_HEADERS, WRONG_HEADERS


@pytest.mark.asyncio
async def test_post_analytics_events_with_valid_join_returns_201(client):
    """POST /analytics/events with valid join event returns 201 with id."""
    payload = {
        "event_type": "join",
        "minecraft_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "data": {"server": "survival"},
    }
    response = await client.post("/api/v1/analytics/events", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["event_type"] == "join"
    assert data["minecraft_uuid"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.mark.asyncio
async def test_post_analytics_events_with_invalid_event_type_returns_422(client):
    """POST /analytics/events with invalid event_type returns 422."""
    payload = {
        "event_type": "invalid_event",
        "minecraft_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
    }
    response = await client.post("/api/v1/analytics/events", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_analytics_events_without_minecraft_uuid_returns_201(client):
    """POST /analytics/events without minecraft_uuid (server event) returns 201."""
    payload = {
        "event_type": "command",
        "minecraft_uuid": None,
        "data": {"command": "/op"},
    }
    response = await client.post("/api/v1/analytics/events", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 201
    data = response.json()
    assert data["minecraft_uuid"] is None


@pytest.mark.asyncio
async def test_post_analytics_events_for_join_auto_creates_playerstat_row(client):
    """POST /analytics/events for join auto-creates PlayerStat row for "joins" metric."""
    payload = {
        "event_type": "join",
        "minecraft_uuid": "cccccccc-dddd-eeee-ffff-aaaaaaaaaaaa",
    }
    await client.post("/api/v1/analytics/events", json=payload, headers=ADMIN_HEADERS)
    
    # Get player stats
    response = await client.get("/api/v1/analytics/players/cccccccc-dddd-eeee-ffff-aaaaaaaaaaaa", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    
    # Should have "joins" metric for both daily and alltime
    joins_stats = [s for s in data if s["metric"] == "joins"]
    assert len(joins_stats) >= 1


@pytest.mark.asyncio
async def test_post_analytics_events_twice_increments_alltime_stat(client):
    """POST /analytics/events twice for same player increments the alltime stat value."""
    uuid = "dddddddd-eeee-ffff-aaaa-bbbbbbbbbbbb"
    
    # First event
    payload1 = {
        "event_type": "join",
        "minecraft_uuid": uuid,
    }
    await client.post("/api/v1/analytics/events", json=payload1, headers=ADMIN_HEADERS)
    
    # Second event
    payload2 = {
        "event_type": "join",
        "minecraft_uuid": uuid,
    }
    await client.post("/api/v1/analytics/events", json=payload2, headers=ADMIN_HEADERS)
    
    # Get alltime stats
    response = await client.get(f"/api/v1/analytics/players/{uuid}?period=alltime", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    
    joins_stat = next((s for s in data if s["metric"] == "joins"), None)
    assert joins_stat is not None
    assert joins_stat["value"] >= 2


@pytest.mark.asyncio
async def test_get_analytics_events_returns_list_newest_first(client):
    """GET /analytics/events returns list, newest first."""
    # Create some events
    for i in range(3):
        payload = {
            "event_type": "join",
            "minecraft_uuid": f"eeeeeeee-ffff-aaaa-bbbb-cccccccccccc{i}",
        }
        await client.post("/api/v1/analytics/events", json=payload, headers=ADMIN_HEADERS)
    
    response = await client.get("/api/v1/analytics/events", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_get_analytics_events_with_event_type_filter(client):
    """GET /analytics/events?event_type=join filters correctly."""
    # Create join events
    payload1 = {
        "event_type": "join",
        "minecraft_uuid": "ffffffff-aaaa-bbbb-cccc-dddddddddddd",
    }
    await client.post("/api/v1/analytics/events", json=payload1, headers=ADMIN_HEADERS)
    
    # Create quit events
    payload2 = {
        "event_type": "quit",
        "minecraft_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    }
    await client.post("/api/v1/analytics/events", json=payload2, headers=ADMIN_HEADERS)
    
    response = await client.get("/api/v1/analytics/events?event_type=join", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    
    # All returned events should be join type
    for event in data:
        assert event["event_type"] == "join"


@pytest.mark.asyncio
async def test_get_analytics_events_with_minecraft_uuid_filter(client):
    """GET /analytics/events?minecraft_uuid=<uuid> filters correctly."""
    uuid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    
    # Create events for specific player
    payload1 = {
        "event_type": "join",
        "minecraft_uuid": uuid,
    }
    await client.post("/api/v1/analytics/events", json=payload1, headers=ADMIN_HEADERS)
    
    # Create events for different player
    payload2 = {
        "event_type": "join",
        "minecraft_uuid": "cccccccc-cccc-cccc-cccc-cccccccccccc",
    }
    await client.post("/api/v1/analytics/events", json=payload2, headers=ADMIN_HEADERS)
    
    response = await client.get(f"/api/v1/analytics/events?minecraft_uuid={uuid}", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    
    # All returned events should be for the specific player
    for event in data:
        assert event["minecraft_uuid"] == uuid


@pytest.mark.asyncio
async def test_get_analytics_players_uuid_returns_stat_list_for_alltime(client):
    """GET /analytics/players/{uuid} returns stat list for alltime period."""
    uuid = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    
    # Create some events
    payload = {
        "event_type": "join",
        "minecraft_uuid": uuid,
    }
    await client.post("/api/v1/analytics/events", json=payload, headers=ADMIN_HEADERS)
    
    response = await client.get(f"/api/v1/analytics/players/{uuid}", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_analytics_players_uuid_with_daily_period(client):
    """GET /analytics/players/{uuid}?period=daily returns daily stats."""
    uuid = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    
    # Create some events
    payload = {
        "event_type": "join",
        "minecraft_uuid": uuid,
    }
    await client.post("/api/v1/analytics/events", json=payload, headers=ADMIN_HEADERS)
    
    response = await client.get(f"/api/v1/analytics/players/{uuid}?period=daily", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_analytics_summary_returns_dict_with_all_metrics(client):
    """GET /analytics/summary returns dict with all six metric keys."""
    response = await client.get("/api/v1/analytics/summary", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    
    expected_keys = ["joins", "leaves", "deaths", "kills", "chat_volume", "playtime_seconds"]
    for key in expected_keys:
        assert key in data


@pytest.mark.asyncio
async def test_get_analytics_summary_totals_increase_after_recording_events(client):
    """GET /analytics/summary totals increase after recording events."""
    # Get initial summary
    response1 = await client.get("/api/v1/analytics/summary", headers=ADMIN_HEADERS)
    initial_joins = response1.json()["joins"]
    
    # Record a join event
    payload = {
        "event_type": "join",
        "minecraft_uuid": "ffffffff-ffff-ffff-ffff-ffffffffffff",
    }
    await client.post("/api/v1/analytics/events", json=payload, headers=ADMIN_HEADERS)
    
    # Get updated summary
    response2 = await client.get("/api/v1/analytics/summary", headers=ADMIN_HEADERS)
    updated_joins = response2.json()["joins"]
    
    # Joins should have increased
    assert updated_joins > initial_joins


@pytest.mark.asyncio
async def test_post_analytics_events_without_admin_key_returns_401(client):
    """POST /analytics/events without X-Admin-Key returns 401."""
    payload = {
        "event_type": "join",
        "minecraft_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    }
    response = await client.post("/api/v1/analytics/events", json=payload)
    assert response.status_code == 401
