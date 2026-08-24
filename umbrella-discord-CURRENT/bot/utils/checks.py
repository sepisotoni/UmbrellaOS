"""
bot/utils/checks.py — Reusable app_commands checks for role-based
access control inside umbrella-discord.

Discord's built-in `default_permissions` gates commands on Discord
*permission bits* (e.g. administrator, manage_guild), which is coarse and
tied to the guild's role hierarchy rather than Umbrella-specific roles.
These checks instead inspect the invoking member's *role IDs* against the
configured owner_role_id — giving the MOON server precise control over who
can run which commands without touching Discord permission settings.

Usage
-----
    from bot.utils.checks import require_owner_role

    @app_commands.command(...)
    @require_owner_role()
    async def my_command(self, interaction: discord.Interaction) -> None:
        ...

If `owner_role_id` is 0 / unset in config, the check falls back to
`interaction.user.guild_permissions.administrator` so commands remain
guarded even in a dev environment without a specific role configured.
"""
from __future__ import annotations

import discord
from discord import app_commands


def require_owner_role() -> app_commands.check:
    """app_commands decorator that restricts a command to members with the
    configured owner_role_id (or administrator permission as fallback)."""

    async def predicate(interaction: discord.Interaction) -> bool:
        # In DMs there's no guild / roles — always deny.
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "This command can only be used inside the server.", ephemeral=True
            )
            return False

        # Retrieve the configured role ID from bot.settings.
        settings = getattr(interaction.client, "settings", None)
        owner_role_id: int = getattr(settings, "owner_role_id", 0) or 0

        if owner_role_id:
            has_role = any(r.id == owner_role_id for r in member.roles)
        else:
            # Fallback: administrator permission bit when role not configured.
            has_role = member.guild_permissions.administrator

        if not has_role:
            await interaction.response.send_message(
                "You need the **Owner** role to run this command.", ephemeral=True
            )
        return has_role

    return app_commands.check(predicate)
