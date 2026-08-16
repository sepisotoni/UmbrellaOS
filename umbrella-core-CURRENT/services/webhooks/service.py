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
import secrets
from datetime import datetime, timezone

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
        if not url.startswith(("http://", "https://")):
            raise WebhookError("url must be an http:// or https:// URL")

        secret = _generate_secret()
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
            if not url.startswith(("http://", "https://")):
                raise WebhookError("url must be an http:// or https:// URL")
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
        internally, see module docstring."""
        import json

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
