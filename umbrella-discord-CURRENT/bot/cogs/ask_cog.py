"""
bot/cogs/ask_cog.py — /ask slash command.

Sends a natural-language question to umbrella-core's AI copilot endpoint
(POST /api/v1/ai/copilot) and returns the answer as an ephemeral embed.
No role restriction — any server member can ask. The copilot runs through
the real AI orchestrator on core (Gemini → OpenRouter failover) so it's
never a client-side simulation.

Context (optional): lets the user give the model extra background, e.g.
"player was banned yesterday" so it can give a more relevant answer. Core
prepends this as "Context: <context>\n\nQuestion: <question>" before
routing to the provider.

This is deliberately the simplest cog in the project — one command, one
core call, one embed. No pagination, no confirmation, no role check.
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.umbrella_core_client import UmbrellaCoreError

logger = logging.getLogger(__name__)


class AskCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ask", description="Ask the UmbrellaOS AI a question about the server or community.")
    @app_commands.describe(
        question="What do you want to know?",
        context="Optional background info to help the AI answer better (e.g. 'player was banned last week')",
    )
    async def ask(
        self,
        interaction: discord.Interaction,
        question: str,
        context: str | None = None,
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            result = await self.bot.core.ask_ai(question, context=context)
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True, wait=True)
            return

        await interaction.followup.send(
            embed=self._format_result(question, result),
            ephemeral=True,
            wait=True,
        )

    @staticmethod
    def _format_error(exc: UmbrellaCoreError) -> str:
        if exc.status_code == 503:
            return "⚠️ The AI copilot is currently unavailable. Try again in a moment."
        if exc.status_code == 403:
            return "You don't have permission to use the AI copilot."
        return f"Ask failed: {exc}"

    @staticmethod
    def _format_result(question: str, result: dict) -> discord.Embed:
        answer = result.get("response", "No response returned.")
        model = result.get("model_used", "unknown")
        latency_ms = result.get("latency_ms", 0)

        # Discord embed description cap is 4096 chars — truncate gracefully.
        if len(answer) > 3900:
            answer = answer[:3900] + "\n\n*(response truncated)*"

        embed = discord.Embed(
            description=answer,
            color=discord.Color.blurple(),
        )
        embed.set_author(name="UmbrellaOS AI", icon_url=None)
        embed.add_field(name="Question", value=question[:1024], inline=False)
        embed.set_footer(text=f"Model: {model} · {latency_ms}ms")
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AskCog(bot))
