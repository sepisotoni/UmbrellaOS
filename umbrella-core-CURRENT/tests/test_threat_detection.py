"""
tests/test_threat_detection.py — Tests for services/threat_detection_service.py
(Phase 9, item 4).

Monkeypatches the module's AsyncSessionLocal reference to the per-test
isolated engine (tests/conftest.py's db_session fixture), the same
session factory interface as the real one — this is what lets these tests
exercise record()'s actual DB writes/queries without depending on the
module-level real-engine tables tests don't otherwise create (see
tests/registry/test_plugin_sandbox.py and test_event_dispatcher.py for
the codebase's existing precedent of testing AsyncSessionLocal-based
service logic against an injected session rather than the real one).
"""
import json

import pytest
from sqlalchemy import select

import services.threat_detection_service as threat_detection_service
from models.security_event import SecurityEvent
from services.events.bus import EventBus


@pytest.fixture(autouse=True)
def _reset_cooldowns_and_bus():
    threat_detection_service.reset_cooldowns()
    EventBus.reset_for_tests()
    yield
    threat_detection_service.reset_cooldowns()
    EventBus.reset_for_tests()


@pytest.fixture
def _patched_session(db_session, monkeypatch):
    monkeypatch.setattr(threat_detection_service, "AsyncSessionLocal", db_session)
    return db_session


@pytest.mark.asyncio
async def test_record_writes_a_security_event_row(_patched_session, db_session):
    await threat_detection_service.record(event_type="auth_failure", source_ip="1.2.3.4")

    async with db_session() as db:
        rows = (await db.execute(select(SecurityEvent))).scalars().all()
    assert len(rows) == 1
    assert rows[0].event_type == "auth_failure"
    assert rows[0].source_ip == "1.2.3.4"


@pytest.mark.asyncio
async def test_no_alert_below_threshold(_patched_session):
    alerted = await threat_detection_service.record(event_type="auth_failure", source_ip="1.2.3.4")
    assert alerted is False


@pytest.mark.asyncio
async def test_alert_fires_once_threshold_crossed(_patched_session):
    from config import get_settings

    threshold = get_settings().threat_detection_auth_failure_threshold
    alerted = False
    for _ in range(threshold):
        alerted = await threat_detection_service.record(event_type="auth_failure", source_ip="9.9.9.9")
    assert alerted is True


@pytest.mark.asyncio
async def test_alert_publishes_security_threat_detected_event(_patched_session, db_session):
    from config import get_settings

    threshold = get_settings().threat_detection_auth_failure_threshold
    for _ in range(threshold):
        await threat_detection_service.record(event_type="auth_failure", source_ip="9.9.9.9")

    async with db_session() as db:
        from models.events import Event

        events = (await db.execute(select(Event).where(Event.topic == "security.threat_detected"))).scalars().all()
    assert len(events) == 1
    payload = json.loads(events[0].payload_json)
    assert payload["event_type"] == "auth_failure"
    assert payload["source_ip"] == "9.9.9.9"


@pytest.mark.asyncio
async def test_repeated_crossings_within_cooldown_do_not_re_alert(_patched_session):
    from config import get_settings

    threshold = get_settings().threat_detection_auth_failure_threshold
    alerts = []
    for _ in range(threshold + 5):
        alerts.append(await threat_detection_service.record(event_type="auth_failure", source_ip="9.9.9.9"))
    assert alerts.count(True) == 1


@pytest.mark.asyncio
async def test_different_source_ips_tracked_independently(_patched_session):
    from config import get_settings

    threshold = get_settings().threat_detection_auth_failure_threshold
    for _ in range(threshold - 1):
        await threat_detection_service.record(event_type="auth_failure", source_ip="1.1.1.1")
    # A different source IP starts its own count from zero.
    alerted = await threat_detection_service.record(event_type="auth_failure", source_ip="2.2.2.2")
    assert alerted is False


@pytest.mark.asyncio
async def test_sandbox_violation_alerts_on_first_occurrence(_patched_session):
    alerted = await threat_detection_service.record(event_type="sandbox_violation", identifier="some-plugin")
    assert alerted is True


@pytest.mark.asyncio
async def test_record_never_raises_when_db_unavailable(monkeypatch):
    """Fail-open: a broken DB session factory must not propagate as an
    exception into the caller (rate-limit middleware, auth dependency)."""
    class _BrokenSessionLocal:
        def __call__(self):
            raise RuntimeError("db is down")

    monkeypatch.setattr(threat_detection_service, "AsyncSessionLocal", _BrokenSessionLocal())
    result = await threat_detection_service.record(event_type="auth_failure", source_ip="1.2.3.4")
    assert result is False
