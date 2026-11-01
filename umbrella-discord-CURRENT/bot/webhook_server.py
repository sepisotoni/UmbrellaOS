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
import json
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
        self._seen_nonces: dict[str, float] = {}

    def register_handler(self, event: str, handler: EventHandler) -> None:
        """Register a coroutine to be called when *event* arrives.
        The handler receives the payload dict. Overwriting an existing
        handler is allowed (last write wins)."""
        self._handlers[event] = handler

    def _compute_mac(self, ts: int) -> str:
        """Synchronous PBKDF2 derivation — only call via _verify_mac_async.

        Kept as a plain method so asyncio.to_thread can offload the
        ~500ms blocking computation without capturing self in a closure.
        100k iterations stall the event loop long enough to trigger Discord
        gateway heartbeat warnings; same fix applied here as in
        UmbrellaCoreClient._make_auth_headers / _make_auth_headers_async.
        """
        return hashlib.pbkdf2_hmac(
            "sha256",
            self._secret.encode(),
            str(ts).encode(),
            100_000,
            dklen=32,
        ).hex()

    async def _verify_mac_async(self, mac: str | None, timestamp: str | None) -> bool:
        """Async MAC verification — offloads the blocking PBKDF2 to a thread.

        FIX (HIGH): _verify_mac was a synchronous method called directly from
        the async _handle_webhook handler. 100k PBKDF2 iterations (~500ms on
        low-power containers) ran on the event loop, blocking Discord gateway
        heartbeats. Split into _compute_mac (sync, runs in thread) + this async
        wrapper, matching the pattern already used in UmbrellaCoreClient.
        """
        if not mac or not timestamp:
            return False
        try:
            ts = int(timestamp)
        except ValueError:
            return False
        if abs(time.time() - ts) > 30:
            return False
        expected = await asyncio.to_thread(self._compute_mac, ts)
        return hmac.compare_digest(expected, mac)

    def _verify_v2(
        self,
        *,
        method: str,
        target: str,
        body: bytes,
        mac: str | None,
        timestamp: str | None,
        nonce: str | None,
    ) -> bool:
        if not mac or not timestamp or not nonce:
            return False
        try:
            ts = int(timestamp)
        except ValueError:
            return False
        now = time.time()
        if abs(now - ts) > 30:
            return False
        if (
            len(nonce) < 16
            or len(nonce) > 128
            or any(ch not in "0123456789abcdefABCDEF" for ch in nonce)
        ):
            return False

        body_hash = hashlib.sha256(body).hexdigest()
        canonical = (
            f"{method.upper()}\n{target}\n{timestamp}\n{nonce}\n{body_hash}"
        ).encode("utf-8")
        expected = hmac.new(
            self._secret.encode("utf-8"), canonical, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, mac):
            return False

        # Single-process bot server: an in-memory nonce cache is sufficient
        # for its own webhook listener. Purge expired entries opportunistically.
        for seen, expires_at in list(self._seen_nonces.items()):
            if expires_at <= now:
                self._seen_nonces.pop(seen, None)
        if nonce in self._seen_nonces:
            return False
        self._seen_nonces[nonce] = now + 90
        return True

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        mac = request.headers.get("X-Auth-MAC")
        timestamp = request.headers.get("X-Auth-Timestamp")
        version = request.headers.get("X-Auth-Version")
        nonce = request.headers.get("X-Auth-Nonce")
        raw_body = await request.read()

        if version == "2":
            auth_ok = self._verify_v2(
                method=request.method,
                target=request.rel_url.path_qs,
                body=raw_body,
                mac=mac,
                timestamp=timestamp,
                nonce=nonce,
            )
        else:
            auth_ok = await self._verify_mac_async(mac, timestamp)

        if not auth_ok:
            logger.warning("Rejected webhook request — invalid or replayed authentication")
            return web.Response(status=401, text="Unauthorized")

        try:
            body = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return web.Response(status=400, text="Invalid JSON")

        if not isinstance(body, dict):
            return web.Response(status=400, text="Webhook body must be an object")
        event = body.get("event")
        payload = body.get("payload", {})

        if not isinstance(event, str) or not event:
            return web.Response(status=400, text="Invalid 'event' field")
        if not isinstance(payload, dict):
            return web.Response(status=400, text="Webhook payload must be an object")

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
