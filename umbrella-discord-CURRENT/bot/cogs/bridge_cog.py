"""
bot/cogs/bridge_cog.py — Delivers dashboard chat-bridge broadcasts to
Discord. Core persists each broadcast in a short-lived outbox; this cog
returns success only after Discord accepts the message so the webhook can
acknowledge the queued event.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlsplit

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

_SEND_RETRY_DELAYS = (0.25, 0.5)
_DEFAULT_EMBED_TITLE = "📢 Staff Broadcast"
_DEFAULT_EMBED_COLOR = 0x9B59B6


def _is_https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


class BridgeCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def handle_dashboard_message_push(self, payload: dict[str, Any]) -> bool:
        """Called by WebhookCog when core pushes a bridge.dashboard_message
        event. Posts the broadcast to the channel the operator selected."""
        channel_id_raw = payload.get("channel_id")
        if not channel_id_raw:
            logger.warning(
                "Push: dashboard broadcast (message_id=%s) has no channel_id — nothing to post to.",
                payload.get("message_id"),
            )
            return False

        try:
            channel_id = int(channel_id_raw)
        except (TypeError, ValueError):
            logger.warning(
                "Push: dashboard broadcast (message_id=%s) has a non-numeric channel_id=%r.",
                payload.get("message_id"),
                channel_id_raw,
            )
            return False

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            logger.warning(
                "Push: dashboard broadcast channel_id=%s isn't a channel this bot can see.",
                channel_id,
            )
            return False

        for attempt in range(len(_SEND_RETRY_DELAYS) + 1):
            try:
                await channel.send(embed=self._format_broadcast(payload))
                return True
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
        return False

    @staticmethod
    def _format_broadcast(payload: dict[str, Any]) -> discord.Embed:
        title = payload.get("embed_title")
        if not isinstance(title, str) or not title.strip():
            title = _DEFAULT_EMBED_TITLE
        try:
            color_value = int(payload.get("embed_color", _DEFAULT_EMBED_COLOR))
        except (TypeError, ValueError):
            color_value = _DEFAULT_EMBED_COLOR
        if not 0 <= color_value <= 0xFFFFFF:
            color_value = _DEFAULT_EMBED_COLOR

        embed = discord.Embed(
            title=title[:256],
            description=payload.get("message", ""),
            color=discord.Color(color_value),
        )
        icon_url = payload.get("icon_url")
        if _is_https_url(icon_url):
            embed.set_thumbnail(url=icon_url)
        image_url = payload.get("image_url")
        if _is_https_url(image_url):
            embed.set_image(url=image_url)
        sender = payload.get("player_name") or "Staff"
        embed.set_footer(text=f"Sent by {sender} via UmbrellaOS Dashboard")
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BridgeCog(bot))
