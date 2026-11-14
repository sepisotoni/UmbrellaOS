"""
bot/cogs/notifications_cog.py — Closes the last item on Phase 6's original
"not started" list: staff escalations existed and were listable
(moderation_intelligence.escalation.list) since early in this project, but
nothing ever surfaced them anywhere - staff had to remember to go check.

Escalations use core's webhook push for near-real-time delivery, with a
5-minute poll as the fallback. Successful push delivery is acknowledged via
the same durable ``StaffEscalation.notified_at`` marker used by polling; the
ack is delayed/retried because core emits the event before its transaction
commits.

**Durability**: delivery acknowledgement is tracked in umbrella-core's DB
(StaffEscalation.notified_at, see models/moderation_intelligence.py and
moderation_intelligence.escalation.mark_notified), not locally in this
stateless service. A successful push writes this marker before the next poll,
while a channel-send failure deliberately skips it so polling retries rather
than silently losing the escalation.

**Known gap, not fixed here**: operational_intelligence's query/postmortem
"escalated" flag (see operational_intelligence_cog.py) is a one-off signal
returned to whoever made that specific call - services/operational_intelligence/
nl_query.py and postmortem.py never write to StaffEscalation, only
moderation_intelligence's own report/investigation flows do (confirmed by
grepping for StaffEscalation writers - only
services/moderation_intelligence/*.py touch that table). So this poller
can only ever surface moderation/investigation escalations, not
operational-intelligence ones. Wiring operational_intelligence into the
same shared queue is a reasonable follow-up, not attempted here - it's a
different domain's capability module, out of scope for "build the
poller that reads what already exists."

Checked against real discord.py 2.7.1 rather than assumed:
discord.ext.tasks.loop()'s decorator signature, Loop.before_loop() for
deferring until the gateway is ready, and Loop.cancel() as the
cog_unload() cleanup hook (discord/ext/tasks/__init__.py).
"""

from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands, tasks

from bot.services.umbrella_core_client import UmbrellaCoreError

logger = logging.getLogger(__name__)

_SOURCE_LABELS = {
    "moderation": "Moderation report",
    "investigation": "Investigation",
    "support": "Support",
}


class NotificationsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._ack_tasks: set[asyncio.Task[None]] = set()
        self.poll_escalations.start()

    async def cog_unload(self) -> None:
        self.poll_escalations.cancel()
        ack_tasks = list(self._ack_tasks)
        for task in ack_tasks:
            task.cancel()
        if ack_tasks:
            await asyncio.gather(*ack_tasks, return_exceptions=True)

    @tasks.loop(
        minutes=5
    )  # Phase 16B: push handles real-time; poll is fallback for missed events
    async def poll_escalations(self) -> None:
        # No discord_user_id here, deliberately, unlike every other cog's
        # invoke() calls (Phase 6's slash-command -> REST-permission
        # mapping - see UmbrellaCoreClient.invoke()'s docstring): this is
        # a background poll with no invoking user at all. It correctly
        # runs as the bot's own identity, using its own API key's blanket
        # scope, same as before that mapping existed.
        try:
            result = await self.bot.core.invoke(
                "moderation_intelligence.escalation.list", {"limit": 20}
            )
        except UmbrellaCoreError:
            logger.exception("Failed to poll staff escalations.")
            return

        unnotified = [
            e for e in result.get("escalations", []) if not e.get("notified_at")
        ]
        if not unnotified:
            return

        channels = self._staff_alert_channels()
        if not channels:
            logger.warning(
                "%d new staff escalation(s) found but no guild has a staff alert channel configured.",
                len(unnotified),
            )
            return

        for escalation in unnotified:
            delivered = 0
            delivery_failed = False
            for guild_id, channel in channels:
                if channel is None:
                    delivery_failed = True
                    continue
                try:
                    await channel.send(embed=self._format_escalation(escalation))
                    delivered += 1
                except discord.HTTPException:
                    delivery_failed = True
                    logger.exception(
                        "Failed to post escalation %s to guild %s.",
                        escalation.get("id"),
                        guild_id,
                    )

            if delivery_failed or not delivered:
                logger.warning(
                    "Escalation %s was not delivered to every configured guild; will retry next poll.",
                    escalation.get("id"),
                )
                continue

            try:
                await self.bot.core.invoke(
                    "moderation_intelligence.escalation.mark_notified",
                    {"escalation_id": escalation["id"]},
                )
            except UmbrellaCoreError:
                logger.exception(
                    "Posted escalation %s but failed to mark it notified — may repost next cycle.",
                    escalation.get("id"),
                )

    @poll_escalations.before_loop
    async def before_poll_escalations(self) -> None:
        await self.bot.wait_until_ready()

    async def handle_escalation_push(self, payload: dict) -> None:
        """Called by WebhookCog when core pushes a staff.escalation.new event.
        Posts the escalation embed immediately without waiting for the poll cycle.
        Acknowledges successful delivery through the existing durable
        notified_at capability after a short delay, allowing core's transaction
        that emitted this push to commit first. The poll loop then sees the
        durable acknowledgement and skips this escalation.
        Posts to each guild with a configured staff alert channel."""
        channels = self._staff_alert_channels()
        if not channels:
            logger.warning(
                "Push: escalation %s received but no guild has a staff alert channel configured.",
                payload.get("id"),
            )
            return

        delivered = 0
        delivery_failed = False
        for guild_id, channel in channels:
            if channel is None:
                delivery_failed = True
                continue
            try:
                await channel.send(embed=self._format_escalation(payload))
                delivered += 1
            except discord.HTTPException:
                delivery_failed = True
                logger.exception(
                    "Push: failed to post escalation %s to guild %s.",
                    payload.get("id"),
                    guild_id,
                )

        if delivery_failed or not delivered:
            logger.warning(
                "Push: escalation %s was not delivered to every configured guild; poll will retry.",
                payload.get("id"),
            )
            return

        escalation_id = payload.get("id")
        if not escalation_id:
            logger.warning(
                "Push: delivered escalation without an id; cannot persist its acknowledgement."
            )
            return

        task = asyncio.create_task(self._acknowledge_push(str(escalation_id)))
        self._ack_tasks.add(task)
        task.add_done_callback(self._ack_tasks.discard)

    def _staff_alert_channels(
        self,
    ) -> list[tuple[int, discord.abc.Messageable | None]]:
        channels = []
        for guild_id, config in self.bot.guild_configs.items():
            channel_id = config.staff_alert_channel_id
            if not channel_id:
                continue
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                logger.warning(
                    "Staff alert channel %s is unavailable in guild %s.",
                    channel_id,
                    guild_id,
                )
            channels.append((guild_id, channel))
        return channels

    async def _acknowledge_push(self, escalation_id: str) -> None:
        """Persist push delivery using core's existing durable marker.

        Core emits the push before its transaction commits, so acknowledgement
        is deferred and retried. No in-memory state is used to suppress polls.
        """
        await asyncio.sleep(1)
        for attempt in range(3):
            try:
                await self.bot.core.invoke(
                    "moderation_intelligence.escalation.mark_notified",
                    {"escalation_id": escalation_id},
                )
                logger.info(
                    "Persisted push acknowledgement for escalation %s.",
                    escalation_id,
                )
                return
            except UmbrellaCoreError:
                logger.exception(
                    "Failed to acknowledge pushed escalation %s (attempt %d/3).",
                    escalation_id,
                    attempt + 1,
                )
                if attempt < 2:
                    await asyncio.sleep(2**attempt)

    @staticmethod
    def _format_escalation(escalation: dict) -> discord.Embed:
        """Separated from the loop body so it's testable without a live
        discord.TextChannel - see tests/test_notifications_cog.py."""
        source = escalation.get("source", "?")
        embed = discord.Embed(
            title=f"⚠️ Staff escalation — {_SOURCE_LABELS.get(source, source)}",
            description=escalation.get("summary", ""),
            color=discord.Color.orange(),
        )
        confidence = escalation.get("confidence")
        if confidence is not None:
            embed.add_field(
                name="AI confidence", value=f"{confidence:.0%}", inline=True
            )
        if escalation.get("related_report_id"):
            embed.add_field(
                name="Related report",
                value=escalation["related_report_id"],
                inline=True,
            )
        embed.set_footer(text=f"Escalation ID: {escalation.get('id', '?')}")
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NotificationsCog(bot))
