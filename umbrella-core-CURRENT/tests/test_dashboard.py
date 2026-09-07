"""
tests/test_dashboard.py — Tests for api/routers/dashboard.py.

[PLUGIN] subsystem audit: GET /api/v1/dashboard/plugins previously returned
a flat list of independent rows with no umbrella_status/grimac_status
fields at all, while the dashboard's api.ts/PluginsView.tsx already
expected one combined object per server with both as sibling fields
(checked against the literal string 'ACTIVE'). No test coverage existed
for this endpoint before this fix.
"""
from datetime import datetime, timedelta, timezone

import pytest

from models.plugin_heartbeat import PluginHeartbeat
from tests.conftest import ADMIN_HEADERS


async def _seed_heartbeat(
    db_session,
    server_id: str,
    grim_connected: bool = False,
    last_seen: datetime | None = None,
    plugin_version: str = "1.2.3",
) -> None:
    async with db_session() as db:
        db.add(PluginHeartbeat(
            server_id=server_id,
            server_name=f"Server {server_id}",
            online_count=5,
            tps=19.8,
            version="1.21.4",
            plugin_version=plugin_version,
            grim_connected=grim_connected,
            last_seen=last_seen or datetime.now(timezone.utc),
        ))
        await db.commit()


@pytest.mark.asyncio
async def test_list_plugins_returns_one_entry_per_server(client, db_session):
    """FIX: previously returned up to TWO rows per server (a separate
    'GrimAC' pseudo-row when connected) with no way for the frontend to
    associate them as one server's combined status. Now one object per
    server with both status fields as siblings."""
    await _seed_heartbeat(db_session, "srv-1", grim_connected=True)
    await _seed_heartbeat(db_session, "srv-2", grim_connected=False)

    response = await client.get("/api/v1/dashboard/plugins", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # not 3 — srv-1 no longer produces a second row


@pytest.mark.asyncio
async def test_list_plugins_umbrella_status_is_active_for_recent_heartbeat(client, db_session):
    """FIX (the actual bug): umbrella_status must be the literal string
    'ACTIVE' — the dashboard's status badge does `p.umbrella_status ===
    'ACTIVE'` and previously always got 'connected' (via a fallback chain
    onto a field this endpoint never returned this shape for), so a
    genuinely healthy server's badge always rendered red/disconnected."""
    await _seed_heartbeat(db_session, "srv-1")

    response = await client.get("/api/v1/dashboard/plugins", headers=ADMIN_HEADERS)
    entry = response.json()[0]
    assert entry["umbrella_status"] == "ACTIVE"
    assert entry["server_id"] == "srv-1"
    assert entry["server_name"] == "Server srv-1"
    assert entry["umbrella_version"] == "1.2.3"


@pytest.mark.asyncio
async def test_list_plugins_grimac_status_reflects_real_connection_state(client, db_session):
    """FIX (the other half of the bug): grimac_status was never populated
    with real data at all -- the frontend's hardcoded 'ACTIVE' fallback
    always won, showing GrimAC as connected even when it wasn't. Now
    reflects hb.grim_connected honestly."""
    await _seed_heartbeat(db_session, "srv-connected", grim_connected=True)
    await _seed_heartbeat(db_session, "srv-standalone", grim_connected=False)

    response = await client.get("/api/v1/dashboard/plugins", headers=ADMIN_HEADERS)
    by_server = {e["server_id"]: e for e in response.json()}

    assert by_server["srv-connected"]["grimac_status"] == "ACTIVE"
    assert by_server["srv-standalone"]["grimac_status"] == "STANDALONE"


@pytest.mark.asyncio
async def test_list_plugins_excludes_stale_heartbeats(client, db_session):
    """Servers not seen in the last 3 minutes are omitted entirely —
    unchanged behavior, verifying the reshape didn't affect the cutoff
    filter."""
    await _seed_heartbeat(db_session, "srv-fresh")
    await _seed_heartbeat(
        db_session, "srv-stale",
        last_seen=datetime.now(timezone.utc) - timedelta(minutes=10),
    )

    response = await client.get("/api/v1/dashboard/plugins", headers=ADMIN_HEADERS)
    server_ids = [e["server_id"] for e in response.json()]
    assert "srv-fresh" in server_ids
    assert "srv-stale" not in server_ids


@pytest.mark.asyncio
async def test_list_plugins_empty_when_no_heartbeats(client):
    response = await client.get("/api/v1/dashboard/plugins", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_plugins_requires_permission(client):
    response = await client.get("/api/v1/dashboard/plugins")
    assert response.status_code == 401
