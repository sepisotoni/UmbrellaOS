"""
services/events/subscribers.py — Built-in in-process event subscribers.

Imported once (see services/events/__init__.py) for its registration side
effect, exactly like capabilities/__init__.py imports every capability
module. Two subscribers now:

1. A structured-log line on "staff_escalation.created" — the first
   genuinely real (if modest) in-process consumer of the event bus, proof
   the dispatcher's fan-out path actually runs a handler, not just that
   undispatched rows exist.
2. A global webhook-delivery subscriber (Phase 7 item 2) — runs on every
   dispatched event regardless of topic, looking up active
   WebhookSubscription rows for that event's topic and POSTing to each.
   See docs/design/public-rest-api-and-webhooks.md, Decision 4 for why
   this is a global subscriber rather than a per-topic one, and
   services/webhooks/service.py for the actual delivery mechanics.

Handlers registered here must be idempotent: a handler that raises causes
the whole event to be retried (see services/events/dispatcher.py's module
docstring), which can mean re-running already-successful handlers for the
same event alongside the one that failed. For the webhook subscriber
specifically that means already-succeeded deliveries to OTHER subscribers
of the same topic get re-POSTed too if even one subscriber's delivery
fails - documented as a deliberate at-least-once trade-off in the design
doc referenced above, not an oversight.
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from services.events.bus import EventBus
from services.webhooks.service import WebhookDeliveryService, WebhookDeliveryError, WebhookService

logger = logging.getLogger(__name__)


async def _log_staff_escalation_created(payload: dict, db: AsyncSession) -> None:
    logger.info(
        "event bus: staff escalation created (source=%s, escalation_id=%s, confidence=%s)",
        payload.get("source"), payload.get("escalation_id"), payload.get("confidence"),
    )


async def _deliver_webhooks(payload: dict, db: AsyncSession, topic: str, event_id: str) -> None:
    subscriptions = await WebhookService.list_active_for_topic(db, topic)
    if not subscriptions:
        return

    errors: list[str] = []
    for subscription in subscriptions:
        try:
            await WebhookDeliveryService.deliver(
                subscription, topic=topic, event_id=event_id, payload=payload
            )
        except WebhookDeliveryError as exc:
            logger.warning("webhook delivery failed: %s", exc)
            errors.append(str(exc))

    if errors:
        # Raising feeds the dispatcher's existing attempts/backoff on the
        # whole event — see this module's docstring for the at-least-once
        # trade-off this implies.
        raise WebhookDeliveryError("; ".join(errors)[:2000])


EventBus.subscribe("staff_escalation.created", _log_staff_escalation_created)
EventBus.subscribe_global(_deliver_webhooks)
