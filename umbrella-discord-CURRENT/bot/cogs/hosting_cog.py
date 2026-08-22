"""
bot/cogs/hosting_cog.py — Seventh proof of the "thin caller" pattern, over
umbrella-core's hosting.* capabilities (capabilities/hosting.py). No
hosting/orchestration logic lives here — that's services/server_service.py
and friends on the core side.

Like operational_intelligence and player_risk, there is **no Moo-assistant
precedent** to port - Moo has zero Minecraft server-management
responsibility (its only adjacent commands, in control_panel_cog.py, are
live Python code execution and scheduling, explicitly flagged in bot.py's
docstring as NOT carried into umbrella-discord). Hosting is entirely
umbrella-daemon/-dashboard territory (Phases 0-4), being reached from
Discord for the first time here.

**Scope decision, flagged rather than silently made**: capabilities/hosting.py
has ~15 capabilities across five sub-domains - node registration, template
management, allocation management, server lifecycle, and backups. This cog
deliberately covers only a read-and-safe-control subset of the server
lifecycle:
  - hosting.server.list / .get / .stats   (read-only)
  - hosting.server.start / .stop          (destructive=False, reversible=True
    on both, per their own @capability declarations)

Since added, with their own gate rather than the read/safe-control pattern:
  - hosting.server.restart / .kill / .delete — each is declared
    destructive=True, reversible=False in capabilities/hosting.py itself
    (restart's own comment: "a restart isn't undoable"). Each now requires
    an explicit Confirm/Cancel button press (_ConfirmDestructiveView)
    before the capability is invoked at all - checked against real
    discord.py 2.7.1 rather than assumed: View.wait() returns True on
    timeout / False when stop() is called (discord/ui/view.py), and
    interaction_check() is the real mechanism for restricting who can
    press the buttons to the person who ran the command. Also gated with
    @app_commands.default_permissions(administrator=True) as a Discord-side
    floor, same reasoning as archive_search_cog.py's stopgap: until the
    slash-command -> REST-permission mapping exists, every cog shares one
    bot-wide API key, so these three (delete especially - it requires the
    stricter hosting.server.manage core-side, one tier above restart/kill's
    hosting.server.control) get the narrowest available Discord-side floor
    rather than none at all.
  - hosting.node.* / .template.* / .allocation.* / .backup.* /
    .reconcile* — infrastructure provisioning and backup lifecycle
    management. No evidence this needs a Discord surface at all (the
    dashboard is the natural home for "register a node" or "create a
    template" - those aren't per-incident, in-the-moment actions the way
    "is server X up" or "restart server X" are). Left to a future,
    deliberate scope decision rather than built speculatively.

hosting.server.create is also excluded for the same "provisioning belongs
on the dashboard, not chat" reasoning, plus its own params_model
(CreateServerParams: node_id, template_id, allocation_ids, memory/cpu
overrides) is not something a Discord slash command's flat string/int
options represent well without a much more elaborate UX than any other
cog here needed.
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.umbrella_core_client import UmbrellaCoreError

logger = logging.getLogger(__name__)

_STATUS_COLORS = {
    "running": discord.Color.green(),
    "stopped": discord.Color.light_grey(),
    "starting": discord.Color.gold(),
    "stopping": discord.Color.gold(),
    "crashed": discord.Color.red(),
}


class _ConfirmDestructiveView(discord.ui.View):
    """Confirm/cancel gate for irreversible hosting actions. Not a
    _format_*-style pure function - it's inherently a live-gateway
    component (buttons, message edits) - so it isn't unit-tested the way
    the rest of this cog is; see tests/test_hosting_cog.py's module
    docstring for the project's general rule on what is and isn't
    pure-function-testable.
    """

    def __init__(self, *, author_id: int, timeout: float = 30.0) -> None:
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.confirmed: bool | None = None
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the person who ran this command can confirm or cancel it.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.confirmed = True
        self.stop()
        await interaction.response.edit_message(content="Confirmed — working...", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.confirmed = False
        self.stop()
        await interaction.response.edit_message(content="Cancelled.", view=None)

    async def on_timeout(self) -> None:
        self.confirmed = False
        if self.message is not None:
            try:
                await self.message.edit(content="Confirmation timed out — no action taken.", view=None)
            except discord.HTTPException:
                pass


class HostingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _confirm(self, interaction: discord.Interaction, prompt: str) -> bool:
        """Sends the confirm/cancel prompt on the original interaction and
        waits for a response. Returns True only if Confirm was pressed."""
        view = _ConfirmDestructiveView(author_id=interaction.user.id)
        await interaction.response.send_message(prompt, view=view, ephemeral=True)
        view.message = await interaction.original_response()
        await view.wait()
        return bool(view.confirmed)

    @app_commands.command(name="server_list", description="List hosted servers, optionally filtered to one node.")
    @app_commands.describe(node_id="Only show servers on this node (optional)")
    async def server_list(self, interaction: discord.Interaction, node_id: str | None = None) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            servers = await self.bot.core.invoke(
                "hosting.server.list", {"node_id": node_id}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(embed=self._format_server_list(servers), ephemeral=True)

    @app_commands.command(name="server_status", description="Get one server's current state.")
    @app_commands.describe(server_id="The server's ID")
    async def server_status(self, interaction: discord.Interaction, server_id: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            server = await self.bot.core.invoke(
                "hosting.server.get", {"server_id": server_id}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(embed=self._format_server_status(server), ephemeral=True)

    @app_commands.command(name="server_stats", description="Fetch one live CPU/memory/network snapshot for a server.")
    @app_commands.describe(server_id="The server's ID")
    async def server_stats(self, interaction: discord.Interaction, server_id: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            stats = await self.bot.core.invoke(
                "hosting.server.stats", {"server_id": server_id}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(embed=self._format_server_stats(server_id, stats), ephemeral=True)

    @app_commands.command(name="server_start", description="Start a server.")
    @app_commands.describe(server_id="The server's ID")
    async def server_start(self, interaction: discord.Interaction, server_id: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            server = await self.bot.core.invoke(
                "hosting.server.start", {"server_id": server_id}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(f"✅ Starting **{server.get('name', server_id)}**.", ephemeral=True)

    @app_commands.command(name="server_stop", description="Gracefully stop a server.")
    @app_commands.describe(server_id="The server's ID", grace_period_seconds="Seconds to wait before force-stopping (optional)")
    async def server_stop(
        self, interaction: discord.Interaction, server_id: str, grace_period_seconds: int | None = None
    ) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            server = await self.bot.core.invoke(
                "hosting.server.stop",
                {"server_id": server_id, "grace_period_seconds": grace_period_seconds},
                discord_user_id=str(interaction.user.id),
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(f"🛑 Stopping **{server.get('name', server_id)}**.", ephemeral=True)

    @app_commands.command(name="server_restart", description="[Staff] Restart a server. Irreversible — requires confirmation.")
    @app_commands.describe(server_id="The server's ID")
    @app_commands.default_permissions(administrator=True)
    async def server_restart(self, interaction: discord.Interaction, server_id: str) -> None:
        confirmed = await self._confirm(interaction, f"⚠️ Restart server `{server_id}`? This is not reversible.")
        if not confirmed:
            return

        try:
            server = await self.bot.core.invoke(
                "hosting.server.restart", {"server_id": server_id}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(f"🔄 Restarted **{server.get('name', server_id)}**.", ephemeral=True)

    @app_commands.command(name="server_kill", description="[Staff] Forcibly kill a server with no grace period. Irreversible — requires confirmation.")
    @app_commands.describe(server_id="The server's ID")
    @app_commands.default_permissions(administrator=True)
    async def server_kill(self, interaction: discord.Interaction, server_id: str) -> None:
        confirmed = await self._confirm(
            interaction, f"⚠️ **Force-kill** server `{server_id}` with no grace period? This is not reversible."
        )
        if not confirmed:
            return

        try:
            server = await self.bot.core.invoke(
                "hosting.server.kill", {"server_id": server_id}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(f"💀 Killed **{server.get('name', server_id)}**.", ephemeral=True)

    @app_commands.command(name="server_delete", description="[Staff] Permanently delete a server and release its allocations. Requires confirmation.")
    @app_commands.describe(server_id="The server's ID")
    @app_commands.default_permissions(administrator=True)
    async def server_delete(self, interaction: discord.Interaction, server_id: str) -> None:
        confirmed = await self._confirm(
            interaction, f"🛑 **Permanently delete** server `{server_id}` and release its allocations? This is not reversible."
        )
        if not confirmed:
            return

        try:
            await self.bot.core.invoke(
                "hosting.server.delete", {"server_id": server_id}, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(f"🗑️ Deleted server `{server_id}`.", ephemeral=True)

    @staticmethod
    def _format_error(exc: UmbrellaCoreError) -> str:
        """Separated from the command bodies so it's testable without a
        live discord.Interaction - see tests/test_hosting_cog.py."""
        if exc.status_code == 403:
            return "You don't have permission to manage hosting."
        if exc.status_code == 404:
            return "No server found with that ID."
        return f"Hosting request failed: {exc}"

    @staticmethod
    def _format_server_list(servers: list) -> discord.Embed:
        """Pure function, testable without discord.py's interaction/gateway
        machinery - same reasoning as every other _format_* in this project."""
        embed = discord.Embed(title="Servers", color=discord.Color.blurple())
        if not servers:
            embed.add_field(name="No servers", value="No servers matched.", inline=False)
            return embed
        lines = [f"`{s['id']}` **{s['name']}** — {s['status']}" for s in servers]
        embed.description = "\n".join(lines)
        return embed

    @staticmethod
    def _format_server_status(server: dict) -> discord.Embed:
        status = server.get("status", "unknown")
        embed = discord.Embed(
            title=server.get("name", "?"),
            color=_STATUS_COLORS.get(status, discord.Color.light_grey()),
        )
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Node", value=server.get("node_id", "?"), inline=True)
        embed.add_field(name="Memory", value=f"{server.get('memory_bytes', 0) / (1024**2):.0f} MB", inline=True)
        embed.add_field(name="CPU cores", value=str(server.get("cpu_cores", "?")), inline=True)
        embed.set_footer(text=f"ID: {server.get('id', '?')}")
        return embed

    @staticmethod
    def _format_server_stats(server_id: str, stats: dict) -> discord.Embed:
        embed = discord.Embed(title=f"Live stats: {server_id}", color=discord.Color.blurple())
        embed.add_field(name="CPU", value=f"{stats.get('cpu_percent', 0):.1f}%", inline=True)
        mem_used = stats.get("memory_used_bytes", 0) / (1024**2)
        mem_limit = stats.get("memory_limit_bytes", 0) / (1024**2)
        embed.add_field(name="Memory", value=f"{mem_used:.0f} / {mem_limit:.0f} MB", inline=True)
        rx = stats.get("network_rx_bytes", 0) / (1024**2)
        tx = stats.get("network_tx_bytes", 0) / (1024**2)
        embed.add_field(name="Network", value=f"↓{rx:.1f} MB / ↑{tx:.1f} MB", inline=True)
        embed.set_footer(text=f"Sampled at {stats.get('timestamp', '?')}")
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HostingCog(bot))
