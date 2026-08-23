"""
bot/webhook_server.py — Lightweight aiohttp HTTP server that receives
push events from umbrella-core (Phase 16B Task B).

Runs inside the same process as the Discord bot on BOT_CALLBACK_PORT
(default 8080). Core authenticates each request with the same PBKDF2-
HMAC-SHA256 scheme used for bot→core calls in Task A (roles reversed:
core is the sender, bot is the verifier).

Verification steps (per request):
1. Read X-Auth-Timestamp. Reject if missing.
2. Reject if |now - timestamp| > 30 seconds (replay window).
3. Derive PBKDF2-HMAC-SHA256 MAC from shared secret and timestamp.
4. Compare with hmac.compare_digest(). Reject on mismatch.

On valid events, the server dispatches to registered handler coroutines
via a simple dict keyed by event type. Cogs register handlers through
WebhookServer.register_handler() at cog load time.

aiohttp>=3.9.0 is already in requirements.txt.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiohttp import web

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class WebhookServer:
    """Manages the aiohttp application and event handler registry."""

    def __init__(self, shared_secret: str, port: int = 8080) -> None:
        self._secret = shared_secret
        self._port = port
        self._handlers: dict[str, EventHandler] = {}
        self._runner: web.AppRunner | None = None

    def register_handler(self, event: str, handler: EventHandler) -> None:
        """Register a coroutine to be called when *event* arrives.
        The handler receives the payload dict. Overwriting an existing
        handler is allowed (last write wins)."""
        self._handlers[event] = handler

    def _verify_mac(self, mac: str | None, timestamp: str | None) -> bool:
        """Return True if the MAC is valid and within the 30-second window."""
        if not mac or not timestamp:
            return False
        try:
            ts = int(timestamp)
        except ValueError:
            return False
        if abs(time.time() - ts) > 30:
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            self._secret.encode(),
            str(ts).encode(),
            100_000,
            dklen=32,
        ).hex()
        return hmac.compare_digest(expected, mac)

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        mac = request.headers.get("X-Auth-MAC")
        timestamp = request.headers.get("X-Auth-Timestamp")

        if not self._verify_mac(mac, timestamp):
            logger.warning("Rejected webhook request — bad or missing MAC/timestamp")
            return web.Response(status=401, text="Unauthorized")

        try:
            body = await request.json()
        except Exception:
            return web.Response(status=400, text="Invalid JSON")

        event = body.get("event")
        payload = body.get("payload", {})

        if not event:
            return web.Response(status=400, text="Missing 'event' field")

        handler = self._handlers.get(event)
        if handler is None:
            logger.debug("No handler registered for event %s — ignoring", event)
            return web.Response(status=200, text="OK (no handler)")

        try:
            await handler(payload)
        except Exception:
            logger.exception("Handler for event %s raised an exception", event)
            # Still return 200: core's fire-and-forget doesn't retry, so a
            # 500 would just silence the error without helping anyone.
            return web.Response(status=200, text="OK (handler error, check logs)")

        return web.Response(status=200, text="OK")

    async def start(self) -> None:
        """Start the aiohttp server. Call once from webhook_cog.py."""
        app = web.Application()
        app.router.add_post("/webhook", self._handle_webhook)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self._port)
        await site.start()
        logger.info("Webhook server listening on port %s", self._port)

    async def stop(self) -> None:
        """Gracefully shut down the aiohttp server."""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
            logger.info("Webhook server stopped")
