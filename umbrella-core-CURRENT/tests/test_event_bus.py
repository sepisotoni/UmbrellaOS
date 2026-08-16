"""
tests/test_event_bus.py — Tests for services/events/bus.py: EventBus.publish
writes a real row in the caller's transaction, and subscribe/subscribers_for
behave as a genuine process-wide registry.
"""
import json

import pytest

from models.events import Event
from services.events.bus import EventBus


@pytest.fixture(autouse=True)
def _reset_event_bus():
    EventBus.reset_for_tests()
    yield
    EventBus.reset_for_tests()


@pytest.mark.asyncio
async def test_publish_writes_event_row_with_encoded_payload(db_session):
    async with db_session() as db:
        event = await EventBus.publish(db, topic="test.topic", payload={"a": 1, "b": "two"})
        await db.commit()

        assert event.id is not None
        assert event.topic == "test.topic"
        assert json.loads(event.payload_json) == {"a": 1, "b": "two"}
        assert event.dispatched_at is None
        assert event.attempts == 0

        fetched = await db.get(Event, event.id)
        assert fetched is not None
        assert fetched.topic == "test.topic"


@pytest.mark.asyncio
async def test_publish_does_not_commit_the_session(db_session):
    """The whole point of the outbox pattern: publish() only flushes, so a
    caller that rolls back its own transaction rolls the event back too."""
    async with db_session() as db:
        event = await EventBus.publish(db, topic="test.topic", payload={})
        event_id = event.id
        await db.rollback()

    async with db_session() as db:
        fetched = await db.get(Event, event_id)
        assert fetched is None


def test_subscribe_registers_handler_for_topic():
    async def handler(payload, db):
        pass

    EventBus.subscribe("test.topic", handler)
    assert EventBus.subscribers_for("test.topic") == [handler]
    assert EventBus.subscribers_for("other.topic") == []


def test_subscribe_supports_multiple_handlers_same_topic():
    async def handler_one(payload, db):
        pass

    async def handler_two(payload, db):
        pass

    EventBus.subscribe("test.topic", handler_one)
    EventBus.subscribe("test.topic", handler_two)
    assert EventBus.subscribers_for("test.topic") == [handler_one, handler_two]


def test_subscribe_global_registers_a_handler_reachable_regardless_of_topic():
    async def global_handler(payload, db, topic, event_id):
        pass

    EventBus.subscribe_global(global_handler)
    assert EventBus.global_subscribers() == [global_handler]


def test_global_subscribers_are_independent_of_per_topic_subscribers():
    async def topic_handler(payload, db):
        pass

    async def global_handler(payload, db, topic, event_id):
        pass

    EventBus.subscribe("test.topic", topic_handler)
    EventBus.subscribe_global(global_handler)

    assert EventBus.subscribers_for("test.topic") == [topic_handler]
    assert EventBus.global_subscribers() == [global_handler]
    # A global subscriber does not also show up as a per-topic subscriber
    # for any topic — it's a separate registration list, not a special
    # topic string.
    assert EventBus.subscribers_for("some.other.topic") == []
