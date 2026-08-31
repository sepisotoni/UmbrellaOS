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


# ---------------------------------------------------------------------------
# FINDING-010 — SSRF protection: hostname resolution path
# ---------------------------------------------------------------------------
# test_capabilities_webhooks.py covers literal-IP URLs against the real
# validator with no mocking needed. This covers the hostname-resolution
# branch specifically (socket.getaddrinfo), mocked for determinism — a
# real DNS lookup in a unit test would make the test's outcome depend on
# network availability and an external hostname's current A/AAAA records,
# neither of which this test should be sensitive to.

from unittest.mock import patch
from services.webhooks.service import WebhookError, _validate_webhook_url


def test_validate_webhook_url_rejects_hostname_resolving_to_private_ip():
    """A hostname (not a literal IP) that resolves to an internal address
    must be rejected — this is the case a naive 'does the string contain
    127.0.0.1' check would miss entirely, e.g. an attacker-controlled
    domain whose DNS record points at an internal target."""
    fake_resolution = [
        (2, 1, 6, "", ("10.0.0.99", 0)),  # AF_INET, SOCK_STREAM, private IP
    ]
    with patch("services.webhooks.service.socket.getaddrinfo", return_value=fake_resolution):
        with pytest.raises(WebhookError, match="disallowed address"):
            _validate_webhook_url("http://attacker-controlled.example/hook")


def test_validate_webhook_url_rejects_if_any_resolved_address_is_private():
    """DNS can return multiple A/AAAA records. Rejecting only if the FIRST
    address is bad would miss a hostname that round-robins between a public
    decoy address and an internal one — an attacker only needs one request
    to land on the bad address. Every resolved address must be checked."""
    fake_resolution = [
        (2, 1, 6, "", ("8.8.8.8", 0)),      # public — would pass alone
        (2, 1, 6, "", ("192.168.1.1", 0)),  # private — must still block the whole URL
    ]
    with patch("services.webhooks.service.socket.getaddrinfo", return_value=fake_resolution):
        with pytest.raises(WebhookError, match="disallowed address"):
            _validate_webhook_url("http://multi-record.example/hook")


def test_validate_webhook_url_allows_hostname_resolving_to_public_ips_only():
    fake_resolution = [
        (2, 1, 6, "", ("8.8.8.8", 0)),
        (2, 1, 6, "", ("1.1.1.1", 0)),
    ]
    with patch("services.webhooks.service.socket.getaddrinfo", return_value=fake_resolution):
        _validate_webhook_url("http://genuinely-public.example/hook")  # must not raise


def test_validate_webhook_url_rejects_unresolvable_hostname():
    """A hostname that fails to resolve at all should be rejected with a
    clear message rather than an unhandled socket.gaierror bubbling up as
    a 500 — this is a normal, expected input (a typo'd domain, a domain
    that doesn't exist yet), not an exceptional condition."""
    import socket
    with patch("services.webhooks.service.socket.getaddrinfo", side_effect=socket.gaierror("nodename nor servname provided")):
        with pytest.raises(WebhookError, match="could not resolve"):
            _validate_webhook_url("http://this-domain-does-not-exist-xyz123.invalid/hook")


def test_validate_webhook_url_rejects_missing_scheme():
    with pytest.raises(WebhookError, match="http:// or https://"):
        _validate_webhook_url("not-a-url-at-all")


def test_validate_webhook_url_rejects_url_with_no_hostname():
    with pytest.raises(WebhookError, match="valid hostname"):
        _validate_webhook_url("http:///no-host-here")
