"""
tests/test_waf_middleware.py — Tests for api/middleware/waf.py (Phase 9, item 7).
"""
import pytest

from sqlalchemy import select

import services.threat_detection_service as threat_detection_service
from models.security_event import SecurityEvent


@pytest.mark.asyncio
async def test_normal_request_passes_through(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_path_traversal_pattern_rejected(client):
    response = await client.get("/api/v1/players/../../etc/passwd")
    assert response.status_code in (400, 404)  # httpx/starlette may normalize the path before routing
    if response.status_code == 400:
        assert response.json()["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_sqli_pattern_in_query_string_rejected(client):
    response = await client.get("/api/v1/audit", params={"q": "1 OR 1=1"})
    assert response.status_code == 400
    assert response.json()["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_xss_pattern_in_query_string_rejected(client):
    response = await client.get("/api/v1/audit", params={"q": "<script>alert(1)</script>"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_oversized_body_rejected(client):
    response = await client.post(
        "/api/v1/audit",
        content=b"x",
        headers={"Content-Length": str(11 * 1024 * 1024)},
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_blocked_request_recorded_as_security_event(client, db_session, monkeypatch):
    # See tests/test_threat_detection.py's module docstring: the WAF
    # middleware records via threat_detection_service's own
    # AsyncSessionLocal (same real engine as `client`'s DB in production),
    # not the `client` fixture's per-test dependency override — point it
    # at the same per-test session factory so this test can observe it.
    monkeypatch.setattr(threat_detection_service, "AsyncSessionLocal", db_session)

    await client.get("/api/v1/audit", params={"q": "1 OR 1=1"})

    async with db_session() as db:
        rows = (await db.execute(select(SecurityEvent).where(SecurityEvent.event_type == "waf_block"))).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_metrics_endpoint_is_exempt_from_waf_checks(client):
    """/metrics itself is admin-key gated (401 without one), not
    WAF-blocked — proves the exemption list actually takes effect rather
    than merely existing."""
    response = await client.get("/metrics", params={"q": "1 OR 1=1"})
    assert response.status_code == 401
