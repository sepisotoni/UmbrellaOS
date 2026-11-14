"""
bot/cogs/bridge_cog.py — Delivers dashboard chat-bridge broadcasts to
Discord.

AUDIT-2026-08-30: staff clicking "Dispatch Embed to Discord" on the
dashboard's Discord Hub confirmed broken in live testing — the request
reached core (api/routers/bridge.py::receive_bridge_message), which
correctly persisted a ChatMessage row and computed forwarded=True,
targets=["minecraft","discord"], but nothing ever actually delivered
anything to Discord. Traced the whole pipeline: umbrella-core already
has a real, working push mechanism (services/bot_push_service.py +
bot/webhook_server.py, Phase 16B Task B) — it's just never used for
this message type. staff.escalation.new (see notifications_cog.py) is
the only event with a registered handler before this cog.

Unlike escalations, the dashboard operator picks the target channel
per-message (BridgeMessageRequest.channel_id) rather than posting to one
fixed configured channel, so there's no fallback default here — if
channel_id is missing or not a channel this bot can see, log and drop
(same "can't do anything useful" guard as notifications_cog.py's
channel-missing case).

Delivery is a bounded best effort: Discord sends are retried three times,
then the failure is logged and this handler returns. WebhookServer therefore
responds 2xx, and umbrella-core's fire-and-forget push does not retry; a
broadcast can be lost after all three send attempts fail. There is no durable
bridge queue or polling fallback today.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

_SEND_RETRY_DELAYS = (0.25, 0.5)


class BridgeCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def handle_dashboard_message_push(self, payload: dict[str, Any]) -> None:
        """Called by WebhookCog when core pushes a bridge.dashboard_message
        event. Posts the broadcast to the channel the operator selected."""
        channel_id_raw = payload.get("channel_id")
        if not channel_id_raw:
            logger.warning(
                "Push: dashboard broadcast (message_id=%s) has no channel_id — nothing to post to.",
                payload.get("message_id"),
            )
            return

        try:
            channel_id = int(channel_id_raw)
        except (TypeError, ValueError):
            logger.warning(
                "Push: dashboard broadcast (message_id=%s) has a non-numeric channel_id=%r.",
                payload.get("message_id"),
                channel_id_raw,
            )
            return

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            logger.warning(
                "Push: dashboard broadcast channel_id=%s isn't a channel this bot can see.",
                channel_id,
            )
            return

        for attempt in range(len(_SEND_RETRY_DELAYS) + 1):
            try:
                await channel.send(embed=self._format_broadcast(payload))
                return
            except discord.HTTPException:
                if attempt < len(_SEND_RETRY_DELAYS):
                    delay = _SEND_RETRY_DELAYS[attempt]
                    logger.exception(
                        "Dashboard broadcast (message_id=%s) send to channel %s failed "
                        "(attempt %d/3); retrying in %.2fs.",
                        payload.get("message_id"),
                        channel_id,
                        attempt + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.exception(
                        "Dashboard broadcast (message_id=%s) send to channel %s failed "
                        "after 3 attempts.",
                        payload.get("message_id"),
                        channel_id,
                    )

    @staticmethod
    def _format_broadcast(payload: dict[str, Any]) -> discord.Embed:
        embed = discord.Embed(
            title="📢 Staff Broadcast",
            description=payload.get("message", ""),
            color=discord.Color.purple(),
        )
        sender = payload.get("player_name") or "Staff"
        embed.set_footer(text=f"Sent by {sender} via UmbrellaOS Dashboard")
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BridgeCog(bot))
