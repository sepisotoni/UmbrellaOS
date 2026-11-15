"""
services/bot_push_service.py — Core-to-bot webhook delivery and short-lived outbox.

The bot registers its callback URL on startup via POST /api/v1/bot/register.
Core reads that URL from the bot_registration table and POSTs events to it.

Authentication: same PBKDF2-HMAC-SHA256 scheme as Task A but reversed —
core authenticates TO the bot using the shared admin_key as the secret.
The bot verifies the MAC before processing any event.

Dashboard broadcasts are persisted before the callback is attempted. The bot
acknowledges handled events and also polls the outbox through runtime-state;
unacknowledged items expire after 24 hours and acknowledged receipts after
one hour.

Callback URL caching: the DB row is cached in memory for 60 seconds to avoid
a DB hit on every event. A bot restart overwrites the row; the cache expires
and the new URL is picked up within 60 s.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import AsyncSessionLocal
from models.bot_pending_event import BotPendingEvent
from models.bot_registration import BotRegistration

logger = logging.getLogger(__name__)
settings = get_settings()

# In-memory cache: (url, expires_at) or (None, 0) when no registration exists.
_cached_url: str | None = None
_cache_expires_at: float = 0.0
_CACHE_TTL = 60.0  # seconds
PENDING_EVENT_TTL = timedelta(hours=24)
ACKNOWLEDGED_EVENT_RETENTION = timedelta(hours=1)
PENDING_EVENT_LEASE = timedelta(minutes=2)


async def _get_callback_url() -> str | None:
    """Return the registered bot callback URL, using a 60-second cache."""
    global _cached_url, _cache_expires_at
    now = time.monotonic()
    if now < _cache_expires_at:
        return _cached_url

    async with AsyncSessionLocal() as db:
        row = await db.get(BotRegistration, 1)
    _cached_url = row.callback_url if row else None
    _cache_expires_at = now + _CACHE_TTL
    return _cached_url


async def enqueue_pending_event(
    db: AsyncSession, event: str, payload: dict
) -> BotPendingEvent:
    """Persist an event with bounded retention before attempting callback delivery."""
    now = datetime.now(timezone.utc)
    await db.execute(
        delete(BotPendingEvent).where(BotPendingEvent.expires_at <= now)
    )
    row = BotPendingEvent(
        event=event,
        payload=payload,
        created_at=now,
        expires_at=now + PENDING_EVENT_TTL,
    )
    db.add(row)
    await db.flush()
    return row


async def claim_pending_events(
    db: AsyncSession, *, limit: int = 25
) -> list[BotPendingEvent]:
    """Lease unacknowledged events for the bot's conditional runtime poll."""
    now = datetime.now(timezone.utc)
    await db.execute(
        delete(BotPendingEvent).where(BotPendingEvent.expires_at <= now)
    )
    result = await db.scalars(
        select(BotPendingEvent)
        .where(
            BotPendingEvent.acknowledged_at.is_(None),
            BotPendingEvent.expires_at > now,
            or_(
                BotPendingEvent.locked_until.is_(None),
                BotPendingEvent.locked_until <= now,
            ),
        )
        .order_by(BotPendingEvent.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    rows = list(result.all())
    for row in rows:
        row.locked_until = now + PENDING_EVENT_LEASE
    await db.flush()
    return rows


async def acknowledge_pending_event(db: AsyncSession, event_id: str) -> bool:
    """Acknowledge delivery; retain the receipt briefly, then purge it."""
    row = await db.get(BotPendingEvent, event_id)
    if row is None:
        return False
    now = datetime.now(timezone.utc)
    if _as_utc(row.expires_at) <= now:
        await db.delete(row)
        return False
    if row.acknowledged_at is None:
        row.acknowledged_at = now
        row.expires_at = now + ACKNOWLEDGED_EVENT_RETENTION
    row.locked_until = None
    await db.flush()
    return True


def _make_push_headers() -> dict[str, str]:
    """Derive a PBKDF2-HMAC-SHA256 MAC for authenticating to the bot."""
    ts = int(time.time())
    mac = hashlib.pbkdf2_hmac(
        "sha256",
        settings.admin_key.encode(),
        str(ts).encode(),
        100_000,
        dklen=32,
    ).hex()
    return {"X-Auth-MAC": mac, "X-Auth-Timestamp": str(ts)}


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def push_event(event: str, payload: dict) -> bool:
    """
    Push an event to the bot's webhook and report whether it was accepted.

    Durable events must already be in the outbox before this is called; the
    bot acknowledges successful handling and also polls the outbox.
    """
    url = await _get_callback_url()
    if not url:
        logger.debug("No bot registration found; skipping push for event %s", event)
        return False

    headers = _make_push_headers()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                url,
                json={"event": event, "payload": payload},
                headers=headers,
            )
        if not 200 <= response.status_code < 300:
            logger.warning(
                "Bot push for event %s returned HTTP %s", event, response.status_code
            )
            return False
        return True
    except httpx.HTTPError:
        logger.warning("Bot push failed for event %s", event, exc_info=True)
        return False


def invalidate_cache() -> None:
    """Force the next push to re-read the callback URL from the DB.
    Called after a successful bot registration upsert so pushes immediately
    use the new URL without waiting for the 60-second TTL to expire."""
    global _cache_expires_at
    _cache_expires_at = 0.0
