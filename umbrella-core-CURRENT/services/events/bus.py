"""
services/events/bus.py — In-process outbox event bus (Phase 7, Decision 1
from handoff-to-new-session-phase7-START.md).

Two separate mechanisms, deliberately not conflated:

1. EventBus.publish(db, topic=..., payload=...) — writes an Event row
   (models/events.py) into the SAME db session/transaction the caller is
   already using for its own state change. It never calls db.commit()
   itself, exactly like every repository-style write in this codebase
   (see services/moderation_intelligence/repository.py's own comment on
   this) — commit happens once, at the request/capability-call boundary
   (database/engine.py's get_db()), which is what makes "the event can
   never be dropped between the state change committing and the event
   being recorded" true: they're literally the same commit.

2. EventBus.subscribe(topic, handler) — registers an in-process callback
   for a topic, in a process-wide, module-level registry populated at
   import time (mirrors registry/registry.py's CapabilitySpec
   registration pattern: side-effect imports at startup, not a database
   table of subscriptions). This only reaches subscribers living inside
   THIS process. umbrella-discord, a separate process, cannot register a
   handler here — it isn't a candidate "in-process subscriber" no matter
   how the topic is named. Cross-process consumption (Discord, registered
   webhooks) is a distinct problem — see EventBus.subscribe_global below
   for how webhooks (Phase 7 item 2) actually reach the bus.

3. EventBus.subscribe_global(handler) — Phase 7 addition
   (docs/design/public-rest-api-and-webhooks.md, Decision 4). A handler
   registered here runs for EVERY dispatched event regardless of topic,
   and receives `(payload, db, topic, event_id)` rather than per-topic
   handlers' `(payload, db)` — it needs `topic` because, unlike a
   per-topic subscriber, it doesn't already know which topic it's being
   invoked for, and `event_id` because a cross-process consumer (a
   webhook receiver) needs a stable id to dedupe on when the same event
   is retried, which a per-topic in-process handler has never needed
   since it isn't crossing a process boundary. This exists because
   registered webhooks are admin-created at runtime for arbitrary topics
   the bus has no way to statically pre-register for at import time the
   way built-in subscribers can; a global subscriber instead re-derives
   "who cares about this topic" from the WebhookSubscription table on
   every event, which needs no startup rehydration and can never go
   stale. Deliberately a separate registration list from per-topic
   subscribers, not a special topic string like "*", so existing
   per-topic handler signatures and every existing dispatcher test are
   completely unaffected by this addition.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from models.events import Event

logger = logging.getLogger(__name__)

# A handler receives the decoded payload and the same db session the
# dispatcher is using for this batch — consistent with every other service
# in this codebase taking `db` from the caller rather than opening its own
# session (see services/investigation/tools.py's module docstring for the
# same convention stated explicitly elsewhere).
EventHandler = Callable[[dict, AsyncSession], Awaitable[None]]

# A global handler additionally receives the event's topic and id — see
# class 3 in the module docstring above for why.
GlobalEventHandler = Callable[[dict, AsyncSession, str, str], Awaitable[None]]

_subscribers: dict[str, list[EventHandler]] = {}
_global_subscribers: list[GlobalEventHandler] = []


class EventBus:
    @staticmethod
    async def publish(db: AsyncSession, *, topic: str, payload: dict) -> Event:
        """Writes an Event row and flushes (not commits) it, so it's
        visible to anything else in this same transaction but still rides
        along with the caller's own eventual commit/rollback."""
        event = Event(
            id=str(uuid.uuid4()),
            topic=topic,
            payload_json=json.dumps(payload),
        )
        db.add(event)
        await db.flush()
        return event

    @staticmethod
    def subscribe(topic: str, handler: EventHandler) -> None:
        _subscribers.setdefault(topic, []).append(handler)

    @staticmethod
    def subscribe_global(handler: GlobalEventHandler) -> None:
        _global_subscribers.append(handler)

    @staticmethod
    def subscribers_for(topic: str) -> list[EventHandler]:
        return list(_subscribers.get(topic, []))

    @staticmethod
    def global_subscribers() -> list[GlobalEventHandler]:
        return list(_global_subscribers)

    @staticmethod
    def reset_for_tests() -> None:
        """Test-only: clears the module-level registry. Without this, one
        test's subscribe() calls leak into every later test in the same
        process (the registry is process-wide by design, per this
        module's docstring) - tests/test_event_bus.py and
        tests/test_event_dispatcher.py call this in a fixture."""
        _subscribers.clear()
        _global_subscribers.clear()
