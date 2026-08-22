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

import logging

import discord
from discord.ext import commands

from bot.config import Settings
from bot.services.umbrella_core_client import UmbrellaCoreClient

logger = logging.getLogger(__name__)

EXTENSIONS: tuple[str, ...] = (
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
)


class UmbrellaBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        super().__init__(command_prefix=settings.command_prefix, intents=intents)
        self.settings = settings
        self.core = UmbrellaCoreClient(settings.umbrella_core_url, settings.umbrella_core_api_key)

    async def setup_hook(self) -> None:
        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
                logger.info("Loaded extension: %s", extension)
            except Exception:
                logger.exception("Failed to load extension: %s", extension)

        await self.tree.sync()
        logger.info("Slash commands synced globally.")

    async def close(self) -> None:
        await super().close()

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (id=%s)", self.user, getattr(self.user, "id", "?"))
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(type=discord.ActivityType.watching, name="the server | /investigate"),
        )

    async def on_message(self, message: discord.Message) -> None:
        """Single global on_message — dispatches to cog listeners then
        processes prefix commands exactly once. Keeping process_commands
        here (not in any cog) prevents double-invocation - identical
        reasoning to Moo's bot.py."""
        if not message.author.bot:
            await self.process_commands(message)
