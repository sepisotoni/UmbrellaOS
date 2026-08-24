"""
bot/cogs/operational_intelligence_cog.py — Fifth proof of the "thin
caller" pattern: slash commands over umbrella-core's
operational_intelligence.* capabilities (capabilities/operational_intelligence.py:
crash_risk.assess, query, postmortem.draft). No analysis logic lives
here — that's services/operational_intelligence/*.py on the core side.

Unlike investigation_cog.py / moderation_report_cog.py / knowledge_cog.py,
this domain has **no Moo-assistant precedent to port** — the capability
module's own docstring calls these "Phase 5's novel capabilities," i.e.
built fresh for umbrella-core, never part of Moo. So the command shapes
below are new design, not adaptations, and are worth a closer look than
a straight port would need:

- `/crash_risk` and `/postmortem` map 1:1 onto their capabilities
  (server_id in, structured result out) - no design decision needed.
- `/ops_query` is the one real judgment call: operational_intelligence.query
  requires a `window_start`/`window_end` datetime pair, and Discord slash
  commands have no native datetime input type (options are limited to
  string/int/number/bool/user/channel/role/mentionable/attachment - see
  discord.py's app_commands option types). Rather than asking the user to
  type two ISO timestamps by hand, this command takes a `hours_back: int`
  and computes the window as `[now - hours_back, now]` server-side (in the
  cog, not core - core still receives two concrete datetimes, exactly what
  the capability's schema requires). This is a UX decision made on the
  Discord side, not a core capability change, so it doesn't need the same
  bar as touching core - but it IS a real design choice, not a mechanical
  port, so it's called out here rather than presented as equivalent to the
  other two commands in this cog.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.umbrella_core_client import UmbrellaCoreError
from bot.utils.checks import require_owner_role

logger = logging.getLogger(__name__)

_RISK_COLORS = {
    "insufficient_data": discord.Color.light_grey(),
    "none": discord.Color.green(),
    "watch": discord.Color.gold(),
    "critical": discord.Color.red(),
}


class OperationalIntelligenceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="crash_risk", description="Assess a server's predictive crash risk from its recent TPS trend.")
    @require_owner_role()
    @app_commands.describe(server_id="The server's PluginHeartbeat identity")
    async def crash_risk(self, interaction: discord.Interaction, server_id: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            result = await self.bot.core.invoke(
                "operational_intelligence.crash_risk.assess", {"server_id": server_id}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(embed=self._format_crash_risk(result), ephemeral=True)

    @app_commands.command(name="ops_query", description="Ask a natural-language question about server operations.")
    @require_owner_role()
    @app_commands.describe(
        server_id="The server's PluginHeartbeat identity",
        question="e.g. 'Why did the server lag at 3pm?'",
        hours_back="How many hours of history to analyze (default 1)",
    )
    async def ops_query(
        self, interaction: discord.Interaction, server_id: str, question: str, hours_back: app_commands.Range[int, 1, 168] = 1
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(hours=hours_back)

        try:
            result = await self.bot.core.invoke(
                "operational_intelligence.query",
                {
                    "server_id": server_id,
                    "question": question,
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                },
                discord_user_id=str(interaction.user.id),
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(embed=self._format_query_result(question, result), ephemeral=True)

    @app_commands.command(name="postmortem", description="Draft an AI-authored incident postmortem for staff review.")
    @require_owner_role()
    @app_commands.describe(server_id="The server's PluginHeartbeat identity")
    async def postmortem(self, interaction: discord.Interaction, server_id: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            result = await self.bot.core.invoke(
                "operational_intelligence.postmortem.draft", {"server_id": server_id}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(embed=self._format_postmortem(result), ephemeral=True)

    @staticmethod
    def _format_error(exc: UmbrellaCoreError) -> str:
        """Separated from the command bodies so it's testable without a
        live discord.Interaction - see tests/test_operational_intelligence_cog.py."""
        if exc.status_code == 403:
            return "You don't have permission to view operational intelligence."
        return f"Operational intelligence request failed: {exc}"

    @staticmethod
    def _format_crash_risk(result: dict) -> discord.Embed:
        """Pure function, testable without discord.py's interaction/gateway
        machinery - same reasoning as every other _format_* in this project."""
        risk_level = result.get("risk_level", "insufficient_data")
        embed = discord.Embed(
            title=f"Crash risk: {result.get('server_id', '?')}",
            description=result.get("reasoning", ""),
            color=_RISK_COLORS.get(risk_level, discord.Color.light_grey()),
        )
        embed.add_field(name="Risk level", value=risk_level.replace("_", " ").title(), inline=True)
        tps = result.get("current_tps")
        embed.add_field(name="Current TPS", value=f"{tps:.2f}" if tps is not None else "—", inline=True)
        trend = result.get("trend_delta")
        embed.add_field(name="Trend", value=f"{trend:+.2f}" if trend is not None else "—", inline=True)
        embed.set_footer(text=f"{result.get('samples_analyzed', 0)} samples analyzed")
        return embed

    @staticmethod
    def _format_query_result(question: str, result: dict) -> discord.Embed:
        embed = discord.Embed(title="Operational query", description=question, color=discord.Color.blurple())
        embed.add_field(name="Answer", value=result.get("answer", "—"), inline=False)
        if result.get("escalated"):
            embed.add_field(name="⚠️ Status", value="Escalated to staff for review.", inline=False)
        embed.set_footer(text=f"Confidence: {result.get('confidence', 0):.0%}")
        return embed

    @staticmethod
    def _format_postmortem(result: dict) -> discord.Embed:
        draft = result.get("draft", "")
        snippet = draft if len(draft) <= 1000 else draft[:1000] + "…"
        embed = discord.Embed(
            title=f"Postmortem draft: {result.get('server_id', '?')}",
            description=snippet,
            color=discord.Color.orange(),
        )
        embed.add_field(name="Status", value=result.get("status", "—"), inline=True)
        if result.get("escalated"):
            embed.add_field(name="⚠️ Escalated", value="Sent to staff for review.", inline=True)
        embed.set_footer(text=f"Confidence: {result.get('confidence', 0):.0%} — never auto-published")
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OperationalIntelligenceCog(bot))
