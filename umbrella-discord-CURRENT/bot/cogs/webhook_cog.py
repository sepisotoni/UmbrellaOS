"""
bot/cogs/webhook_cog.py — Integrates WebhookServer with the bot lifecycle
and routes push events from umbrella-core to the appropriate cog handlers.

Lifecycle:
1. cog_load() — starts the aiohttp webhook server on BOT_CALLBACK_PORT,
   registers event handlers, then (if BOT_CALLBACK_URL is set) calls
   core to register this bot's public webhook address.
2. cog_unload() — stops the aiohttp server cleanly.

Event routing:
  staff.escalation.new       → NotificationsCog.handle_escalation_push()
  bridge.dashboard_message   → BridgeCog.handle_dashboard_message_push()
  (others can be added here without touching WebhookServer or bot.py)

The cog does NOT crash the bot if the server fails to start or if
registration with core fails — it logs and continues. Registration retries
with bounded backoff and repeats every five minutes after exhaustion. The
fallback poll loop in NotificationsCog ensures escalations eventually surface.
Bridge delivery has no such fallback: after its bounded send retries fail,
BridgeCog logs and returns, so this endpoint replies 2xx and core's
fire-and-forget sender does not retry. See BridgeCog's module docstring for
that bounded-loss limitation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from discord.ext import commands

from bot.services.umbrella_core_client import UmbrellaCoreError
from bot.webhook_server import WebhookServer

logger = logging.getLogger(__name__)

_REGISTRATION_RETRY_DELAYS = (1, 2, 4)
_REGISTRATION_RETRY_INTERVAL = 300


class WebhookCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._server: WebhookServer | None = None
        self._registration_task: asyncio.Task[None] | None = None

    async def cog_load(self) -> None:
        port = self.bot.remote.callback_port
        secret = self.bot.settings.umbrella_core_api_key

        self._server = WebhookServer(shared_secret=secret, port=port)

        # Register handlers before starting so no event races during startup.
        self._server.register_handler("staff.escalation.new", self._on_escalation)
        self._server.register_handler(
            "bridge.dashboard_message", self._on_bridge_message
        )

        try:
            await self._server.start()
        except Exception:
            logger.exception(
                "Webhook server failed to start on port %s — push events will not be received. "
                "Bot continues; poll fallback remains active.",
                port,
            )
            return

        # Register this bot's public URL with umbrella-core.
        callback_url = self.bot.remote.callback_url
        if not callback_url:
            logger.warning(
                "BOT_CALLBACK_URL is not set — skipping registration with core. "
                "Push events will not be delivered until the URL is configured."
            )
            return

        self._registration_task = asyncio.create_task(
            self._registration_worker(f"{callback_url.rstrip('/')}/webhook")
        )

    async def cog_unload(self) -> None:
        if self._registration_task:
            self._registration_task.cancel()
            try:
                await self._registration_task
            except asyncio.CancelledError:
                pass
        if self._server:
            await self._server.stop()

    async def _register_with_backoff(self, callback_url: str) -> bool:
        """Attempt webhook registration with bounded exponential backoff."""
        for attempt in range(len(_REGISTRATION_RETRY_DELAYS) + 1):
            try:
                await self.bot.core.register_bot(callback_url)
                logger.info("Registered bot webhook with umbrella-core.")
                return True
            except UmbrellaCoreError:
                if attempt < len(_REGISTRATION_RETRY_DELAYS):
                    delay = _REGISTRATION_RETRY_DELAYS[attempt]
                    logger.exception(
                        "Webhook registration failed (attempt %d/4); retrying in %ds.",
                        attempt + 1,
                        delay,
                    )
                else:
                    logger.exception(
                        "Webhook registration failed after 4 attempts; will retry in %ds.",
                        _REGISTRATION_RETRY_INTERVAL,
                    )
                if attempt < len(_REGISTRATION_RETRY_DELAYS):
                    await asyncio.sleep(_REGISTRATION_RETRY_DELAYS[attempt])
        return False

    async def _registration_worker(self, callback_url: str) -> None:
        while True:
            if await self._register_with_backoff(callback_url):
                return
            await asyncio.sleep(_REGISTRATION_RETRY_INTERVAL)

    async def _on_escalation(self, payload: dict[str, Any]) -> None:
        """Handle a staff.escalation.new push event from core.

        Forwards directly to NotificationsCog if it's loaded, otherwise
        logs and drops (the poll will pick it up within 5 minutes).
        """
        notifications_cog = self.bot.cogs.get("NotificationsCog")
        if notifications_cog is None:
            logger.warning(
                "Received staff.escalation.new push but NotificationsCog is not loaded — "
                "escalation %s will surface on next poll.",
                payload.get("id"),
            )
            return

        try:
            await notifications_cog.handle_escalation_push(payload)
        except Exception:
            logger.exception(
                "NotificationsCog.handle_escalation_push raised for escalation %s",
                payload.get("id"),
            )

    async def _on_bridge_message(self, payload: dict[str, Any]) -> None:
        """Handle a bridge.dashboard_message push event from core — a
        dashboard "Dispatch Embed to Discord" broadcast. Forwards to
        BridgeCog if it's loaded; unlike escalations there's no poll
        fallback for this event type (dashboard broadcasts are one-shot,
        not a queryable list), so if BridgeCog isn't loaded the message
        is simply dropped rather than delayed."""
        bridge_cog = self.bot.cogs.get("BridgeCog")
        if bridge_cog is None:
            logger.warning(
                "Received bridge.dashboard_message push but BridgeCog is not loaded — "
                "message %s will not be delivered.",
                payload.get("message_id"),
            )
            return

        try:
            await bridge_cog.handle_dashboard_message_push(payload)
        except Exception:
            logger.exception(
                "BridgeCog.handle_dashboard_message_push raised for message %s",
                payload.get("message_id"),
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WebhookCog(bot))
