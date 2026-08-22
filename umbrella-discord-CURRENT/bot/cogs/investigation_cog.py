"""
bot/cogs/investigation_cog.py — The first proof of the "thin caller"
pattern the Phase 6 roadmap requires: this cog does not implement any
investigation logic itself. It formats a Discord interaction into a
capability call and formats the result back into a Discord response.
All the actual logic lives in umbrella-core's investigation.run
capability (services/investigation/service.py on that side).
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.umbrella_core_client import UmbrellaCoreError

logger = logging.getLogger(__name__)


class InvestigationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="investigate", description="Run every investigation tool against a question and optional user.")
    @app_commands.describe(question="What you want to investigate", user="The user this concerns, if any")
    async def investigate(
        self, interaction: discord.Interaction, question: str, user: discord.Member | None = None
    ) -> None:
        await interaction.response.defer(thinking=True)

        try:
            result = await self.bot.core.invoke(
                "investigation.run",
                {
                    "question": question,
                    "target_user_id": str(user.id) if user is not None else None,
                },
                discord_user_id=str(interaction.user.id),
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc))
            return

        await interaction.followup.send(embed=self._format_result(question, result))

    @staticmethod
    def _format_error(exc: UmbrellaCoreError) -> str:
        """Separated from the command body so it's testable without a
        live discord.Interaction - see tests/test_investigation_cog.py."""
        if exc.status_code == 403:
            return "You don't have permission to run investigations."
        return f"Investigation failed: {exc}"

    @staticmethod
    def _format_result(question: str, result: dict) -> discord.Embed:
        """Separated from the command body for the same reason as
        _format_error - pure function, testable without discord.py's
        interaction/gateway machinery."""
        embed = discord.Embed(title="Investigation", description=question, color=discord.Color.blurple())
        for finding in result.get("findings", []):
            embed.add_field(name=finding["tool_key"], value=finding["finding_text"], inline=False)
        embed.set_footer(text=f"Confidence: {result.get('confidence', 0):.0%}")
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(InvestigationCog(bot))
