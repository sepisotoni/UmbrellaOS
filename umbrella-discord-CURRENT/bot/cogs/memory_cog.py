"""
bot/cogs/memory_cog.py — Fourth proof of the "thin caller" pattern: slash
commands over umbrella-core's memory.server_fact.* and memory.recurring.*
capabilities (capabilities/memory.py). No memory logic lives here — that's
services/memory/service.py on the core side.

Ported from Moo-assistant's founder_admin_cog.py's `!ai-memory` command
(list / set / purge), adapted to two slash commands rather than one
prefix command with a sub-action string — matching the shape every other
Phase 6 cog uses (app_commands, not commands.Context sub-dispatch).

Real gap found while porting, since closed rather than worked around: Moo's
`!ai-memory purge` action calls MemoryService.purge_expired() directly (a
monolith reaching its own service method). umbrella-core's
capabilities/memory.py originally had no memory.*.purge capability -
MemoryService.purge_expired() existed on the core service layer but was
never wrapped. Since fixed (capabilities/memory.py now has
memory.maintenance.purge_expired) - /memory_purge below calls it the same
way every other command here calls its capability.

/memory_get (a single-fact lookup) is still not built: Moo's !ai-memory has
no such action either - facts are only surfaced via `list`, or read
internally by the AI itself, never queried one-by-one by a human. Not
inventing a command Moo never had.
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.umbrella_core_client import UmbrellaCoreError

logger = logging.getLogger(__name__)


class MemoryCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="memory_set", description="Set a durable server fact (server IP, store URL, etc).")
    @app_commands.describe(fact_key="The fact's key, e.g. 'server_ip'", value="The fact's value")
    async def memory_set(self, interaction: discord.Interaction, fact_key: str, value: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            entry = await self.bot.core.invoke(
                "memory.server_fact.set",
                {"fact_key": fact_key, "value": value},
                discord_user_id=str(interaction.user.id),
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(self._format_set_result(entry), ephemeral=True)

    @app_commands.command(name="memory_list", description="List durable server facts and top recurring topics.")
    async def memory_list(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            facts = await self.bot.core.invoke("memory.server_fact.list", {}, discord_user_id=str(interaction.user.id))
            recurring = await self.bot.core.invoke(
                "memory.recurring.top", {"limit": 5}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(embed=self._format_list_result(facts, recurring), ephemeral=True)

    @app_commands.command(name="memory_purge", description="[Staff] Remove expired short-term memory entries (never touches server facts or recurring topics).")
    @app_commands.default_permissions(manage_guild=True)
    async def memory_purge(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            result = await self.bot.core.invoke(
                "memory.maintenance.purge_expired", {}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(f"🧹 Purged {result['purged_count']} expired entries.", ephemeral=True)

    @staticmethod
    def _format_error(exc: UmbrellaCoreError) -> str:
        """Separated from the command bodies so it's testable without a
        live discord.Interaction - see tests/test_memory_cog.py."""
        if exc.status_code == 403:
            return "You don't have permission to manage server memory."
        return f"Memory operation failed: {exc}"

    @staticmethod
    def _format_set_result(entry: dict) -> str:
        return f"✅ Set server fact `{entry['key']}`."

    @staticmethod
    def _format_list_result(facts: dict, recurring: dict) -> discord.Embed:
        """Separated from the command body for the same reason as
        _format_error - pure function, testable without discord.py's
        interaction/gateway machinery. Takes both already-invoked results
        rather than fetching them itself, mirroring Moo's combined
        facts+recurring listing in a single response."""
        embed = discord.Embed(title="Server memory", color=discord.Color.blurple())

        fact_entries = facts.get("facts", [])
        fact_lines = [f"`{f['key']}`: {f['value'][:80]}" for f in fact_entries] or ["(none)"]
        embed.add_field(name="Server facts", value="\n".join(fact_lines), inline=False)

        recurring_entries = recurring.get("entries", [])
        recurring_lines = [f"`{e['key']}` (seen {e['hit_count']}×): {e['value'][:80]}" for e in recurring_entries] or ["(none)"]
        embed.add_field(name="Top recurring topics", value="\n".join(recurring_lines), inline=False)

        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MemoryCog(bot))
