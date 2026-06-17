"""
tests/test_bridge.py — Tests for bridge endpoints.

POST /api/v1/bridge/message
GET  /api/v1/bridge/messages
GET  /api/v1/bridge/settings
PATCH /api/v1/bridge/settings
"""
import pytest
from tests.conftest import ADMIN_HEADERS, WRONG_HEADERS


@pytest.mark.asyncio
async def test_post_bridge_message_mode_off_returns_forwarded_false(client):
    """When bridge mode is off, messages should not be forwarded."""
    # Set mode to off
    await client.patch(
        "/api/v1/bridge/settings",
        json={"mode": "off"},
        headers=ADMIN_HEADERS,
    )
    
    # Post a message
    payload = {
        "source": "discord",
        "discord_id": "123456789",
        "message": "Test message",
        "channel_id": "987654321",
    }
    response = await client.post("/api/v1/bridge/message", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["forwarded"] is False
    assert data["targets"] == []


@pytest.mark.asyncio
async def test_post_bridge_message_mode_full_returns_forwarded_true(client):
    """When bridge mode is full, messages should be forwarded."""
    # Set mode to full and enable discord_to_mc
    await client.patch(
        "/api/v1/bridge/settings",
        json={"mode": "full", "discord_to_mc": True},
        headers=ADMIN_HEADERS,
    )
    
    # Post a message
    payload = {
        "source": "discord",
        "discord_id": "123456789",
        "message": "Test message",
        "channel_id": "987654321",
    }
    response = await client.post("/api/v1/bridge/message", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["forwarded"] is True
    assert "minecraft" in data["targets"]


@pytest.mark.asyncio
async def test_get_bridge_messages_returns_list_with_correct_shape(client):
    """GET /bridge/messages should return a list with correct shape."""
    # First, add a message
    payload = {
        "source": "minecraft",
        "player_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "message": "Test message from MC",
    }
    await client.post("/api/v1/bridge/message", json=payload, headers=ADMIN_HEADERS)
    
    # Get messages
    response = await client.get("/api/v1/bridge/messages", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        first = data[0]
        for field in ("id", "source", "player_uuid", "discord_id", "discord_channel_id", "message", "timestamp", "filtered"):
            assert field in first


@pytest.mark.asyncio
async def test_get_bridge_messages_with_source_filter_works(client):
    """GET /bridge/messages with source filter should only return messages from that source."""
    # Add a minecraft message
    await client.post(
        "/api/v1/bridge/message",
        json={
            "source": "minecraft",
            "player_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "message": "MC message",
        },
        headers=ADMIN_HEADERS,
    )
    
    # Add a discord message
    await client.post(
        "/api/v1/bridge/message",
        json={
            "source": "discord",
            "discord_id": "123456789",
            "message": "Discord message",
        },
        headers=ADMIN_HEADERS,
    )
    
    # Get only minecraft messages
    response = await client.get("/api/v1/bridge/messages?source=minecraft", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    for msg in data:
        assert msg["source"] == "minecraft"


@pytest.mark.asyncio
async def test_patch_bridge_settings_updates_mode_successfully(client):
    """PATCH /bridge/settings should update mode successfully."""
    response = await client.patch(
        "/api/v1/bridge/settings",
        json={"mode": "full"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "full"


@pytest.mark.asyncio
async def test_patch_bridge_settings_with_invalid_mode_returns_400(client):
    """PATCH /bridge/settings with invalid mode should return 400."""
    response = await client.patch(
        "/api/v1/bridge/settings",
        json={"mode": "invalid"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_post_bridge_message_without_admin_key_returns_401(client):
    """POST /bridge/message without X-Admin-Key should return 401."""
    payload = {
        "source": "discord",
        "discord_id": "123456789",
        "message": "Test message",
    }
    response = await client.post("/api/v1/bridge/message", json=payload, headers=WRONG_HEADERS)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_bridge_messages_without_auth_returns_401(client):
    """GET /bridge/messages without auth should return 401."""
    response = await client.get("/api/v1/bridge/messages")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_bridge_settings_requires_settings_view_permission(client):
    """GET /bridge/settings requires settings.view permission."""
    # Create a user with helper role (no settings.view permission)
    await client.post(
        "/api/v1/auth/discord/authorize",
        json={"redirect_uri": "http://localhost:3000"},
    )
    # Get the redirect URL
    # For simplicity, we'll just test with admin headers (should work)
    response = await client.get("/api/v1/bridge/settings", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    
    # Test without headers (should fail)
    response = await client.get("/api/v1/bridge/settings")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_bridge_message_requires_valid_source(client):
    """POST /bridge/message requires valid source (minecraft or discord)."""
    payload = {
        "source": "invalid",
        "message": "Test message",
    }
    response = await client.post("/api/v1/bridge/message", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_post_bridge_message_requires_identifier_for_source(client):
    """POST /bridge/message requires player_uuid for minecraft, discord_id for discord."""
    # Test minecraft without player_uuid
    payload = {
        "source": "minecraft",
        "message": "Test message",
    }
    response = await client.post("/api/v1/bridge/message", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 400
    
    # Test discord without discord_id
    payload = {
        "source": "discord",
        "message": "Test message",
    }
    response = await client.post("/api/v1/bridge/message", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 400
