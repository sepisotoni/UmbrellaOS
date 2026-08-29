"""
bot/cogs/knowledge_cog.py — Third proof of the "thin caller" pattern: a
slash command over umbrella-core's knowledge.entry.search capability
(capabilities/knowledge.py). No search/ranking logic lives here — that's
services/knowledge/service.py on the core side.

Worth flagging rather than silently assuming: Moo-assistant has no
existing "search the knowledge base" slash command to port. Its knowledge
base (bot/knowledge/retriever.py) is only ever read internally, by the
SupportEngine building an AI answer (bot/cogs/ai_cog.py) — a user never
queries it directly. Moo's actual user-facing /search command
(bot/cogs/search_cog.py) searches archived *messages*
(bot/services/search_service.py), a different capability entirely
(archive_search.*, not knowledge.*) that isn't part of this pair.

Given umbrella-core already exposes knowledge.entry.search as its own
capability with its own permission (knowledge.entry.search, distinct from
knowledge.entry.manage), exposing it directly as a user-facing command is
a reasonable, low-risk default — same shape as every other capability
this service wraps — rather than something that needs a bigger design
conversation. Flagging the "no Moo precedent" fact here instead of
silently presenting this as a straight port, per this project's working
conventions.

Correction review (knowledge.correction.propose/list_pending/approve/
reject) is deliberately NOT built here — that's staff-only moderation
tooling with a different shape (Moo's !ai-knowledge in
founder_admin_cog.py), not a "search" command, and is its own cog-sized
piece of work.
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.umbrella_core_client import UmbrellaCoreError

logger = logging.getLogger(__name__)


class KnowledgeCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="knowledge_search", description="Search the knowledge base for an answer.")
    @app_commands.describe(query="What you're looking for")
    async def knowledge_search(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            result = await self.bot.core.search_knowledge(query, limit=5)
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(embed=self._format_result(query, result), ephemeral=True)

    @staticmethod
    def _format_error(exc: UmbrellaCoreError) -> str:
        """Separated from the command body so it's testable without a
        live discord.Interaction - see tests/test_knowledge_cog.py."""
        if exc.status_code == 503:
            return "⚠️ The AI knowledge service is currently unavailable. Try again in a moment."
        if exc.status_code == 403:
            return "You don't have permission to search the knowledge base."
        return f"Knowledge search failed: {exc}"

    @staticmethod
    def _format_result(query: str, result: dict) -> discord.Embed:
        """Separated from the command body for the same reason as
        _format_error - pure function, testable without discord.py's
        interaction/gateway machinery."""
        embed = discord.Embed(title="Knowledge search", description=f'Results for "{query}"', color=discord.Color.blurple())
        entries = result.get("entries", [])
        if not entries:
            embed.add_field(name="No results", value="Nothing matched that query.", inline=False)
            return embed

        for entry in entries:
            content = entry["content"]
            snippet = content if len(content) <= 500 else content[:500] + "…"
            embed.add_field(name=f"#{entry['channel_name']}", value=snippet, inline=False)
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(KnowledgeCog(bot))
