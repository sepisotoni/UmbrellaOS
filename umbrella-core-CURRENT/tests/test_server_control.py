"""
tests/test_server_control.py — Tests for POST /api/v1/server/control.

[PLUGIN] subsystem audit: the "power" action treated a missing `enabled`
field identically to enabled=False, so a request that simply omitted
`enabled` would silently issue a stop command — no test coverage existed
before this fix. First tests this endpoint has ever had.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

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


@pytest.mark.asyncio
async def test_configured_process_timeout_is_reaped(monkeypatch):
    """Timeout must terminate AND wait for the child rather than orphan it."""
    import asyncio
    from unittest.mock import AsyncMock
    import services.server_control_service as ctrl

    async def lookup(db, key):
        return "fake-command" if key.endswith("_cmd") else None

    class Process:
        returncode = None
        kill_called = False
        wait_called = False

        async def communicate(self):
            await asyncio.sleep(2.0)

        def kill(self):
            self.kill_called = True
            self.returncode = -9

        async def wait(self):
            self.wait_called = True
            return -9

    proc = Process()
    monkeypatch.setattr(ctrl.SettingsService, "get_value", lookup)
    monkeypatch.setattr(ctrl, "COMMAND_TIMEOUT_SEC", 0.001)
    monkeypatch.setattr(
        ctrl.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)
    )

    with pytest.raises(ctrl.ServerControlError) as raised:
        await ctrl._run_configured_command(AsyncMock(spec=AsyncSession), "server.control.restart_cmd")
    assert raised.value.status_code == 504
    assert proc.kill_called
    assert proc.wait_called


@pytest.mark.asyncio
async def test_configured_process_is_reaped_on_request_cancellation(monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock
    import services.server_control_service as ctrl

    entered = asyncio.Event()

    async def lookup(db, key):
        return "fake-command" if key.endswith("_cmd") else None

    class Process:
        returncode = None
        kill_called = False
        wait_called = False

        async def communicate(self):
            entered.set()
            await asyncio.Event().wait()

        def kill(self):
            self.kill_called = True
            self.returncode = -9

        async def wait(self):
            self.wait_called = True

    proc = Process()
    monkeypatch.setattr(ctrl.SettingsService, "get_value", lookup)
    monkeypatch.setattr(
        ctrl.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)
    )
    task = asyncio.create_task(
        ctrl._run_configured_command(AsyncMock(spec=AsyncSession), "server.control.restart_cmd")
    )
    await asyncio.wait_for(entered.wait(), timeout=2.0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert proc.kill_called
    assert proc.wait_called


@pytest.mark.asyncio
async def test_missing_configured_command_returns_control_error(monkeypatch):
    from unittest.mock import AsyncMock
    import services.server_control_service as ctrl

    async def lookup(db, key):
        return "nonexistent-command" if key.endswith("_cmd") else None

    monkeypatch.setattr(ctrl.SettingsService, "get_value", lookup)
    monkeypatch.setattr(
        ctrl.asyncio, "create_subprocess_exec",
        AsyncMock(side_effect=FileNotFoundError("not found")),
    )
    with pytest.raises(ctrl.ServerControlError) as raised:
        await ctrl._run_configured_command(AsyncMock(spec=AsyncSession), "server.control.restart_cmd")
    assert raised.value.status_code == 503
