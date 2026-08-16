"""
tests/registry/test_capabilities_knowledge.py — REST integration tests for
knowledge capabilities: listing, RBAC, and index/search round-trip.
"""
import pytest

from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_knowledge_capabilities_are_listed(client):
    response = await client.get("/api/v1/capabilities")
    names = {c["name"] for c in response.json()}
    assert "knowledge.entry.index" in names
    assert "knowledge.entry.search" in names
    assert "knowledge.correction.propose" in names
    assert "knowledge.correction.approve" in names


@pytest.mark.asyncio
async def test_index_and_search_round_trip(client, monkeypatch):
    from config import get_settings

    monkeypatch.setattr(get_settings(), "knowledge_channel_names", "ai-faq")

    index_resp = await client.post(
        "/api/v1/capabilities/knowledge.entry.index/invoke",
        json={
            "channel_id": "chan-1", "channel_name": "ai-faq", "discord_message_id": "msg-100",
            "author_id": "user-1", "author_name": "Alice", "content": "the wiki is at wiki.example.com",
        },
        headers=ADMIN_HEADERS,
    )
    assert index_resp.status_code == 200
    assert index_resp.json()["indexed"] is True

    search_resp = await client.post(
        "/api/v1/capabilities/knowledge.entry.search/invoke",
        json={"query": "wiki"},
        headers=ADMIN_HEADERS,
    )
    assert search_resp.status_code == 200
    assert len(search_resp.json()["entries"]) == 1


@pytest.mark.asyncio
async def test_search_allowed_for_helper_but_index_denied(client, db_session):
    """helper has knowledge.entry.search but not knowledge.entry.manage."""
    headers = await session_headers_for_role(db_session, "helper")

    search_resp = await client.post(
        "/api/v1/capabilities/knowledge.entry.search/invoke", json={}, headers=headers
    )
    assert search_resp.status_code == 200

    index_resp = await client.post(
        "/api/v1/capabilities/knowledge.entry.index/invoke",
        json={
            "channel_id": "c", "channel_name": "ai-faq", "discord_message_id": "m",
            "author_id": "u", "author_name": "n", "content": "x",
        },
        headers=headers,
    )
    assert index_resp.status_code == 403


@pytest.mark.asyncio
async def test_correction_review_denied_for_helper(client, db_session):
    """helper has no knowledge.correction.review - approve/reject are moderator+."""
    headers = await session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/capabilities/knowledge.correction.list_pending/invoke", json={}, headers=headers
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_approve_nonexistent_correction_returns_404(client):
    response = await client.post(
        "/api/v1/capabilities/knowledge.correction.approve/invoke",
        json={"entry_id": "does-not-exist"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404
