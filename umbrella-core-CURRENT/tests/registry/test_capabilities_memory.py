"""
tests/registry/test_capabilities_memory.py — REST integration tests for
memory capabilities: listing, RBAC, and round-trip.
"""
import pytest

from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_memory_capabilities_are_listed(client):
    response = await client.get("/api/v1/capabilities")
    names = {c["name"] for c in response.json()}
    assert "memory.server_fact.set" in names
    assert "memory.server_fact.get" in names
    assert "memory.recurring.record" in names
    assert "memory.recurring.top" in names
    assert "memory.maintenance.purge_expired" in names


@pytest.mark.asyncio
async def test_server_fact_set_and_get_round_trip(client):
    set_resp = await client.post(
        "/api/v1/capabilities/memory.server_fact.set/invoke",
        json={"fact_key": "server_ip", "value": "play.example.com"},
        headers=ADMIN_HEADERS,
    )
    assert set_resp.status_code == 200

    get_resp = await client.post(
        "/api/v1/capabilities/memory.server_fact.get/invoke",
        json={"fact_key": "server_ip"},
        headers=ADMIN_HEADERS,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["value"] == "play.example.com"


@pytest.mark.asyncio
async def test_recurring_top_orders_by_hit_count(client):
    await client.post(
        "/api/v1/capabilities/memory.recurring.record/invoke",
        json={"topic_key": "common-issue", "resolution": "restart client"},
        headers=ADMIN_HEADERS,
    )
    await client.post(
        "/api/v1/capabilities/memory.recurring.record/invoke",
        json={"topic_key": "common-issue", "resolution": "restart client v2"},
        headers=ADMIN_HEADERS,
    )
    await client.post(
        "/api/v1/capabilities/memory.recurring.record/invoke",
        json={"topic_key": "rare-issue", "resolution": "x"},
        headers=ADMIN_HEADERS,
    )

    top_resp = await client.post(
        "/api/v1/capabilities/memory.recurring.top/invoke", json={}, headers=ADMIN_HEADERS
    )
    entries = top_resp.json()["entries"]
    assert entries[0]["key"] == "recurring:common-issue"
    assert entries[0]["hit_count"] == 2


@pytest.mark.asyncio
async def test_memory_capabilities_denied_for_helper(client, db_session):
    """memory.manage is moderator+, not the helper tier."""
    headers = await session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/capabilities/memory.server_fact.list/invoke", json={}, headers=headers
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_memory_capabilities_allowed_for_moderator(client, db_session):
    headers = await session_headers_for_role(db_session, "moderator")
    response = await client.post(
        "/api/v1/capabilities/memory.server_fact.list/invoke", json={}, headers=headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_purge_expired_removes_only_expired_short_term_entries(client, db_session):
    from datetime import datetime, timedelta, timezone
    from models.memory import MemoryEntry, MemoryScope

    async with db_session() as db:
        db.add_all([
            MemoryEntry(scope=MemoryScope.SHORT_TERM, key="conversation:c1:u1", value="expired",
                        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)),
            MemoryEntry(scope=MemoryScope.SHORT_TERM, key="conversation:c2:u2", value="still fresh",
                        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)),
        ])
        await db.commit()

    # Server facts never have an expiry - confirms purge can never touch them.
    await client.post(
        "/api/v1/capabilities/memory.server_fact.set/invoke",
        json={"fact_key": "server_ip", "value": "play.example.com"},
        headers=ADMIN_HEADERS,
    )

    response = await client.post(
        "/api/v1/capabilities/memory.maintenance.purge_expired/invoke", json={}, headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    assert response.json()["purged_count"] == 1

    get_resp = await client.post(
        "/api/v1/capabilities/memory.server_fact.get/invoke",
        json={"fact_key": "server_ip"},
        headers=ADMIN_HEADERS,
    )
    assert get_resp.json()["value"] == "play.example.com"


@pytest.mark.asyncio
async def test_purge_expired_denied_for_helper(client, db_session):
    headers = await session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/capabilities/memory.maintenance.purge_expired/invoke", json={}, headers=headers
    )
    assert response.status_code == 403
