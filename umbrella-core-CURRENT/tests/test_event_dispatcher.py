"""
tests/test_event_dispatcher.py — Tests for services/events/dispatcher.py.

Covers dispatch_pending's core logic directly (mirrors
tests/test_scheduler_service.py's approach to SchedulerService.run_due_schedules)
and run_event_dispatcher_loop's stop/iteration behavior (mirrors
tests/test_scheduler_loop.py exactly).
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from services.events.bus import EventBus
from services.events.dispatcher import EventDispatcher, run_event_dispatcher_loop


@pytest.fixture(autouse=True)
def _reset_event_bus():
    EventBus.reset_for_tests()
    yield
    EventBus.reset_for_tests()


@pytest.mark.asyncio
async def test_dispatch_pending_marks_dispatched_when_no_subscribers(db_session):
    async with db_session() as db:
        event = await EventBus.publish(db, topic="no.subscribers", payload={})
        await db.commit()

        dispatched = await EventDispatcher.dispatch_pending(db)
        await db.commit()

        assert event.id in dispatched
        assert event.dispatched_at is not None


@pytest.mark.asyncio
async def test_dispatch_pending_calls_subscriber_and_marks_dispatched(db_session):
    received = []

    async def handler(payload, db):
        received.append(payload)

    EventBus.subscribe("with.subscriber", handler)

    async with db_session() as db:
        event = await EventBus.publish(db, topic="with.subscriber", payload={"x": 1})
        await db.commit()

        dispatched = await EventDispatcher.dispatch_pending(db)
        await db.commit()

        assert event.id in dispatched
        assert event.dispatched_at is not None
        assert received == [{"x": 1}]


@pytest.mark.asyncio
async def test_dispatch_pending_calls_every_subscriber_for_topic(db_session):
    calls = []

    async def handler_one(payload, db):
        calls.append("one")

    async def handler_two(payload, db):
        calls.append("two")

    EventBus.subscribe("multi.subscriber", handler_one)
    EventBus.subscribe("multi.subscriber", handler_two)

    async with db_session() as db:
        await EventBus.publish(db, topic="multi.subscriber", payload={})
        await db.commit()

        await EventDispatcher.dispatch_pending(db)
        await db.commit()

        assert calls == ["one", "two"]


@pytest.mark.asyncio
async def test_dispatch_pending_retries_on_handler_failure_with_backoff(db_session):
    async def failing_handler(payload, db):
        raise ValueError("boom")

    EventBus.subscribe("failing.topic", failing_handler)

    async with db_session() as db:
        event = await EventBus.publish(db, topic="failing.topic", payload={})
        await db.commit()

        now = datetime.now(timezone.utc)
        dispatched = await EventDispatcher.dispatch_pending(db, now=now)
        await db.commit()

        assert dispatched == []
        assert event.dispatched_at is None
        assert event.attempts == 1
        assert event.last_error is not None
        assert "boom" in event.last_error
        assert event.next_attempt_at is not None
        assert event.next_attempt_at > now


@pytest.mark.asyncio
async def test_dispatch_pending_skips_row_still_in_backoff_window(db_session):
    async def failing_handler(payload, db):
        raise ValueError("still failing")

    EventBus.subscribe("backoff.topic", failing_handler)

    async with db_session() as db:
        event = await EventBus.publish(db, topic="backoff.topic", payload={})
        await db.commit()

        now = datetime.now(timezone.utc)
        await EventDispatcher.dispatch_pending(db, now=now)
        await db.commit()
        assert event.attempts == 1

        # Immediately retrying (before the backoff window elapses) must
        # not re-invoke the handler or increment attempts again.
        still_now = now + timedelta(seconds=1)
        dispatched = await EventDispatcher.dispatch_pending(db, now=still_now)
        await db.commit()

        assert dispatched == []
        assert event.attempts == 1


@pytest.mark.asyncio
async def test_dispatch_pending_eventually_succeeds_after_backoff_elapses(db_session):
    attempts_seen = []

    async def flaky_handler(payload, db):
        attempts_seen.append(True)
        if len(attempts_seen) < 2:
            raise ValueError("fails once")

    EventBus.subscribe("flaky.topic", flaky_handler)

    async with db_session() as db:
        event = await EventBus.publish(db, topic="flaky.topic", payload={})
        await db.commit()

        now = datetime.now(timezone.utc)
        await EventDispatcher.dispatch_pending(db, now=now)
        await db.commit()
        assert event.dispatched_at is None

        later = now + timedelta(seconds=60)  # past the backoff window for attempt 1
        dispatched = await EventDispatcher.dispatch_pending(db, now=later)
        await db.commit()

        assert dispatched == [event.id]
        assert event.dispatched_at is not None


@pytest.mark.asyncio
async def test_dispatch_pending_only_touches_undispatched_rows(db_session):
    calls = []

    async def handler(payload, db):
        calls.append(payload)

    EventBus.subscribe("already.dispatched", handler)

    async with db_session() as db:
        event = await EventBus.publish(db, topic="already.dispatched", payload={})
        await db.commit()

        await EventDispatcher.dispatch_pending(db)
        await db.commit()
        assert len(calls) == 1

        # A second call must not re-dispatch the same, now-dispatched row.
        dispatched_again = await EventDispatcher.dispatch_pending(db)
        await db.commit()

        assert dispatched_again == []
        assert len(calls) == 1


@pytest.mark.asyncio
async def test_dispatch_pending_calls_global_subscriber_with_topic(db_session):
    received = []

    async def global_handler(payload, db, topic, event_id):
        received.append((payload, topic, event_id))

    EventBus.subscribe_global(global_handler)

    async with db_session() as db:
        event = await EventBus.publish(db, topic="global.topic", payload={"x": 1})
        await db.commit()

        dispatched = await EventDispatcher.dispatch_pending(db)
        await db.commit()

        assert event.id in dispatched
        assert received == [({"x": 1}, "global.topic", event.id)]


@pytest.mark.asyncio
async def test_dispatch_pending_calls_global_subscriber_for_topic_with_no_topic_subscribers(db_session):
    """A global subscriber (webhooks) must still run for a topic that has
    no per-topic in-process subscriber registered — that's the entire
    point of it existing rather than requiring static per-topic
    pre-registration."""
    received = []

    async def global_handler(payload, db, topic, event_id):
        received.append(topic)

    EventBus.subscribe_global(global_handler)

    async with db_session() as db:
        event = await EventBus.publish(db, topic="nobody.subscribed.per_topic", payload={})
        await db.commit()

        dispatched = await EventDispatcher.dispatch_pending(db)
        await db.commit()

        assert event.id in dispatched
        assert received == ["nobody.subscribed.per_topic"]


@pytest.mark.asyncio
async def test_dispatch_pending_retries_whole_event_when_global_subscriber_fails(db_session):
    async def failing_global_handler(payload, db, topic, event_id):
        raise ValueError("webhook delivery failed")

    EventBus.subscribe_global(failing_global_handler)

    async with db_session() as db:
        event = await EventBus.publish(db, topic="global.failure", payload={})
        await db.commit()

        now = datetime.now(timezone.utc)
        dispatched = await EventDispatcher.dispatch_pending(db, now=now)
        await db.commit()

        assert dispatched == []
        assert event.dispatched_at is None
        assert event.attempts == 1
        assert "webhook delivery failed" in event.last_error
        assert event.next_attempt_at is not None


@pytest.mark.asyncio
async def test_loop_stops_promptly_when_stop_event_is_set():
    stop_event = asyncio.Event()
    task = asyncio.create_task(run_event_dispatcher_loop(stop_event, poll_interval_seconds=60))

    await asyncio.sleep(0.05)
    stop_event.set()

    await asyncio.wait_for(task, timeout=2.0)
    assert task.done()


@pytest.mark.asyncio
async def test_loop_runs_at_least_one_iteration_before_stopping(monkeypatch):
    calls = []

    async def fake_dispatch_pending(db, batch_size=50, now=None):
        calls.append(True)
        return []

    import services.events.dispatcher as dispatcher_module

    monkeypatch.setattr(
        dispatcher_module.EventDispatcher, "dispatch_pending", staticmethod(fake_dispatch_pending)
    )

    stop_event = asyncio.Event()
    task = asyncio.create_task(run_event_dispatcher_loop(stop_event, poll_interval_seconds=60))
    await asyncio.sleep(0.1)
    stop_event.set()
    await asyncio.wait_for(task, timeout=2.0)

    assert len(calls) >= 1
