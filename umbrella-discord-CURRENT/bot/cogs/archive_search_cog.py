"""
bot/cogs/archive_search_cog.py — Eighth proof of the "thin caller"
pattern, over umbrella-core's archive.search capability
(capabilities/archive_search.py). No search logic lives here — that's
services/archive_search/service.py on the core side.

**Real behavior change from Moo, not a straight port — get this right,
not just familiar-looking.** Moo's bot/cogs/search_cog.py is genuinely
per-member permission-aware: it computes, live against the Discord
gateway, which channels the *requesting member* can currently see, and
restricts results to those. services/archive_search/service.py's own
module docstring is explicit that this was a deliberate scope reduction,
not an oversight: that per-member computation needs a live
guild/channel-permission mirror umbrella-core doesn't have, so rather
than fake it (a stubbed "always visible" check would be a false sense of
security), umbrella-core's archive.search is **staff-only**
("archive.search", granted moderator+, not the lower-trust tier
investigation/knowledge search use) and returns **unfiltered content
across every channel** to whoever is allowed to call it at all - per-
channel filtering is deferred, real future work, not present today.

Porting Moo's actual UI copy ("Search archived messages (only in channels
you can see)") onto this would misrepresent what the command does - a
real information-disclosure risk, not just a cosmetic inaccuracy. This
cog's copy says "staff" and doesn't claim any channel-visibility
filtering that doesn't exist.

Second reason for extra caution here, worth being explicit about: the
slash-command -> REST-permission mapping is still an open question for
this whole project (see the handoff doc's "not started" list) - today
every cog shares one bot-wide API key via self.bot.core. Until that
mapping exists, ANY Discord member who can invoke bot commands gets
whatever that one key is scoped to. Rather than waiting on that larger
design question to land before this command can exist at all, this cog
adds a Discord-side stopgap - @app_commands.default_permissions(manage_messages=True)
restricts who can even see/use the command in a properly configured
server by default (guild admins can override this in Discord's own
integration settings, which is expected and fine - it's a floor, not a
substitute for the real fix). This is not a replacement for real
permission mapping, just a narrower blast radius until that work happens.
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.umbrella_core_client import UmbrellaCoreError

logger = logging.getLogger(__name__)


class ArchiveSearchCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="archive_search", description="[Staff] Search archived chat history (Minecraft and Discord, unfiltered).")
    @app_commands.describe(query="Text to search for", source="Restrict to 'minecraft' or 'discord' (optional)")
    @app_commands.default_permissions(manage_messages=True)
    async def archive_search(
        self, interaction: discord.Interaction, query: str, source: str | None = None
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            result = await self.bot.core.invoke(
                "archive.search", {"query": query, "source": source}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(embed=self._format_result(query, result), ephemeral=True)

    @staticmethod
    def _format_error(exc: UmbrellaCoreError) -> str:
        """Separated from the command body so it's testable without a
        live discord.Interaction - see tests/test_archive_search_cog.py."""
        if exc.status_code == 403:
            return "You don't have permission to search the chat archive."
        return f"Archive search failed: {exc}"

    @staticmethod
    def _format_result(query: str, result: dict) -> discord.Embed:
        """Pure function, testable without discord.py's interaction/gateway
        machinery - same reasoning as every other _format_* in this project."""
        embed = discord.Embed(title="Archive search", description=f'Results for "{query}"', color=discord.Color.blurple())
        messages = result.get("messages", [])
        if not messages:
            embed.add_field(name="No results", value="Nothing matched that query.", inline=False)
            return embed

        for msg in messages[:10]:
            content = msg["content"]
            snippet = content if len(content) <= 300 else content[:300] + "…"
            author = msg.get("author_name") or "unknown"
            embed.add_field(name=f"[{msg['source']}] {author}", value=snippet, inline=False)
        if len(messages) > 10:
            embed.set_footer(text=f"Showing 10 of {len(messages)} results")
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ArchiveSearchCog(bot))
