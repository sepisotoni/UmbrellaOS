"""
tests/registry/test_capabilities_player_risk.py — REST integration tests
for the unified player risk score.
"""
import pytest

from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_player_risk_capability_is_listed(client):
    response = await client.get("/api/v1/capabilities")
    names = {c["name"] for c in response.json()}
    assert "player_risk.score" in names


@pytest.mark.asyncio
async def test_player_risk_score_with_no_signals(client):
    response = await client.post(
        "/api/v1/capabilities/player_risk.score/invoke",
        json={"player_uuid": "no-signals-uuid"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["total_score"] == 0


@pytest.mark.asyncio
async def test_player_risk_denied_for_helper(client, db_session):
    headers = await session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/capabilities/player_risk.score/invoke",
        json={"player_uuid": "some-uuid"},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_player_risk_allowed_for_moderator(client, db_session):
    headers = await session_headers_for_role(db_session, "moderator")
    response = await client.post(
        "/api/v1/capabilities/player_risk.score/invoke",
        json={"player_uuid": "some-uuid"},
        headers=headers,
    )
    assert response.status_code == 200
