"""
tests/test_server_control.py — Tests for POST /api/v1/server/control.

[PLUGIN] subsystem audit: the "power" action treated a missing `enabled`
field identically to enabled=False, so a request that simply omitted
`enabled` would silently issue a stop command — no test coverage existed
before this fix. First tests this endpoint has ever had.
"""
import pytest

from tests.conftest import ADMIN_HEADERS, PLUGIN_HEADERS


@pytest.mark.asyncio
async def test_server_control_requires_permission(client):
    response = await client.post(
        "/api/v1/server/control",
        json={"server_id": "default", "action": "power", "enabled": True},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_server_control_plugin_key_alone_is_not_authorized(client):
    """X-Plugin-Key is not sufficient here — server.control is a real staff
    permission, not a plugin-facing endpoint (unlike plugin.py's routes)."""
    response = await client.post(
        "/api/v1/server/control",
        json={"server_id": "default", "action": "power", "enabled": True},
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_power_action_without_enabled_is_rejected_not_defaulted_to_stop(client):
    """The actual bug this fix addresses: omitting `enabled` for a "power"
    action must fail loudly, not silently behave like enabled=False (which
    would stop a live server on a client bug or a forgotten field)."""
    response = await client.post(
        "/api/v1/server/control",
        json={"server_id": "default", "action": "power"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422
    assert "enabled is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_power_action_with_explicit_enabled_false_is_accepted(client):
    """enabled=False explicitly is a valid, intentional stop request — must
    still be distinguishable from (and behave differently than) omitting
    the field entirely. No command is configured in the test settings, so
    this reaches the "command not configured" 503 rather than actually
    running anything — that's the correct behavior for validating the
    request shape without needing to mock subprocess execution."""
    response = await client.post(
        "/api/v1/server/control",
        json={"server_id": "default", "action": "power", "enabled": False},
        headers=ADMIN_HEADERS,
    )
    # Must NOT be the 422 "enabled is required" error — it reached the
    # command-execution path and failed there instead, for an unrelated
    # reason (no command configured in test settings).
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


@pytest.mark.asyncio
async def test_maintenance_action_toggle_still_works_without_enabled(client):
    """Sanity check that the fix is scoped to "power" only — "maintenance"
    is a genuine toggle-when-omitted design (already correct before this
    fix) and must be unaffected."""
    response = await client.post(
        "/api/v1/server/control",
        json={"server_id": "default", "action": "maintenance"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "maintenance"
    assert isinstance(data["maintenance"], bool)


@pytest.mark.asyncio
async def test_invalid_action_rejected(client):
    response = await client.post(
        "/api/v1/server/control",
        json={"server_id": "default", "action": "not-a-real-action"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422
