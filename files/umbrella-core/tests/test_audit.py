"""
tests/test_audit.py — Tests for audit log endpoints.

GET /api/v1/audit
GET /api/v1/audit/{action}

Key concern: total must reflect full matching row count, not page size (TD-05).
"""
import pytest
from tests.conftest import ADMIN_HEADERS


async def _seed_audit_entries(client, count: int = 5, action: str = "settings.update"):
    """Helper: create audit entries by patching settings 'count' times."""
    for i in range(count):
        await client.patch(
            "/api/v1/settings/server.name",
            json={"value": f"value-{i}"},
            headers=ADMIN_HEADERS,
        )


@pytest.mark.asyncio
async def test_audit_list_returns_dict(client):
    response = await client.get("/api/v1/audit", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "entries" in data
    assert "limit" in data
    assert "offset" in data


@pytest.mark.asyncio
async def test_audit_total_reflects_real_count_not_page_size(client):
    """
    TD-05 regression test.
    Seed 10 entries, request page size of 3.
    total must be 10, not 3.
    """
    await _seed_audit_entries(client, count=10)
    response = await client.get("/api/v1/audit?limit=3&offset=0", headers=ADMIN_HEADERS)
    data = response.json()
    assert len(data["entries"]) == 3       # page has 3 items
    assert data["total"] >= 10             # but total is the real count


@pytest.mark.asyncio
async def test_audit_entries_newest_first(client):
    await _seed_audit_entries(client, count=3)
    response = await client.get("/api/v1/audit", headers=ADMIN_HEADERS)
    entries = response.json()["entries"]
    if len(entries) >= 2:
        assert entries[0]["created_at"] >= entries[-1]["created_at"]


@pytest.mark.asyncio
async def test_audit_entry_shape(client):
    await _seed_audit_entries(client, count=1)
    response = await client.get("/api/v1/audit", headers=ADMIN_HEADERS)
    entry = response.json()["entries"][0]
    for field in ("id", "actor", "actor_type", "action", "target", "details", "created_at"):
        assert field in entry


@pytest.mark.asyncio
async def test_audit_filter_by_actor_type(client):
    await _seed_audit_entries(client, count=3)
    response = await client.get("/api/v1/audit?actor_type=staff", headers=ADMIN_HEADERS)
    data = response.json()
    assert response.status_code == 200
    for entry in data["entries"]:
        assert entry["actor_type"] == "staff"


@pytest.mark.asyncio
async def test_audit_filter_actor_type_total_is_accurate(client):
    """total for a filtered request must match entries of that type only."""
    await _seed_audit_entries(client, count=4)
    response = await client.get(
        "/api/v1/audit?actor_type=staff&limit=1", headers=ADMIN_HEADERS
    )
    data = response.json()
    # total should be >= 4 (all staff entries), page should have 1
    assert len(data["entries"]) == 1
    assert data["total"] >= 4


@pytest.mark.asyncio
async def test_audit_by_action_returns_correct_shape(client):
    await _seed_audit_entries(client, count=2)
    response = await client.get("/api/v1/audit/settings.update", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "action" in data
    assert data["action"] == "settings.update"
    assert "total" in data
    assert "entries" in data


@pytest.mark.asyncio
async def test_audit_by_action_filters_correctly(client):
    await _seed_audit_entries(client, count=3, action="settings.update")
    response = await client.get("/api/v1/audit/settings.update", headers=ADMIN_HEADERS)
    data = response.json()
    for entry in data["entries"]:
        assert entry["action"] == "settings.update"


@pytest.mark.asyncio
async def test_audit_by_action_unknown_action_returns_empty(client):
    response = await client.get("/api/v1/audit/nonexistent.action", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["entries"] == []


@pytest.mark.asyncio
async def test_audit_by_action_total_not_page_size(client):
    """Same TD-05 regression but on the /{action} endpoint."""
    await _seed_audit_entries(client, count=8)
    response = await client.get(
        "/api/v1/audit/settings.update?limit=2", headers=ADMIN_HEADERS
    )
    data = response.json()
    assert len(data["entries"]) == 2
    assert data["total"] >= 8
