"""
tests/test_observability_routers.py — Tests for api/routers/logs.py and
api/routers/security.py (Phase 9, items 3 & 4).
"""
import pytest

from models.log_entry import LogEntry
from models.security_event import SecurityEvent
from tests.conftest import ADMIN_HEADERS


@pytest.mark.asyncio
async def test_logs_search_requires_auth(client):
    response = await client.get("/api/v1/logs")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logs_search_returns_matching_entries(client, db_session):
    async with db_session() as db:
        db.add(LogEntry(level="ERROR", logger_name="umbrella.a", message="disk full", source="umbrella-core"))
        db.add(LogEntry(level="INFO", logger_name="umbrella.b", message="startup complete", source="umbrella-core"))
        await db.commit()

    response = await client.get("/api/v1/logs", params={"query": "disk"}, headers=ADMIN_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert len(body["entries"]) == 1
    assert body["entries"][0]["message"] == "disk full"


@pytest.mark.asyncio
async def test_security_events_requires_auth(client):
    response = await client.get("/api/v1/security/events")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_security_events_lists_recorded_events(client, db_session):
    async with db_session() as db:
        db.add(SecurityEvent(event_type="auth_failure", source_ip="1.2.3.4", detail="{}"))
        await db.commit()

    response = await client.get("/api/v1/security/events", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["entries"][0]["event_type"] == "auth_failure"


@pytest.mark.asyncio
async def test_security_events_filters_by_event_type(client, db_session):
    async with db_session() as db:
        db.add(SecurityEvent(event_type="auth_failure", source_ip="1.2.3.4", detail="{}"))
        db.add(SecurityEvent(event_type="rate_limit_violation", source_ip="1.2.3.4", detail="{}"))
        await db.commit()

    response = await client.get(
        "/api/v1/security/events", params={"event_type": "rate_limit_violation"}, headers=ADMIN_HEADERS
    )
    body = response.json()
    assert body["total"] == 1
    assert body["entries"][0]["event_type"] == "rate_limit_violation"
