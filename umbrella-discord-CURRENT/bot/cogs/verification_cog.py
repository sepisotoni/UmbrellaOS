"""
bot/cogs/verification_cog.py — Verification cog with message templates loaded
from umbrella-core settings (P16D).

Templates are fetched on cog load via GET /api/v1/settings/{key} and cached on
the cog instance.  A background task refreshes them every 5 minutes so staff
can edit wording from the dashboard without restarting the bot.

**render() helper**: uses simple $VARIABLE substitution — same convention as
the rest of the template system.  Variables are uppercased, so caller passes
keyword arguments in any case (e.g. player="Steve" -> replaces $PLAYER).

All other behaviour (DM detection, nickname sync, role assignment) is
unchanged from the previous revision; see the module docstring history in git
for the reasoning behind those implementation choices.
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

    # ------------------------------------------------------------------
    # Event listener
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # DMs only — message.guild is None is this project's existing discriminator.
        # Also skip the bot's own messages (success/error replies would re-trigger).
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
            if exc.code == "VERIFICATION_DISABLED":
                return
            if exc.code in ("NOT_FOUND", "VALIDATION_ERROR", "CONFLICT"):
                response = str(exc)
            else:
                response = (
                    "I'm not able to confirm verification codes right now — "
                    "please contact staff."
                )
            await message.channel.send(response)
            return

        player = result.get("player_username")
        response = result.get("discord_message")
        if not isinstance(player, str) or not player or not isinstance(response, str):
            logger.error(
                "Core returned an incomplete verification response for Discord user %s",
                message.author.id,
            )
            await message.channel.send(
                "Verification could not be completed right now — please contact staff."
            )
            return

        await message.channel.send(response)
        await self._sync_nickname(message.author, player)
        await self._assign_verified_role(message.author)

    # ------------------------------------------------------------------
    # Nickname & role helpers
    # ------------------------------------------------------------------

    async def _sync_nickname(self, user: discord.User, player_username: str) -> None:
        """Best-effort only — see module docstring.  Never raises."""
        nick = render(self._t("verification.nickname_format"), player=player_username)
        for guild in self.bot.guilds:
            member = guild.get_member(user.id)
            if member is None:
                continue
            try:
                await member.edit(
                    nick=nick, reason="Verification: synced to Minecraft username"
                )
            except discord.Forbidden:
                logger.warning(
                    "Nickname sync skipped for %s in guild %s: missing permission.",
                    user.id,
                    guild.id,
                )
            except discord.HTTPException:
                logger.exception(
                    "Nickname sync failed for %s in guild %s", user.id, guild.id
                )

    async def _assign_verified_role(self, user: discord.User) -> None:
        """Assign each guild's configured verified role. Best-effort only."""
        for guild in self.bot.guilds:
            member = guild.get_member(user.id)
            if member is None:
                continue
            config = self.bot.guild_configs.get(guild.id)
            role_id = config.verified_role_id if config else None
            if not role_id:
                continue
            verified_role = guild.get_role(role_id)
            if verified_role is None:
                logger.warning(
                    "Verified role %s not found in guild %s — skipping for %s.",
                    role_id,
                    guild.id,
                    user.id,
                )
                continue
            try:
                await member.add_roles(
                    verified_role, reason="Minecraft account verified"
                )
            except discord.Forbidden:
                logger.warning(
                    "Role assignment skipped for %s in guild %s: missing Manage Roles.",
                    user.id,
                    guild.id,
                )
            except discord.HTTPException:
                logger.exception(
                    "Role assignment failed for %s in guild %s", user.id, guild.id
                )

    # ------------------------------------------------------------------
    # Static helpers (kept separate so they're unit-testable)
    # ------------------------------------------------------------------

    @staticmethod
    def _looks_like_code(text: str) -> bool:
        return bool(_CODE_PATTERN.match(text))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VerificationCog(bot))
