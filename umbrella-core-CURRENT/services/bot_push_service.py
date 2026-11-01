"""
services/bot_push_service.py — Fire-and-forget push from umbrella-core to
the Discord bot's webhook endpoint (Phase 16B Task B).

The bot registers its callback URL on startup via POST /api/v1/bot/register.
Core reads that URL from the bot_registration table and POSTs events to it.

Authentication: same PBKDF2-HMAC-SHA256 scheme as Task A but reversed —
core authenticates TO the bot using the shared admin_key as the secret.
The bot verifies the MAC before processing any event.

Failure handling: any exception (network error, timeout, bot down) is logged
and swallowed. This is intentionally fire-and-forget — push is a best-effort
real-time optimisation; the bot's fallback poll loop (slowed to 5 min in
Task B) ensures eventual consistency even when push fails.

Callback URL caching: the DB row is cached in memory for 60 seconds to avoid
a DB hit on every event. A bot restart overwrites the row; the cache expires
and the new URL is picked up within 60 s.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import time

import httpx
from urllib.parse import urlparse

from config import get_settings
from database import AsyncSessionLocal
from models.bot_registration import BotRegistration
from services.webhooks.service import WebhookError, _validate_webhook_url

logger = logging.getLogger(__name__)
settings = get_settings()

# In-memory cache: (url, expires_at) or (None, 0) when no registration exists.
_cached_url: str | None = None
_cache_expires_at: float = 0.0
_CACHE_TTL = 60.0  # seconds


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


def _make_push_headers(target: str, body: bytes) -> dict[str, str]:
    """Create a request-bound v2 MAC for Core -> bot webhook delivery."""
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = (
        f"POST\n{target}\n{timestamp}\n{nonce}\n{body_hash}"
    ).encode("utf-8")
    mac = hmac.new(
        settings.admin_key.encode("utf-8"), canonical, hashlib.sha256
    ).hexdigest()
    return {
        "X-Auth-Version": "2",
        "X-Auth-MAC": mac,
        "X-Auth-Timestamp": timestamp,
        "X-Auth-Nonce": nonce,
        "Content-Type": "application/json",
    }


async def push_event(event: str, payload: dict) -> bool:
    """
    Fire-and-forget push of an event to the bot's webhook.

    Call this after any state change the bot should know about immediately.
    Never raises — failures are logged at WARNING level and the fallback
    poll loop provides eventual delivery.
    """
    url = await _get_callback_url()
    if not url:
        logger.debug("No bot registration found; skipping push for event %s", event)
        return False

    try:
        # Existing DB rows may predate registration validation; never send
        # a privileged MAC or event payload to a private/internal address.
        # DNS resolution and PBKDF2 are blocking operations.
        await asyncio.to_thread(_validate_webhook_url, url)
        body = json.dumps(
            {"event": event, "payload": payload},
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        parsed = urlparse(url)
        target = parsed.path or "/"
        if parsed.query:
            target += "?" + parsed.query
        headers = _make_push_headers(target, body)
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            response = await client.post(
                url,
                content=body,
                headers=headers,
            )
        if response.status_code >= 400:
            logger.warning(
                "Bot push for event %s returned HTTP %s", event, response.status_code
            )
            return False
        return True
    except (WebhookError, ValueError):
        logger.warning("Bot push blocked: unsafe registered callback for event %s", event)
        return False
    except Exception:
        logger.warning("Bot push failed for event %s", event, exc_info=True)
        return False


def invalidate_cache() -> None:
    """Force the next push to re-read the callback URL from the DB.
    Called after a successful bot registration upsert so pushes immediately
    use the new URL without waiting for the 60-second TTL to expire."""
    global _cache_expires_at
    _cache_expires_at = 0.0
