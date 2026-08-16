"""
tests/registry/test_capabilities_operational_intelligence.py — REST
integration tests for crash-risk assessment and NL operational queries.
"""
import pytest

from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_operational_intelligence_capabilities_are_listed(client):
    response = await client.get("/api/v1/capabilities")
    names = {c["name"] for c in response.json()}
    assert "operational_intelligence.crash_risk.assess" in names
    assert "operational_intelligence.query" in names
    assert "operational_intelligence.postmortem.draft" in names


@pytest.mark.asyncio
async def test_crash_risk_assess_with_no_data(client):
    response = await client.post(
        "/api/v1/capabilities/operational_intelligence.crash_risk.assess/invoke",
        json={"server_id": "nonexistent-server"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["risk_level"] == "insufficient_data"


@pytest.mark.asyncio
async def test_crash_risk_denied_for_helper(client, db_session):
    headers = await session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/capabilities/operational_intelligence.crash_risk.assess/invoke",
        json={"server_id": "srv-1"},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_crash_risk_allowed_for_moderator(client, db_session):
    headers = await session_headers_for_role(db_session, "moderator")
    response = await client.post(
        "/api/v1/capabilities/operational_intelligence.crash_risk.assess/invoke",
        json={"server_id": "srv-1"},
        headers=headers,
    )
    assert response.status_code == 200
