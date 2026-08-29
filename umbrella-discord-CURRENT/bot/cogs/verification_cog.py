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
from discord.ext import commands, tasks

from bot.services.umbrella_core_client import UmbrellaCoreError

logger = logging.getLogger(__name__)

_CODE_PATTERN = re.compile(r"^\d{6}$")

# Keys fetched from core settings on startup / every 5 minutes.
_TEMPLATE_KEYS: list[str] = [
    "verification.dm_prompt",
    "verification.success_message",
    "verification.error_already_linked",
    "verification.error_invalid_code",
    "verification.ingame_prompt",
    "verification.ingame_success",
    "verification.nickname_format",
]

# Fallback strings used when a core fetch fails so the bot remains functional.
_DEFAULTS: dict[str, str] = {
    "verification.dm_prompt": (
        "Hi $PLAYER! To verify your Minecraft account, send this code in-game: $CODE"
        " (expires in $EXPIRES)"
    ),
    "verification.success_message": (
        "\u2705 Your Minecraft account **$PLAYER** has been successfully linked!"
    ),
    "verification.error_already_linked": (
        "\u274c This Discord account is already linked to a Minecraft account."
    ),
    "verification.error_invalid_code": (
        "\u274c Invalid or expired code. Please run /verify in-game again."
    ),
    "verification.ingame_prompt": (
        "Check your Discord DMs to complete verification! Code expires in $EXPIRES."
    ),
    "verification.ingame_success": (
        "\u2705 Your Discord account has been linked successfully!"
    ),
    "verification.nickname_format": "$PLAYER",
}


def render(template: str, **kwargs: str) -> str:
    """Replace $VARIABLE placeholders in *template* with *kwargs* values.

    Variable names are matched case-insensitively: ``render(t, player="Steve")``
    replaces ``$PLAYER``.  Unknown placeholders are left as-is.
    """
    for key, val in kwargs.items():
        template = template.replace(f"${key.upper()}", str(val))
    return template


class VerificationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Template cache — populated by _load_templates() on cog load.
        self._templates: dict[str, str] = dict(_DEFAULTS)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def cog_load(self) -> None:
        """Fetch templates from core then start the 5-minute refresh loop."""
        await self._load_templates()
        self._refresh_templates.start()

    async def cog_unload(self) -> None:
        self._refresh_templates.cancel()

    # ------------------------------------------------------------------
    # Template management
    # ------------------------------------------------------------------

    async def _load_templates(self) -> None:
        """Fetch every verification.* template from core and update the cache.

        A failure for any individual key is logged and the cached default is
        kept so the bot stays functional even if core is temporarily unreachable.
        """
        for key in _TEMPLATE_KEYS:
            try:
                # umbrella_core_client exposes a thin async HTTP wrapper;
                # GET /api/v1/settings/{key} returns {"key":..., "value":..., ...}
                data: dict = await self.bot.core.get(f"/api/v1/settings/{key}")
                value = data.get("value", "").strip()
                if value and value != "***":
                    self._templates[key] = value
                    logger.debug("Template loaded: %s", key)
            except Exception as exc:  # network error, 404, etc.
                logger.warning(
                    "Could not load template %r from core (%s) — keeping cached value.",
                    key, exc,
                )

    @tasks.loop(minutes=5)
    async def _refresh_templates(self) -> None:
        """Background task: refresh template cache every 5 minutes."""
        await self._load_templates()

    @_refresh_templates.before_loop
    async def _before_refresh(self) -> None:
        await self.bot.wait_until_ready()

    def _t(self, key: str) -> str:
        """Return the cached template for *key*, falling back to the built-in default."""
        return self._templates.get(key, _DEFAULTS.get(key, f"[missing template: {key}]"))

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

        # Respect verification.enabled master toggle — silently skip if disabled
        # so users don't get confusing responses when verification is turned off.
        try:
            setting = await self.bot.core.get(f"/api/v1/settings/verification.enabled")
            if setting.get("value", "true").lower() in ("false", "0", "no", "off"):
                return
        except Exception:
            pass  # If we can't read the setting, proceed — fail open is safer

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

        player = result.get("player_username", "")
        await message.channel.send(self._format_success(result, player))
        await self._sync_nickname(message.author, player)
        await self._assign_verified_role(message.author)

    # ------------------------------------------------------------------
    # Formatting helpers (use cached templates)
    # ------------------------------------------------------------------

    def _format_success(self, result: dict, player: str) -> str:
        if result.get("already_linked"):
            return f"\u2705 You're already verified as **{player}**."
        return render(self._t("verification.success_message"), player=player)

    def _format_error(self, exc: UmbrellaCoreError) -> str:
        if exc.status_code == 403:
            return "I'm not able to confirm verification codes right now — please contact staff."
        if exc.status_code == 409:
            return render(self._t("verification.error_already_linked"))
        if exc.status_code in (404, 422):
            return render(self._t("verification.error_invalid_code"))
        return f"Verification failed: {exc}"

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
                await member.edit(nick=nick, reason="Verification: synced to Minecraft username")
            except discord.Forbidden:
                logger.warning(
                    "Nickname sync skipped for %s in guild %s: missing permission.",
                    user.id, guild.id,
                )
            except discord.HTTPException:
                logger.exception("Nickname sync failed for %s in guild %s", user.id, guild.id)

    async def _assign_verified_role(self, user: discord.User) -> None:
        """Assign the verified role from RemoteConfig.  Best-effort only.

        FIX (HIGH): was reading self.bot.settings.discord_verified_role_id, which
        does not exist on Settings (Settings only carries discord_bot_token,
        umbrella_core_url, umbrella_core_api_key).  getattr() silently returned 0
        every time, so verified-role assignment was always silently skipped.
        Corrected to self.bot.remote.verified_role_id, the RemoteConfig field
        populated from core's discord.verified_role_id setting at startup.
        """
        remote = getattr(self.bot, "remote", None)
        role_id: int = getattr(remote, "verified_role_id", 0) or 0
        if not role_id:
            return
        for guild in self.bot.guilds:
            member = guild.get_member(user.id)
            if member is None:
                continue
            verified_role = guild.get_role(role_id)
            if verified_role is None:
                logger.warning(
                    "Verified role %s not found in guild %s — skipping for %s.",
                    role_id, guild.id, user.id,
                )
                continue
            try:
                await member.add_roles(verified_role, reason="Minecraft account verified")
            except discord.Forbidden:
                logger.warning(
                    "Role assignment skipped for %s in guild %s: missing Manage Roles.",
                    user.id, guild.id,
                )
            except discord.HTTPException:
                logger.exception("Role assignment failed for %s in guild %s", user.id, guild.id)

    # ------------------------------------------------------------------
    # Static helpers (kept separate so they're unit-testable)
    # ------------------------------------------------------------------

    @staticmethod
    def _looks_like_code(text: str) -> bool:
        return bool(_CODE_PATTERN.match(text))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VerificationCog(bot))
