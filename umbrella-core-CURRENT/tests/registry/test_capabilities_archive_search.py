"""
tests/registry/test_capabilities_archive_search.py — REST integration
tests for archive.search: listing, RBAC (moderator+, not helper - given
the unfiltered-by-channel exposure), and round-trip.
"""
import pytest

from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_archive_search_is_listed(client):
    response = await client.get("/api/v1/capabilities")
    names = {c["name"] for c in response.json()}
    assert "archive.search" in names


@pytest.mark.asyncio
async def test_archive_search_via_admin_key(client):
    response = await client.post(
        "/api/v1/capabilities/archive.search/invoke",
        json={"query": "nonexistent-marker-xyz"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["messages"] == []


@pytest.mark.asyncio
async def test_archive_search_allowed_for_moderator(client, db_session):
    headers = await session_headers_for_role(db_session, "moderator")
    response = await client.post(
        "/api/v1/capabilities/archive.search/invoke", json={}, headers=headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_archive_search_denied_for_helper(client, db_session):
    """helper gets investigation/knowledge search but not archive.search -
    this reveals unfiltered chat content across every channel, a higher
    trust bar than the read-only diagnostic tools."""
    headers = await session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/capabilities/archive.search/invoke", json={}, headers=headers
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_archive_search_denied_for_member(client, db_session):
    headers = await session_headers_for_role(db_session, "member")
    response = await client.post(
        "/api/v1/capabilities/archive.search/invoke", json={}, headers=headers
    )
    assert response.status_code == 403
