"""
bot/cogs/player_risk_cog.py — Sixth proof of the "thin caller" pattern: a
slash command over umbrella-core's player_risk.score capability
(capabilities/player_risk.py). No scoring logic lives here - that's
services/player_risk/risk_score.py on the core side.

Like operational_intelligence, this has no Moo-assistant precedent - it's
one of Phase 5's "novel capabilities," never part of Moo. One real
identity gap, since closed: player_risk.score takes a Minecraft
`player_uuid` directly, not a Discord user - the Minecraft-side and
Discord-side signals it combines are keyed differently (see
services/player_risk/risk_score.py's module docstring). The only prior
path from a Discord user to a player_uuid was investigation's
LinkedAccountTool, which returns a human-readable sentence, not a
structured value safe to chain into player_risk.score. Now fixed:
capabilities/verification.py exposes verification.link.by_discord for
exactly this. /player_risk_by_discord below chains it into player_risk.score
- two capability calls in sequence, same "thin caller calling two existing
operations" shape moderation_report_cog.py's /report uses (create then
analyze) - still no judgment logic of its own, just plumbing.

No explicit risk-level buckets or color thresholds are used in
_format_risk_score, deliberately: capabilities/player_risk.py's
RiskScoreResultModel has no risk_level field the way CrashRiskResult does
(no "low/medium/high" classification exists on the core side) - inventing
a color-coded severity scale here would be presenting a judgment core
never made. Raw numbers only, exactly what the capability actually returns.
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.umbrella_core_client import UmbrellaCoreError
from bot.utils.checks import require_owner_role

logger = logging.getLogger(__name__)


class PlayerRiskCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="player_risk", description="Compute a unified risk score for a player (anticheat, alts, moderation, investigations).")
    @require_owner_role()
    @app_commands.describe(player_uuid="The Minecraft player's UUID")
    async def player_risk(self, interaction: discord.Interaction, player_uuid: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            result = await self.bot.core.invoke(
                "player_risk.score", {"player_uuid": player_uuid}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(embed=self._format_risk_score(result), ephemeral=True)

    @app_commands.command(name="player_risk_by_discord", description="Compute a unified risk score for a linked Discord member.")
    @require_owner_role()
    @app_commands.describe(member="The Discord member to look up")
    async def player_risk_by_discord(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            link = await self.bot.core.invoke(
                "verification.link.by_discord", {"discord_id": str(member.id)}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        if not link["linked"]:
            await interaction.followup.send(f"{member.mention} isn't linked to a Minecraft account.", ephemeral=True)
            return

        try:
            result = await self.bot.core.invoke(
                "player_risk.score", {"player_uuid": link["player_uuid"]}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(embed=self._format_risk_score(result), ephemeral=True)

    @staticmethod
    def _format_error(exc: UmbrellaCoreError) -> str:
        """Separated from the command body so it's testable without a
        live discord.Interaction - see tests/test_player_risk_cog.py."""
        if exc.status_code == 403:
            return "You don't have permission to view player risk scores."
        if exc.status_code == 404:
            return "No player found with that UUID."
        return f"Player risk lookup failed: {exc}"

    @staticmethod
    def _format_risk_score(result: dict) -> discord.Embed:
        """Pure function, testable without discord.py's interaction/gateway
        machinery - same reasoning as every other _format_* in this project."""
        embed = discord.Embed(
            title=f"Risk score: {result.get('total_score', 0)}",
            description=result.get("reasoning", ""),
            color=discord.Color.blurple(),
        )
        discord_id = result.get("discord_id")
        embed.add_field(name="Player UUID", value=result.get("player_uuid", "?"), inline=False)
        embed.add_field(name="Linked Discord account", value=f"<@{discord_id}>" if discord_id else "Not linked", inline=False)

        breakdown = result.get("breakdown", {})
        lines = [
            f"Anticheat: {breakdown.get('anticheat_component', 0)} (raw: {breakdown.get('anticheat_points', 0)})",
            f"Confirmed alt group: {'+' + str(breakdown.get('alt_component', 0)) if breakdown.get('confirmed_alt_group') else '0'}",
            f"Moderation actions: {breakdown.get('moderation_component', 0)} ({breakdown.get('moderation_action_count', 0)} actions)",
            f"Investigations: {breakdown.get('investigation_component', 0)} ({breakdown.get('investigation_count', 0)} investigations)",
        ]
        embed.add_field(name="Breakdown", value="\n".join(lines), inline=False)
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PlayerRiskCog(bot))
