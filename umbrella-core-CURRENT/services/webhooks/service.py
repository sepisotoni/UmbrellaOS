"""
services/webhooks/service.py — CRUD for WebhookSubscription rows, plus the
actual HTTP delivery of a signed payload to one subscription.

Split deliberately into two responsibilities in one file (CRUD is trivial
enough not to warrant its own module; delivery is the part with real
behavior worth documenting):

- WebhookService: plain CRUD, called by capabilities/webhooks.py. No retry
  logic here — see docs/design/public-rest-api-and-webhooks.md, Decision 4
  for why retries are the event dispatcher's job, not this service's.
- WebhookDeliveryService.deliver: one POST, one attempt, no internal retry
  loop. A failed delivery raises WebhookDeliveryError; the caller (the
  global event subscriber in services/events/subscribers.py) lets that
  propagate so the *event dispatcher's* existing attempts/backoff handles
  the retry, exactly as instructed.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import secrets
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import AppException, ResourceNotFoundException
from models.webhook import WebhookSubscription

DELIVERY_TIMEOUT_SECONDS = 5.0


class WebhookError(AppException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, "WEBHOOK_ERROR", status_code)


class WebhookDeliveryError(Exception):
    """Raised when a single subscription's delivery fails (non-2xx
    response, timeout, or connection error). Left uncaught by
    services/events/subscribers.py's global handler so it feeds the event
    dispatcher's existing attempts/backoff — see this package's module
    docstring."""


def _generate_secret() -> str:
    return secrets.token_urlsafe(32)


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _validate_webhook_url(url: str) -> None:
    """Reject webhook URLs that could be used for SSRF.

    FIX (FINDING-010): create/update only checked the URL scheme, so any
    http(s) destination — including loopback (127.0.0.1), link-local
    (169.254.169.254, the AWS/GCP/Azure cloud metadata endpoint on every
    major cloud provider), and RFC1918 private ranges — was accepted and
    later POSTed to by an authenticated operator via 'test delivery' or by
    the real event dispatcher on every matching topic event. A webhook
    pointed at the metadata endpoint or an internal admin port becomes a
    live SSRF primitive: whoever holds webhooks.subscription.manage can
    make Core issue arbitrary GET-adjacent requests to internal-only hosts.

    This resolves the hostname via DNS and checks every results against
    ipaddress's is_private / is_loopback / is_link_local / is_reserved /
    is_multicast classifications — not a string-match blocklist, which a
    numeric-IP URL or an alternate encoding (decimal, octal, IPv6-mapped
    IPv4) could trivially bypass. Rejects if ANY resolved address is
    disallowed, since DNS can return multiple records and an attacker only
    needs one of them to be internal (DNS rebinding is a known bypass for
    single-address checks; checking all resolved addresses at
    creation/update time doesn't fully close the TOCTOU gap against
    rebinding at delivery time, but it does close the far simpler direct
    attack of just pointing the URL at an internal literal or hostname).
    """
    if not url.startswith(("http://", "https://")):
        raise WebhookError("url must be an http:// or https:// URL")

    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise WebhookError("url must have a valid hostname")

    try:
        # getaddrinfo resolves both A and AAAA records; this also runs for
        # literal IPs (loopback on it), so one path covers hostnames and
        # numeric addresses alike.
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise WebhookError(f"could not resolve webhook hostname {hostname!r}: {exc}")

    for family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise WebhookError(
                f"webhook url resolves to a disallowed address ({ip_str}) — "
                "internal, private, loopback, and link-local destinations "
                "(including cloud metadata endpoints) are not permitted"
            )


class WebhookService:
    @staticmethod
    async def create(
        db: AsyncSession, *, topic: str, url: str, created_by: str | None
    ) -> tuple[WebhookSubscription, str]:
        """Returns (subscription, plaintext_secret). Same one-time-reveal
        shape as ApiKeyService.create_api_key: the secret is stored (it has
        to be, to sign future deliveries — see models/webhook.py's module
        docstring) but the capability layer should still only ever show it
        to the caller at creation time, not on subsequent list calls."""
        _validate_webhook_url(url)
        subscription = WebhookSubscription(
            topic=topic,
            url=url,
            secret=secret,
            created_by=created_by,
        )
        db.add(subscription)
        await db.flush()
        return subscription, secret

    @staticmethod
    async def list_all(db: AsyncSession, *, topic: str | None = None) -> list[WebhookSubscription]:
        stmt = select(WebhookSubscription)
        if topic is not None:
            stmt = stmt.where(WebhookSubscription.topic == topic)
        stmt = stmt.order_by(WebhookSubscription.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def list_active_for_topic(db: AsyncSession, topic: str) -> list[WebhookSubscription]:
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.topic == topic, WebhookSubscription.active.is_(True)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get(db: AsyncSession, subscription_id: str) -> WebhookSubscription:
        subscription = await db.get(WebhookSubscription, subscription_id)
        if subscription is None:
            raise ResourceNotFoundException("webhook subscription", subscription_id)
        return subscription

    @staticmethod
    async def update(
        db: AsyncSession,
        subscription_id: str,
        *,
        url: str | None = None,
        active: bool | None = None,
    ) -> WebhookSubscription:
        subscription = await WebhookService.get(db, subscription_id)
        if url is not None:
            _validate_webhook_url(url)
            subscription.url = url
        if active is not None:
            subscription.active = active
        await db.flush()
        return subscription

    @staticmethod
    async def delete(db: AsyncSession, subscription_id: str) -> None:
        subscription = await WebhookService.get(db, subscription_id)
        await db.delete(subscription)
        await db.flush()


class WebhookDeliveryService:
    @staticmethod
    async def deliver(subscription: WebhookSubscription, *, topic: str, event_id: str, payload: dict) -> None:
        """One POST, one attempt. Raises WebhookDeliveryError on any
        non-2xx response, timeout, or connection error - never retries
        internally, see module docstring.

        FIX (FINDING-10, defense in depth): re-validates the destination
        immediately before sending, not just at create/update time. Two
        gaps this closes that create/update-time validation alone cannot:
        (1) rows created before this validation existed are grandfathered
        with no re-check unless they're later edited, and (2) DNS
        rebinding — a hostname that resolved to a public IP when the
        subscription was saved can be repointed to an internal address by
        the time delivery actually happens. This does not fully eliminate
        rebinding (there's still a gap between this check and the actual
        httpx connection a moment later), but it meaningfully shrinks the
        window on every single delivery rather than only at save time.
        """
        import json

        try:
            _validate_webhook_url(subscription.url)
        except WebhookError as exc:
            raise WebhookDeliveryError(
                f"delivery to subscription {subscription.id} blocked: {exc}"
            ) from exc

        body = json.dumps(
            {
                "topic": topic,
                "event_id": event_id,
                "delivered_at": datetime.now(timezone.utc).isoformat(),
                "payload": payload,
            }
        ).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "X-Umbrella-Topic": topic,
            "X-Umbrella-Event-Id": event_id,
            "X-Umbrella-Signature": _sign(subscription.secret, body),
        }

        try:
            async with httpx.AsyncClient(timeout=DELIVERY_TIMEOUT_SECONDS) as client:
                response = await client.post(subscription.url, content=body, headers=headers)
        except httpx.HTTPError as exc:
            raise WebhookDeliveryError(
                f"delivery to subscription {subscription.id} ({subscription.url}) failed: {exc}"
            ) from exc

        if response.status_code >= 300:
            raise WebhookDeliveryError(
                f"delivery to subscription {subscription.id} ({subscription.url}) "
                f"returned status {response.status_code}"
            )
