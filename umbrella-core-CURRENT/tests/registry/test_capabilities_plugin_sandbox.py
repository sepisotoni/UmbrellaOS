"""
tests/registry/test_capabilities_plugin_sandbox.py — REST integration
tests for Phase 8 completion's plugin.sandbox.* capabilities
(capabilities/plugin_sandbox.py), exercised through the real REST
adapter/registry/database, same style as test_capabilities_system.py.

Data setup here seeds PluginExecutionRecord rows directly via db_session
rather than running real sandboxed executions — this file is about the
capabilities' own query/permission/pagination logic, not sandbox
execution semantics (that's tests/registry/test_plugin_execution_telemetry.py's
job, which exercises real forked-process telemetry end to end).
"""
from datetime import datetime, timedelta, timezone

import pytest

from models.plugin_execution import PluginExecutionRecord
from tests.registry.conftest import session_headers_for_role


async def _seed(db_session, **overrides) -> None:
    defaults = dict(
        plugin_id="demo-plugin",
        entrypoint="main:handle",
        actor_id="user-1",
        outcome="success",
        wall_time_ms=12.5,
        cpu_time_ms=4.0,
        peak_memory_bytes=8_000_000,
        error_detail=None,
    )
    defaults.update(overrides)
    async with db_session() as db:
        db.add(PluginExecutionRecord(**defaults))
        await db.commit()


# --------------------------------------------------------------------------
# plugin.sandbox.execution_history
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execution_history_denied_without_permission(client, db_session):
    # 'member' role has no plugin.sandbox.view permission (see DEFAULT_ROLES).
    headers = await session_headers_for_role(db_session, "member")
    response = await client.post(
        "/api/v1/capabilities/plugin.sandbox.execution_history/invoke",
        json={},
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_execution_history_lists_most_recent_first(client, db_session):
    headers = await session_headers_for_role(db_session, "owner")
    await _seed(db_session, entrypoint="main:one")
    await _seed(db_session, entrypoint="main:two")

    response = await client.post(
        "/api/v1/capabilities/plugin.sandbox.execution_history/invoke",
        json={"limit": 5, "offset": 0},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 5
    assert body["offset"] == 0
    assert body["total"] == 2
    assert len(body["entries"]) == 2
    # Most recent (second seeded) first.
    assert body["entries"][0]["entrypoint"] == "main:two"
    assert body["entries"][1]["entrypoint"] == "main:one"
    # List view omits error_detail entirely (Task B's job).
    assert "error_detail" not in body["entries"][0]


@pytest.mark.asyncio
async def test_execution_history_filters_by_plugin_id_and_outcome(client, db_session):
    headers = await session_headers_for_role(db_session, "owner")
    await _seed(db_session, plugin_id="plugin-a", outcome="success")
    await _seed(db_session, plugin_id="plugin-a", outcome="error", error_detail="boom")
    await _seed(db_session, plugin_id="plugin-b", outcome="success")

    response = await client.post(
        "/api/v1/capabilities/plugin.sandbox.execution_history/invoke",
        json={"plugin_id": "plugin-a", "outcome": "error"},
        headers=headers,
    )
    body = response.json()
    assert body["total"] == 1
    assert body["entries"][0]["plugin_id"] == "plugin-a"
    assert body["entries"][0]["outcome"] == "error"


@pytest.mark.asyncio
async def test_execution_history_rejects_out_of_range_limit(client, db_session):
    headers = await session_headers_for_role(db_session, "owner")
    response = await client.post(
        "/api/v1/capabilities/plugin.sandbox.execution_history/invoke",
        json={"limit": 999},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


# --------------------------------------------------------------------------
# plugin.sandbox.execution_detail
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execution_detail_includes_error_detail(client, db_session):
    headers = await session_headers_for_role(db_session, "owner")
    await _seed(db_session, outcome="error", error_detail="ValueError: boom")

    async with db_session() as db:
        from sqlalchemy import select

        row = (await db.execute(select(PluginExecutionRecord))).scalar_one()
        execution_id = row.id

    response = await client.post(
        "/api/v1/capabilities/plugin.sandbox.execution_detail/invoke",
        json={"execution_id": execution_id},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == execution_id
    assert body["error_detail"] == "ValueError: boom"


@pytest.mark.asyncio
async def test_execution_detail_unknown_id_returns_404(client, db_session):
    headers = await session_headers_for_role(db_session, "owner")
    response = await client.post(
        "/api/v1/capabilities/plugin.sandbox.execution_detail/invoke",
        json={"execution_id": "does-not-exist"},
        headers=headers,
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------
# plugin.sandbox.profile
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_profile_aggregates_per_plugin(client, db_session):
    headers = await session_headers_for_role(db_session, "owner")
    await _seed(db_session, plugin_id="plugin-a", wall_time_ms=10.0, peak_memory_bytes=1_000_000, outcome="success")
    await _seed(db_session, plugin_id="plugin-a", wall_time_ms=20.0, peak_memory_bytes=3_000_000, outcome="error", error_detail="x")
    await _seed(db_session, plugin_id="plugin-b", wall_time_ms=5.0, peak_memory_bytes=2_000_000, outcome="success")

    response = await client.post(
        "/api/v1/capabilities/plugin.sandbox.profile/invoke",
        json={},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    by_plugin = {entry["plugin_id"]: entry for entry in body}

    plugin_a = by_plugin["plugin-a"]
    assert plugin_a["execution_count"] == 2
    assert plugin_a["avg_wall_time_ms"] == pytest.approx(15.0)
    assert plugin_a["avg_peak_memory_bytes"] == pytest.approx(2_000_000)
    assert plugin_a["error_rate"] == pytest.approx(0.5)

    plugin_b = by_plugin["plugin-b"]
    assert plugin_b["execution_count"] == 1
    assert plugin_b["error_rate"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_profile_excludes_rows_outside_the_window(client, db_session):
    headers = await session_headers_for_role(db_session, "owner")
    await _seed(db_session, plugin_id="plugin-old")

    # Backdate the seeded row's created_at to well outside the default 24h
    # window, so this test actually exercises the window filter rather
    # than relying on wall-clock timing during the test run.
    async with db_session() as db:
        from sqlalchemy import select

        row = (await db.execute(select(PluginExecutionRecord))).scalar_one()
        row.created_at = datetime.now(timezone.utc) - timedelta(hours=48)
        db.add(row)
        await db.commit()

    response = await client.post(
        "/api/v1/capabilities/plugin.sandbox.profile/invoke",
        json={"window_hours": 24},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_profile_can_scope_to_one_plugin(client, db_session):
    headers = await session_headers_for_role(db_session, "owner")
    await _seed(db_session, plugin_id="plugin-a")
    await _seed(db_session, plugin_id="plugin-b")

    response = await client.post(
        "/api/v1/capabilities/plugin.sandbox.profile/invoke",
        json={"plugin_id": "plugin-a"},
        headers=headers,
    )
    body = response.json()
    assert len(body) == 1
    assert body[0]["plugin_id"] == "plugin-a"


# --------------------------------------------------------------------------
# plugin.sandbox.limits
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_limits_reports_the_real_configured_sandbox_limits(client, db_session):
    headers = await session_headers_for_role(db_session, "owner")

    from services.plugins.runtime import plugin_sandbox

    expected = plugin_sandbox.limits

    response = await client.post(
        "/api/v1/capabilities/plugin.sandbox.limits/invoke",
        json={},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cpu_seconds"] == expected.cpu_seconds
    assert body["memory_bytes"] == expected.memory_bytes
    assert body["wall_timeout_seconds"] == expected.wall_timeout_seconds


@pytest.mark.asyncio
async def test_limits_denied_without_permission(client, db_session):
    headers = await session_headers_for_role(db_session, "member")
    response = await client.post(
        "/api/v1/capabilities/plugin.sandbox.limits/invoke",
        json={},
        headers=headers,
    )
    assert response.status_code == 403
