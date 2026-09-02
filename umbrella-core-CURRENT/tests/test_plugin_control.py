"""
tests/test_plugin_control.py — Tests for POST /api/v1/plugin/control.

[PLUGIN] subsystem audit: this endpoint previously returned a misleading
200 {"ok": True, "command_id": ...} that implied a real action would
happen, when nothing anywhere in this codebase reads or acts on the
PluginCommand row it writes. Fixed to return 202 with an explicit "note"
field saying so. This is the first test coverage this endpoint has had.
"""
import pytest

from tests.conftest import PLUGIN_HEADERS


@pytest.mark.asyncio
async def test_plugin_control_requires_plugin_key(client):
    response = await client.post(
        "/api/v1/plugin/control",
        json={"plugin_name": "example", "action": "reload"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_plugin_control_returns_honest_pending_status(client):
    """The endpoint still records the command (for whenever a real consumer
    exists) but must not claim it will actually be executed."""
    response = await client.post(
        "/api/v1/plugin/control",
        json={"plugin_name": "example", "action": "reload"},
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 202
    data = response.json()
    assert data["ok"] is True
    assert data["status"] == "pending"
    assert isinstance(data["command_id"], int)
    # The whole point of this fix — must not silently look like success.
    assert "note" in data
    assert "nothing currently polls" in data["note"]


@pytest.mark.asyncio
async def test_plugin_control_rejects_invalid_action(client):
    response = await client.post(
        "/api/v1/plugin/control",
        json={"plugin_name": "example", "action": "not-a-real-action"},
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 422
