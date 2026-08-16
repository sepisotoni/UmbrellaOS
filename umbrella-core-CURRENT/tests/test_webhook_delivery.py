"""
tests/test_webhook_delivery.py — Tests for
services/webhooks/service.py::WebhookDeliveryService (the actual HTTP POST)
and services/events/subscribers.py::_deliver_webhooks (the global event
subscriber that wires delivery into the dispatcher's existing
attempts/backoff — see docs/design/public-rest-api-and-webhooks.md,
Decision 4).

httpx is mocked at the AsyncClient.post level, same pattern as
tests/test_ai_config.py, rather than hitting a real network endpoint.
"""
import hashlib
import hmac
import json

import httpx
import pytest

from services.events.bus import EventBus
from services.events.dispatcher import EventDispatcher
from services.webhooks.service import WebhookDeliveryError, WebhookDeliveryService, WebhookService


class _MockResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code


@pytest.mark.asyncio
async def test_deliver_sends_signed_payload_to_subscription_url(db_session, monkeypatch):
    calls = []

    async def mock_post(self, url, **kwargs):
        calls.append((url, kwargs))
        return _MockResponse(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    async with db_session() as db:
        subscription, secret = await WebhookService.create(
            db, topic="test.topic", url="https://example.com/hook", created_by=None
        )
        await db.commit()

        await WebhookDeliveryService.deliver(
            subscription, topic="test.topic", event_id="evt-1", payload={"a": 1}
        )

    assert len(calls) == 1
    url, kwargs = calls[0]
    assert url == "https://example.com/hook"
    assert kwargs["headers"]["X-Umbrella-Topic"] == "test.topic"
    assert kwargs["headers"]["X-Umbrella-Event-Id"] == "evt-1"

    body = kwargs["content"]
    expected_signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    assert kwargs["headers"]["X-Umbrella-Signature"] == expected_signature
    assert json.loads(body)["payload"] == {"a": 1}


@pytest.mark.asyncio
async def test_deliver_raises_on_non_2xx_response(db_session, monkeypatch):
    async def mock_post(self, url, **kwargs):
        return _MockResponse(500)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    async with db_session() as db:
        subscription, _ = await WebhookService.create(
            db, topic="test.topic", url="https://example.com/hook", created_by=None
        )
        await db.commit()

        with pytest.raises(WebhookDeliveryError):
            await WebhookDeliveryService.deliver(
                subscription, topic="test.topic", event_id="evt-2", payload={}
            )


@pytest.mark.asyncio
async def test_deliver_raises_on_connection_error(db_session, monkeypatch):
    async def mock_post(self, url, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    async with db_session() as db:
        subscription, _ = await WebhookService.create(
            db, topic="test.topic", url="https://example.com/hook", created_by=None
        )
        await db.commit()

        with pytest.raises(WebhookDeliveryError):
            await WebhookDeliveryService.deliver(
                subscription, topic="test.topic", event_id="evt-3", payload={}
            )


@pytest.fixture(autouse=True)
def _real_subscribers_registered():
    """Other test files (test_event_bus.py, test_event_dispatcher.py) reset
    the process-wide EventBus registry to empty in their own teardown, by
    design (they want a clean slate for the next test, per their own
    fixture). That means by the time this file's tests run, the real
    subscribers imported at app startup may already have been cleared out
    of the registry - so this fixture explicitly (re-)registers them at
    setup, not just at teardown, rather than assuming import-time
    registration is still intact when this test starts."""
    import services.events.subscribers as subscribers_module

    EventBus.reset_for_tests()
    EventBus.subscribe("staff_escalation.created", subscribers_module._log_staff_escalation_created)
    EventBus.subscribe_global(subscribers_module._deliver_webhooks)
    yield
    EventBus.reset_for_tests()


@pytest.mark.asyncio
async def test_dispatch_pending_delivers_to_registered_webhook_subscription(db_session, monkeypatch):
    """End-to-end: publish an event, dispatch it, and confirm the
    already-registered global webhook subscriber (imported at app startup
    via services.events) actually POSTs to a real WebhookSubscription row
    - not a test-only handler standing in for it."""
    calls = []

    async def mock_post(self, url, **kwargs):
        calls.append(url)
        return _MockResponse(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    async with db_session() as db:
        await WebhookService.create(
            db, topic="webhook.e2e.topic", url="https://example.com/e2e-hook", created_by=None
        )
        event = await EventBus.publish(db, topic="webhook.e2e.topic", payload={"hello": "world"})
        await db.commit()

        dispatched = await EventDispatcher.dispatch_pending(db)
        await db.commit()

        assert event.id in dispatched
        assert calls == ["https://example.com/e2e-hook"]


@pytest.mark.asyncio
async def test_dispatch_pending_retries_event_when_webhook_delivery_fails(db_session, monkeypatch):
    async def mock_post(self, url, **kwargs):
        return _MockResponse(500)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    async with db_session() as db:
        await WebhookService.create(
            db, topic="webhook.e2e.failure", url="https://example.com/down", created_by=None
        )
        event = await EventBus.publish(db, topic="webhook.e2e.failure", payload={})
        await db.commit()

        dispatched = await EventDispatcher.dispatch_pending(db)
        await db.commit()

        assert dispatched == []
        assert event.dispatched_at is None
        assert event.attempts == 1


@pytest.mark.asyncio
async def test_dispatch_pending_ignores_inactive_subscriptions(db_session, monkeypatch):
    calls = []

    async def mock_post(self, url, **kwargs):
        calls.append(url)
        return _MockResponse(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    async with db_session() as db:
        subscription, _ = await WebhookService.create(
            db, topic="webhook.inactive.topic", url="https://example.com/inactive", created_by=None
        )
        await WebhookService.update(db, subscription.id, active=False)
        event = await EventBus.publish(db, topic="webhook.inactive.topic", payload={})
        await db.commit()

        dispatched = await EventDispatcher.dispatch_pending(db)
        await db.commit()

        assert event.id in dispatched
        assert calls == []
