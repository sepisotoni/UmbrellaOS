"""
services/threat_detection_service.py — Phase 9, item 4: "Threat
detection: anomalous auth patterns, brute-force/rate-limit-violation
alerting, tied into the Phase 6 notification fabric."

Scoping decision, stated up front (per the handoff's own instruction to
flag real scoping decisions rather than default them): this is deliberately
NOT generic enterprise SIEM tooling — no ML anomaly models, no
cross-tenant correlation, no compliance-report generation. It's scoped to
this project's actual, stated threat model (Phase 0 onward: a
single-operator, internet-exposed platform that must assume malicious
users) and its three concrete, currently-observable failure signals:

- repeated authentication failures from one source (credential stuffing /
  brute force against admin-key, session, or API-key auth)
- repeated rate-limit violations from one source (scraping/abuse)
- any plugin sandbox violation (a single occurrence matters — see below)

"Tied into the Phase 6 notification fabric" concretely means: publishing
onto the existing EventBus (services/events/bus.py) under a
`security.threat_detected` topic. That's the same mechanism Phase 7's
webhooks already use to reach arbitrary runtime-registered subscribers
(EventBus.subscribe_global -> WebhookSubscription rows), and the same one
umbrella-discord would subscribe to for a Discord alert — no new delivery
mechanism invented here, reusing what Phase 6/7 already built rather than
building a second notification path.

Design: each call to `record()` is a durable fact (a SecurityEvent row),
independent of whether it crosses the alert threshold. Whether it crosses
the threshold is evaluated on every insert by counting this source's
matching rows within the configured lookback window. Sandbox violations
alert on the first occurrence (threshold effectively 1) since a single
sandbox escape *attempt* is the kind of thing Phase 7's own hand-testing
treated as inherently serious, not something to wait for a pattern on.

Alert de-duplication: a per-(event_type, source_ip) in-process cooldown
(module-level dict, mirrors metrics_service's process-wide-singleton
pattern) prevents re-alerting on every single row once a burst has already
crossed the threshold once — an ongoing brute-force attempt would
otherwise fire one webhook per failed request, which is noise, not signal.
Deliberately in-memory rather than a DB-backed cooldown: losing cooldown
state on a restart just means one possibly-redundant alert after a
restart during an ongoing attack, which is a far smaller cost than adding
a second source of truth for something this ephemeral.

Uses its own DB session (AsyncSessionLocal) rather than piggybacking on
the caller's request-scoped session, because most call sites (rate-limit
middleware, auth-failure paths) run in contexts where a failure is being
actively rejected and the caller's own transaction may be about to roll
back — recording the security signal must not be contingent on that.
Same reasoning as log_aggregation_service's flush loop.
"""
from __future__ import annotations

import json
import logging
import time

from sqlalchemy import func, select

from config import get_settings
from database import AsyncSessionLocal
from models.security_event import SecurityEvent
from services.events.bus import EventBus
from services.metrics_service import security_events_total, threat_alerts_total

logger = logging.getLogger(__name__)

# event_type -> alert threshold override. Anything not listed uses the
# configured auth_failure/rate_limit thresholds by event_type name below.
_IMMEDIATE_ALERT_EVENT_TYPES = {"sandbox_violation"}

# (event_type, source_ip) -> last alert unix timestamp. Process-wide,
# in-memory — see module docstring.
_last_alerted: dict[tuple[str, str], float] = {}


def _threshold_for(event_type: str) -> int:
    settings = get_settings()
    if event_type in _IMMEDIATE_ALERT_EVENT_TYPES:
        return 1
    if event_type == "rate_limit_violation":
        return settings.threat_detection_rate_limit_threshold
    return settings.threat_detection_auth_failure_threshold


def _cooldown_key(event_type: str, source_ip: str | None) -> tuple[str, str]:
    return (event_type, source_ip or "unknown")


def _in_cooldown(event_type: str, source_ip: str | None) -> bool:
    settings = get_settings()
    key = _cooldown_key(event_type, source_ip)
    last = _last_alerted.get(key)
    if last is None:
        return False
    return (time.time() - last) < settings.threat_detection_alert_cooldown_seconds


def reset_cooldowns() -> None:
    """Test-only: clears in-process alert cooldown state."""
    _last_alerted.clear()


async def record(
    *,
    event_type: str,
    source_ip: str | None = None,
    identifier: str | None = None,
    detail: dict | None = None,
) -> bool:
    """Records a security signal and, if it crosses this event_type's
    threshold within the lookback window and isn't in cooldown, publishes
    a `security.threat_detected` event. Returns True if an alert was
    raised this call, False otherwise. Never raises — a bug in threat
    detection must not break the auth/rate-limit path that's calling it,
    the same fail-open-on-the-observability-path principle already used
    by rate_limit.py (Redis) and log_aggregation_service (queue-full)."""
    try:
        settings = get_settings()
        async with AsyncSessionLocal() as db:
            row = SecurityEvent(
                event_type=event_type,
                source_ip=source_ip,
                identifier=identifier,
                detail=json.dumps(detail or {}),
            )
            db.add(row)
            await db.flush()
            security_events_total.inc(event_type=event_type)

            threshold = _threshold_for(event_type)
            count_stmt = select(func.count()).select_from(SecurityEvent).where(
                SecurityEvent.event_type == event_type,
            )
            if source_ip is not None:
                count_stmt = count_stmt.where(SecurityEvent.source_ip == source_ip)
            # Portable recency filter: compare against a Python-computed
            # cutoff rather than SQLite-specific `datetime('now', ...)`,
            # since this project also targets Postgres in production.
            from datetime import datetime, timedelta, timezone

            cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.threat_detection_window_seconds)
            count_stmt = count_stmt.where(SecurityEvent.created_at >= cutoff)
            recent_count = (await db.execute(count_stmt)).scalar_one()

            alerted = False
            if recent_count >= threshold and not _in_cooldown(event_type, source_ip):
                await EventBus.publish(
                    db,
                    topic="security.threat_detected",
                    payload={
                        "event_type": event_type,
                        "source_ip": source_ip,
                        "identifier": identifier,
                        "recent_count": recent_count,
                        "threshold": threshold,
                        "window_seconds": settings.threat_detection_window_seconds,
                    },
                )
                _last_alerted[_cooldown_key(event_type, source_ip)] = time.time()
                threat_alerts_total.inc(event_type=event_type)
                alerted = True

            await db.commit()
            return alerted
    except Exception:
        logger.exception("threat detection: failed to record/alert for event_type=%s (non-fatal)", event_type)
        return False
