"""
tests/test_settings.py — Tests for settings endpoints.

GET  /api/v1/settings
GET  /api/v1/settings/{key}
PATCH /api/v1/settings/{key}
"""
import pytest
from tests.conftest import ADMIN_HEADERS


@pytest.mark.asyncio
async def test_list_settings_returns_list(client):
    response = await client.get("/api/v1/settings", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_list_settings_has_expected_keys(client):
    response = await client.get("/api/v1/settings", headers=ADMIN_HEADERS)
    first = response.json()[0]
    for field in ("id", "key", "value", "category", "description", "sensitive", "requires_restart"):
        assert field in first


@pytest.mark.asyncio
async def test_get_setting_by_key(client):
    response = await client.get("/api/v1/settings/server.name", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "server.name"


@pytest.mark.asyncio
async def test_get_setting_not_found(client):
    response = await client.get("/api/v1/settings/does.not.exist", headers=ADMIN_HEADERS)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_sensitive_settings_are_masked(client):
    """discord.bot_token is sensitive — value must come back as '***'."""
    response = await client.get("/api/v1/settings/discord.bot_token", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert response.json()["value"] == "***"


@pytest.mark.asyncio
async def test_non_sensitive_settings_not_masked(client):
    response = await client.get("/api/v1/settings/server.name", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    # Value should be the seeded default, not masked
    assert response.json()["value"] != "***"


@pytest.mark.asyncio
async def test_patch_setting_updates_value(client):
    payload = {"value": "MyTestServer"}
    response = await client.patch(
        "/api/v1/settings/server.name", json=payload, headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    assert response.json()["value"] == "MyTestServer"


@pytest.mark.asyncio
async def test_patch_setting_persists(client):
    """After PATCH, GET should return the new value."""
    await client.patch(
        "/api/v1/settings/server.name",
        json={"value": "PersistTest"},
        headers=ADMIN_HEADERS,
    )
    response = await client.get("/api/v1/settings/server.name", headers=ADMIN_HEADERS)
    assert response.json()["value"] == "PersistTest"


@pytest.mark.asyncio
async def test_patch_setting_not_found(client):
    response = await client.patch(
        "/api/v1/settings/fake.key",
        json={"value": "x"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_sensitive_setting_returns_masked(client):
    """Patching a sensitive key must still return masked value in response."""
    response = await client.patch(
        "/api/v1/settings/discord.bot_token",
        json={"value": "real-token-123"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["value"] == "***"
