"""
services/events/dispatcher.py — Reads undispatched Event rows and fans them
out to in-process subscribers (Phase 7, Decision 1).

Structurally the same shape as Phase 6's proven notifications_cog.py
60-second poller, and — inside this service — the same shape as
services/scheduler_loop.py: EventDispatcher.dispatch_pending() is the
testable core logic (mirrors SchedulerService.run_due_schedules(), already
fully tested on its own), and run_event_dispatcher_loop() is a thin
loop-with-a-stop-event wrapper around it, wired into main.py's app
lifespan exactly like run_scheduler_loop and run_sampler_loop already are.

Dispatch semantics, stated plainly:
- A row with zero currently-registered in-process subscribers for its
  topic is marked dispatched immediately — there's nothing to fan out to.
  This does NOT mean "no consumer will ever see it": external consumers
  (Discord, future webhooks) don't go through this path at all (see
  services/events/bus.py's module docstring) - this dispatched_at is
  purely "did every currently-registered in-process handler run."
- A row with one or more subscribers (per-topic and/or global — see
  services/events/bus.py's module docstring for the distinction) is only
  marked dispatched once every one of them has run without raising. If any
  handler raises, the row is retried as a whole next eligible attempt (not
  per-handler) — the simplest correct behavior for at-least-once delivery.
  Handlers must be safe to run more than once for the same event as a
  result; the built-in logging subscriber is idempotent by construction,
  and the webhook-delivery global subscriber (Phase 7 item 2) documents
  its own at-least-once trade-off in
  docs/design/public-rest-api-and-webhooks.md.
- Backoff is exponential in `attempts`, capped, computed into
  `next_attempt_at` — see models/events.py's docstring for why that
  column exists beyond the locked decision's original field list.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models.events import Event
from services.events.bus import EventBus
from services.metrics_service import events_dispatched_total, events_dispatch_failed_total

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL_SECONDS = 60
DEFAULT_BATCH_SIZE = 50

_BACKOFF_BASE_SECONDS = 5
_BACKOFF_MAX_SECONDS = 300


def _backoff_seconds(attempts: int) -> int:
    return min(_BACKOFF_BASE_SECONDS * (2 ** attempts), _BACKOFF_MAX_SECONDS)


class EventDispatcher:
    @staticmethod
    async def dispatch_pending(
        db: AsyncSession, *, batch_size: int = DEFAULT_BATCH_SIZE, now: datetime | None = None
    ) -> list[str]:
        """Dispatches up to `batch_size` eligible undispatched events.
        Returns the ids of events successfully dispatched this call (not
        the ids of events that failed and were rescheduled)."""
        now = now or datetime.now(timezone.utc)

        stmt = (
            select(Event)
            .where(Event.dispatched_at.is_(None))
            .order_by(Event.created_at.asc())
            .limit(batch_size)
        )
        rows = list((await db.execute(stmt)).scalars().all())

        dispatched_ids: list[str] = []
        for event in rows:
            if event.next_attempt_at is not None:
                next_attempt_at = event.next_attempt_at
                if next_attempt_at.tzinfo is None:
                    next_attempt_at = next_attempt_at.replace(tzinfo=timezone.utc)
                if next_attempt_at > now:
                    continue  # still in backoff, not eligible this cycle

            topic_handlers = EventBus.subscribers_for(event.topic)
            global_handlers = EventBus.global_subscribers()
            if not topic_handlers and not global_handlers:
                event.dispatched_at = now
                dispatched_ids.append(event.id)
                continue

            try:
                payload = json.loads(event.payload_json)
                for handler in topic_handlers:
                    await handler(payload, db)
                for global_handler in global_handlers:
                    await global_handler(payload, db, event.topic, event.id)
            except Exception as exc:  # noqa: BLE001 - a handler's failure must not take the dispatcher down
                event.attempts += 1
                event.last_error = str(exc)[:2000]
                event.next_attempt_at = now + timedelta(seconds=_backoff_seconds(event.attempts))
                logger.exception(
                    "event dispatcher: handler failed for event %s (topic=%s), attempt %d, retrying in %ds",
                    event.id, event.topic, event.attempts, _backoff_seconds(event.attempts),
                )
                events_dispatch_failed_total.inc(topic=event.topic)
                continue

            event.dispatched_at = now
            dispatched_ids.append(event.id)
            events_dispatched_total.inc(topic=event.topic)

        return dispatched_ids


async def run_event_dispatcher_loop(
    stop_event: asyncio.Event, poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS
) -> None:
    """Runs until stop_event is set. Each iteration opens its own DB
    session (not one held across the whole loop's lifetime), same
    reasoning as run_scheduler_loop."""
    while not stop_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                dispatched = await EventDispatcher.dispatch_pending(db)
                await db.commit()
                if dispatched:
                    logger.info("event dispatcher: dispatched %d event(s): %s", len(dispatched), dispatched)
        except Exception:
            # Same outer guard as run_scheduler_loop: a failure in the
            # polling infrastructure itself (e.g. a DB connectivity blip)
            # must not kill the background task permanently.
            logger.exception("event dispatcher: error dispatching pending events, will retry next interval")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval_seconds)
        except asyncio.TimeoutError:
            pass  # normal case: timed out waiting, loop again
