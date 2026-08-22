"""
bot/cogs/verification_cog.py — Ninth cog, and the completion point for the
nickname-sync TODO originally left in umbrella-core's
api/routers/verification.py (now capabilities/verification.py). Thin
caller over the new verification.confirm capability
(capabilities/verification.py) for the actual link/unlink state - the one
genuinely new piece of logic here, unavoidably, is the DM listener itself
and the nickname sync, neither of which has a capability to call because
neither is possible from umbrella-core's process (no live gateway there -
see capabilities/verification.py's own docstring on this).

**DM detection, checked against real discord.py 2.7.1 rather than assumed**:
there is no dedicated "on_dm" event. Every message, guild or DM, dispatches
`on_message`; a DM is distinguished by `message.guild is None` (also
`isinstance(message.channel, discord.DMChannel)` works, since DMChannel
subclasses discord.abc.PrivateChannel - discord.py's own
ext/commands/cooldowns.py uses exactly that isinstance check internally).
This project's own Moo-derived precedent (moo-source's archive_cog.py)
already uses `message.guild is None` as its guild/DM discriminator (there,
inverted, to *skip* DMs) - matching that existing idiom rather than
introducing a second way to ask the same question.

Also confirmed against source rather than memory: adding
`@commands.Cog.listener()` for `on_message` in a cog does NOT conflict
with or replace commands.Bot's own on_message (which just calls
process_commands() - see ext/commands/bot.py's BotBase.on_message). Cog
listeners are dispatched independently and additively; this is the exact
scenario discord.py's own Client.event docstring uses as its worked
example.

**Nickname sync**: a DM has no attached guild (message.guild is None, by
definition, for the very listener that triggers this), so which guild(s)
to set a nickname in isn't available from the triggering message itself -
this cog iterates every guild the bot shares with the verifying user
(self.bot.guilds -> guild.get_member(user.id)) rather than requiring a new
"home guild" setting in bot/config.py. Reasonable default for what's
almost certainly a single-server deployment (matches "UmbrellaOS" being
one community's Minecraft+Discord platform, not a general-purpose
multi-tenant bot), and degrades correctly for a multi-guild bot too
(applies in every shared guild, skips guilds where the user isn't a
member). Wrapped per-guild in its own try/except: a nickname failure
(bot's top role below the member's, missing Manage Nicknames, an
unexpected 4xx) is logged and skipped, never surfaced to the user as if
verification itself failed - by the time nickname sync runs,
verification.confirm has already returned success and the link already
exists on the umbrella-core side.

**Verified role assignment**: if DISCORD_VERIFIED_ROLE_ID is set in .env,
the role is assigned after successful nickname sync. Best-effort only —
missing role or missing permissions are logged and skipped, never raised.
"""
from __future__ import annotations

import logging
import re

import discord
from discord.ext import commands

from bot.services.umbrella_core_client import UmbrellaCoreError

logger = logging.getLogger(__name__)

_CODE_PATTERN = re.compile(r"^\d{6}$")


class VerificationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # DMs only - message.guild is None is this project's existing
        # discriminator (see module docstring). Also skip the bot's own
        # messages (including its own success/error replies below, which
        # would otherwise re-trigger this same listener).
        if message.guild is not None or message.author.bot:
            return

        code = message.content.strip()
        if not self._looks_like_code(code):
            return

        try:
            result = await self.bot.core.invoke(
                "verification.confirm",
                {
                    "discord_id": str(message.author.id),
                    "discord_username": str(message.author),
                    "code": code,
                },
                discord_user_id=str(message.author.id),
            )
        except UmbrellaCoreError as exc:
            await message.channel.send(self._format_error(exc))
            return

        await message.channel.send(self._format_success(result))
        await self._sync_nickname(message.author, result["player_username"])
        await self._assign_verified_role(message.author)

    async def _sync_nickname(self, user: discord.User, player_username: str) -> None:
        """Best-effort only - see module docstring. Never raises; a
        failure here must never look like a verification failure to the
        user, since verification.confirm already succeeded by the time
        this runs."""
        for guild in self.bot.guilds:
            member = guild.get_member(user.id)
            if member is None:
                continue
            try:
                await member.edit(nick=player_username, reason="Verification: synced to Minecraft username")
            except discord.Forbidden:
                logger.warning(
                    "Nickname sync skipped for %s in guild %s: missing permission (bot role below member's, or no Manage Nicknames).",
                    user.id, guild.id,
                )
            except discord.HTTPException:
                logger.exception("Nickname sync failed for %s in guild %s", user.id, guild.id)

    async def _assign_verified_role(self, user: discord.User) -> None:
        """Assign DISCORD_VERIFIED_ROLE_ID to the member in every shared guild.
        Best-effort only — missing role or missing Manage Roles permission
        is logged and skipped, never raised to the user."""
        role_id: int = getattr(self.bot.settings, "discord_verified_role_id", 0)
        if not role_id:
            return
        for guild in self.bot.guilds:
            member = guild.get_member(user.id)
            if member is None:
                continue
            verified_role = guild.get_role(role_id)
            if verified_role is None:
                logger.warning(
                    "Verified role %s not found in guild %s — skipping role assignment for %s.",
                    role_id, guild.id, user.id,
                )
                continue
            try:
                await member.add_roles(verified_role, reason="Minecraft account verified")
            except discord.Forbidden:
                logger.warning(
                    "Role assignment skipped for %s in guild %s: missing Manage Roles permission.",
                    user.id, guild.id,
                )
            except discord.HTTPException:
                logger.exception("Role assignment failed for %s in guild %s", user.id, guild.id)

    @staticmethod
    def _looks_like_code(text: str) -> bool:
        """Separated from on_message so it's testable without a live
        discord.Message - see tests/test_verification_cog.py. Matches
        the 6-digit format api/routers/verification.py's request_verification
        (and now services/verification/service.py) always generates."""
        return bool(_CODE_PATTERN.match(text))

    @staticmethod
    def _format_error(exc: UmbrellaCoreError) -> str:
        """Separated from on_message for the same reason as _looks_like_code."""
        if exc.status_code == 403:
            return "I'm not able to confirm verification codes right now — please contact staff."
        if exc.status_code == 404:
            return "I couldn't find that verification code. Double-check it and try again."
        if exc.status_code == 422:
            return f"That code can't be used: {exc}"
        if exc.status_code == 409:
            return str(exc)
        return f"Verification failed: {exc}"

    @staticmethod
    def _format_success(result: dict) -> str:
        """Separated from on_message for the same reason as _looks_like_code."""
        if result.get("already_linked"):
            return f"✅ You're already verified as **{result['player_username']}**."
        return f"✅ Verified! Your Discord account is now linked to **{result['player_username']}**."


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VerificationCog(bot))
