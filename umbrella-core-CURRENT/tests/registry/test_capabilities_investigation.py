"""
tests/registry/test_capabilities_investigation.py — REST integration tests
for the investigation capabilities: listing, RBAC, and the aggregator's
end-to-end round trip through the real HTTP stack.
"""
import pytest

from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_investigation_capabilities_are_listed(client):
    response = await client.get("/api/v1/capabilities")
    names = {c["name"] for c in response.json()}
    assert "investigation.run" in names
    assert "investigation.whitelist_status" in names
    assert "investigation.known_issues" in names
    assert "investigation.punishment_history" in names
    assert "investigation.linked_account" in names
    assert "investigation.maintenance_status" in names
    assert "investigation.recent_announcements" in names


@pytest.mark.asyncio
async def test_investigation_run_via_admin_key(client):
    response = await client.post(
        "/api/v1/capabilities/investigation.run/invoke",
        json={"question": "Why can't they join?", "target_user_id": "discord-abc"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["findings"]) == 6
    assert body["investigation_id"]


@pytest.mark.asyncio
async def test_investigation_run_allowed_for_helper_role(client, db_session):
    """helper has investigation.run - a read-only diagnostic role should
    reasonably include it, unlike moderation report management."""
    headers = await session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/capabilities/investigation.run/invoke",
        json={"question": "test", "target_user_id": None},
        headers=headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_investigation_run_denied_for_member_role(client, db_session):
    headers = await session_headers_for_role(db_session, "member")
    response = await client.post(
        "/api/v1/capabilities/investigation.run/invoke",
        json={"question": "test", "target_user_id": None},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_single_tool_capability_round_trip(client):
    response = await client.post(
        "/api/v1/capabilities/investigation.known_issues/invoke",
        json={},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tool_key"] == "known_issues"
