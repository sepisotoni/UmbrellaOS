"""
bot/cogs/webhook_cog.py — Integrates WebhookServer with the bot lifecycle
and routes push events from umbrella-core to the appropriate cog handlers.

Lifecycle:
1. cog_load() — starts the aiohttp webhook server on BOT_CALLBACK_PORT,
   registers event handlers, then (if BOT_CALLBACK_URL is set) calls
   core to register this bot's public webhook address.
2. cog_unload() — stops the aiohttp server cleanly.

Event routing:
  staff.escalation.new   → NotificationsCog.handle_escalation_push()
  (others can be added here without touching WebhookServer or bot.py)

The cog does NOT crash the bot if the server fails to start or if
registration with core fails — it logs and continues. The fallback poll
loop in NotificationsCog ensures escalations eventually surface.
"""
from __future__ import annotations

import logging
from typing import Any

from discord.ext import commands

from bot.services.umbrella_core_client import UmbrellaCoreError
from bot.webhook_server import WebhookServer

logger = logging.getLogger(__name__)


class WebhookCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._server: WebhookServer | None = None

    async def cog_load(self) -> None:
        port = self.bot.remote.callback_port
        secret = self.bot.settings.umbrella_core_api_key

        self._server = WebhookServer(shared_secret=secret, port=port)

        # Register handlers before starting so no event races during startup.
        self._server.register_handler("staff.escalation.new", self._on_escalation)

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

        try:
            await self.bot.core.register_bot(f"{callback_url.rstrip('/')}/webhook")
            logger.info("Registered bot webhook with umbrella-core at %s", callback_url)
        except UmbrellaCoreError:
            logger.exception(
                "Failed to register bot webhook with umbrella-core — push events "
                "will not be received until next restart. Poll fallback remains active."
            )

    async def cog_unload(self) -> None:
        if self._server:
            await self._server.stop()

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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WebhookCog(bot))
