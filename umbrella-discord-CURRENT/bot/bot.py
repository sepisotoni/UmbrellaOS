"""
bot/bot.py — umbrella-discord's bot, adapted from Moo-assistant's
bot/bot.py (bot lifecycle: intents, extension loading via setup_hook,
on_ready, single-dispatch on_message — all reused, that part of Moo's
design is solid and unrelated to the service-graph question).

The one deliberate, load-bearing difference: Moo's __init__ constructs
~15 in-process services (self.orchestrator, self.moderation_intel_service,
self.memory_service, ...) because it's a monolith - umbrella-core and
umbrella-discord are two separate deployable services here, so there is
no service graph to construct. There is exactly one integration point
(self.core, an UmbrellaCoreClient) - every cog is a thin caller into it,
per the Phase 6 roadmap requirement.

Consequences of that difference, also not carried over from Moo:
- No database engine/Base.metadata.create_all in setup_hook - umbrella-core
  owns the database entirely; this service has none of its own.
- No "seed defaults" call - same reason.
- No scheduler service - umbrella-core's own services/scheduler_loop.py
  and services/operational_intelligence/sampler_loop.py already own
  anything periodic; a second scheduler here would be a second, redundant
  one.
- No CodeExecutionService attachment - Moo's version was flagged during
  Phase 5 porting as real, unrestricted code execution gated only by an
  owner-only permission check, explicitly NOT a safe pattern to carry into
  a service any capability-holder can reach (see
  docs/adr/phase-7-notes-from-phase-5.md on the core side). Nothing here
  reintroduces it.
"""

from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from bot.config import (
    BotTokenUnavailable,
    GuildConfig,
    RemoteConfig,
    Settings,
    fetch_bot_config,
    fetch_discord_bot_token,
)
from bot.services.umbrella_core_client import UmbrellaCoreClient, UmbrellaCoreError

logger = logging.getLogger(__name__)

TOKEN_POLL_INTERVAL_SECONDS = 30

EXTENSIONS: tuple[str, ...] = (
    "bot.cogs.ask_cog",
    "bot.cogs.investigation_cog",
    "bot.cogs.moderation_report_cog",
    "bot.cogs.knowledge_cog",
    "bot.cogs.memory_cog",
    "bot.cogs.operational_intelligence_cog",
    "bot.cogs.player_risk_cog",
    "bot.cogs.hosting_cog",
    "bot.cogs.archive_search_cog",
    "bot.cogs.verification_cog",
    "bot.cogs.notifications_cog",
    "bot.cogs.marketplace_cog",
    "bot.cogs.webhook_cog",
    "bot.cogs.bridge_cog",
)


class UmbrellaBot(commands.Bot):
    def __init__(
        self,
        settings: Settings,
        discord_token: str,
        *,
        core: UmbrellaCoreClient | None = None,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        # command_prefix defaults to "!" here; the actual value from core's
        # settings API is stored in self.remote after setup_hook runs. The
        # prefix cannot be changed after construction without subclassing
        # get_prefix(), and "!" matches the RemoteConfig default anyway.
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self._discord_token = discord_token
        # timeout=90s: the default 30s wraps the full round-trip including the
        # upstream LLM call inside umbrella-core. Providers have their own 30s
        # timeout, but orchestrator overhead (DB reads, constitution build, dual
        # review, decision log write) adds ~5-10s on top. With 30s client timeout
        # and 30s provider timeout, a slow-but-valid LLM response causes the bot
        # to raise "Could not reach umbrella-core" before core even replies.
        # 90s gives the provider its full 30s plus 60s of headroom.
        self.core = core or UmbrellaCoreClient(
            settings.umbrella_core_url,
            settings.umbrella_core_api_key,
            timeout=90.0,
        )
        # Populated by setup_hook after fetching from core's settings API.
        self.remote: RemoteConfig | None = None
        self.guild_configs: dict[int, GuildConfig] = {}
        self._token_watch_task: asyncio.Task[None] | None = None

    async def setup_hook(self) -> None:
        # Fetch remote config from core before loading extensions so cogs
        # can access self.bot.remote (via self.bot) from their __init__.
        self.remote = await fetch_bot_config(self.core)
        logger.info(
            "Bot-wide RemoteConfig loaded — callback_port=%s",
            self.remote.callback_port,
        )

        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
                logger.info("Loaded extension: %s", extension)
            except Exception:
                logger.exception("Failed to load extension: %s", extension)

        await self.tree.sync()
        logger.info("Slash commands synced globally.")

        # Push command manifest to core so the dashboard can read real command data.
        try:
            tree_commands = self.tree.get_commands()
            manifest = []
            for cmd in tree_commands:
                manifest.append(
                    {
                        "name": cmd.name,
                        "description": getattr(cmd, "description", "") or "",
                        "args": " ".join(
                            f"<{p.name}>" if p.required else f"[{p.name}]"
                            for p in (getattr(cmd, "parameters", []) or [])
                        ),
                        "owner_only": any(
                            c.__class__.__name__ == "OwnerRoleCheck"
                            for c in (getattr(cmd, "checks", []) or [])
                        ),
                    }
                )
            await self.core.push_command_manifest(manifest)
            logger.info("Pushed %d commands to core manifest.", len(manifest))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to push command manifest: %s", exc)

        self._token_watch_task = asyncio.create_task(self._watch_discord_token())

    async def close(self) -> None:
        task = self._token_watch_task
        if (
            task is not None
            and task is not asyncio.current_task()
            and not task.done()
        ):
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self._token_watch_task = None
        await super().close()

    async def _watch_discord_token(self) -> None:
        while not self.is_closed():
            await asyncio.sleep(TOKEN_POLL_INTERVAL_SECONDS)
            try:
                token = await fetch_discord_bot_token(self.core)
            except BotTokenUnavailable as exc:
                logger.error("%s; disconnecting until Core has a token again.", exc)
                await self.close()
                return
            except UmbrellaCoreError as exc:
                logger.warning(
                    "Could not check the Discord token in Core (status=%s); "
                    "keeping the current session.",
                    exc.status_code,
                )
                continue

            if token != self._discord_token:
                logger.info("Discord bot token changed in Core; reconnecting.")
                await self.close()
                return
            await self._refresh_guild_configs()

    async def _refresh_guild_configs(self) -> None:
        try:
            data = await self.core.get_guilds()
            configs = {
                config.guild_id: config for config in map(GuildConfig.from_api, data)
            }
            if set(configs) != {guild.id for guild in self.guilds}:
                await self._sync_guilds_with_core()
            else:
                self.guild_configs = configs
        except (UmbrellaCoreError, KeyError, TypeError, ValueError):
            logger.exception("Failed to refresh per-guild Discord configuration.")

    async def _sync_guilds_with_core(self) -> None:
        """Publish all joined guilds and load each guild's saved configuration."""
        guilds = self.guilds
        payload = [
            {
                "guild_id": str(guild.id),
                "name": guild.name,
                "channels": [
                    {
                        "id": str(channel.id),
                        "name": channel.name,
                        "category": channel.category.name if channel.category else None,
                    }
                    for channel in guild.text_channels
                ],
                "roles": [
                    {
                        "id": str(role.id),
                        "name": role.name,
                        "color": role.color.value,
                        "mentionable": role.mentionable,
                    }
                    for role in guild.roles
                ],
            }
            for guild in guilds
        ]

        try:
            data = await self.core.sync_guilds(payload)
            self.guild_configs = {
                config.guild_id: config for config in map(GuildConfig.from_api, data)
            }
            logger.info("Synchronized %d Discord guild(s) with Core.", len(guilds))
        except (UmbrellaCoreError, KeyError, TypeError, ValueError):
            logger.exception("Failed to synchronize Discord guilds with Core.")

    async def _sync_guild_commands(self, guild: discord.Guild) -> None:
        guild_ref = discord.Object(id=guild.id)
        self.tree.clear_commands(guild=guild_ref)
        self.tree.copy_global_to(guild=guild_ref)
        await self.tree.sync(guild=guild_ref)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self._sync_guild_commands(guild)
        await self._sync_guilds_with_core()

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        logger.info("Removed from Discord guild %s (%s).", guild.name, guild.id)
        await self._sync_guilds_with_core()

    async def on_guild_update(
        self, before: discord.Guild, after: discord.Guild
    ) -> None:
        if before.name != after.name:
            await self._sync_guilds_with_core()

    async def on_guild_channel_create(
        self, channel: discord.abc.GuildChannel
    ) -> None:
        await self._sync_guilds_with_core()

    async def on_guild_channel_delete(
        self, channel: discord.abc.GuildChannel
    ) -> None:
        await self._sync_guilds_with_core()

    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ) -> None:
        await self._sync_guilds_with_core()

    async def on_guild_role_create(self, role: discord.Role) -> None:
        await self._sync_guilds_with_core()

    async def on_guild_role_delete(self, role: discord.Role) -> None:
        await self._sync_guilds_with_core()

    async def on_guild_role_update(
        self, before: discord.Role, after: discord.Role
    ) -> None:
        await self._sync_guilds_with_core()

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (id=%s)", self.user, getattr(self.user, "id", "?"))
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="your servers | /investigate"
            ),
        )
        await self._sync_guilds_with_core()
        for guild in self.guilds:
            await self._sync_guild_commands(guild)

    async def on_message(self, message: discord.Message) -> None:
        """Single global on_message — dispatches to cog listeners then
        processes prefix commands exactly once. Keeping process_commands
        here (not in any cog) prevents double-invocation - identical
        reasoning to Moo's bot.py."""
        if not message.author.bot:
            await self.process_commands(message)
