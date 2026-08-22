"""
bot/cogs/marketplace_cog.py — Closes Phase 7's stated loose end: umbrella-
core can tell you what Discord commands an installed plugin declares
(marketplace.install.discord_commands, joined against
GET /api/v1/capabilities for each command's param schema), but until this
cog, nothing in umbrella-discord ever turned that into a real, invokable
Discord slash command. See bot/services/marketplace_sync.py for the actual
fetch/diff/build/register logic - this cog only owns *when* that runs.

**Design decision: polling, not a core-side push, and why.** Stated
explicitly per this project's working convention of flagging real
decisions before building past them (see PHASE7-COMPLETE-AND-PHASE8-
HANDOFF.md's own framing of this exact question).

umbrella-core's event bus (services/events/bus.py) and webhook delivery
(services/webhooks/service.py, capabilities/webhooks.py) genuinely exist
as of Phase 7 - but grepping the whole umbrella-core-PHASE7-COMPLETE tree
for `EventBus.publish` shows only one topic is ever published,
"staff_escalation.created" (services/operational_intelligence/postmortem.py,
nl_query.py). Nothing in services/plugins/marketplace_service.py's
install()/uninstall() publishes anything - there is no
"marketplace.plugin_installed" (or similar) topic for a webhook
subscription to even receive. A genuine push design here isn't an
umbrella-discord change at all: it requires umbrella-core to start
publishing plugin-lifecycle events first, which is real, worthwhile,
correctly-scoped-as-separate follow-up work (that repo's own
marketplace_service.py module docstring already treats even in-repo
extensions to this exact flow carefully - see its "known limitation"
section) - not something to invent unreviewed from this side, in a
different repo, this session.

This also isn't a new pattern being introduced here - it's the existing
one. notifications_cog.py already made this exact call for staff
escalations, for the same reason stated in its own module docstring: "the
integration boundary in this whole project has only ever run one
direction - Discord calls core, never the reverse." That cog is the only
existing precedent in this codebase for "how does umbrella-discord notice
something changed in umbrella-core without a restart," and this one
follows it rather than inventing a second, different answer to the same
question:

- **On startup/reconnect**: `MarketplaceCommandSync.sync()` runs once via
  `before_loop`/`wait_until_ready()` - the identical gating
  notifications_cog.py already established - so a fresh process boot
  always picks up whatever is installed at that moment, no manual step
  required.
- **Periodically** (`_SYNC_INTERVAL_SECONDS`, independent of
  notifications_cog's unrelated 60s escalation-poll interval - marketplace
  installs are a rarer, more deliberate admin action than escalations, so
  a longer interval is the right trade-off here): an install/update/
  uninstall made *while the bot is already running* becomes live without
  a restart, bounded by this interval - an explicitly accepted staleness
  window, not a claim of true real-time push.
- **On demand**, via `/plugin_sync` below: an admin who just installed a
  plugin doesn't have to wait out that window. Discord-side
  `default_permissions(administrator=True)` here is the same "UX stopgap,
  not the real permission check" pattern hosting_cog.py's destructive
  commands and archive_search_cog.py already use -
  `marketplace.install.discord_commands` itself requires
  `marketplace.install.view` server-side regardless of what this
  decorator shows in the Discord UI client-side.

If umbrella-core later adds real plugin-lifecycle events, replacing the
periodic loop with a webhook receiver is a bounded change to this cog
alone - `MarketplaceCommandSync.sync()` itself doesn't know or care what
triggered it, so nothing in that module would need to change.
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.services.marketplace_sync import MarketplaceCommandSync, SyncOutcome

logger = logging.getLogger(__name__)

_SYNC_INTERVAL_SECONDS = 300  # 5 minutes - see module docstring for why this differs from notifications_cog's 60s.


class MarketplaceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.sync_service = MarketplaceCommandSync(bot)
        self.periodic_sync.start()

    async def cog_unload(self) -> None:
        self.periodic_sync.cancel()

    @tasks.loop(seconds=_SYNC_INTERVAL_SECONDS)
    async def periodic_sync(self) -> None:
        await self.sync_service.sync()

    @periodic_sync.before_loop
    async def before_periodic_sync(self) -> None:
        # tasks.loop runs its body immediately on .start(), so gating on
        # wait_until_ready() here is what makes the *first* run double as
        # the "on startup" sync this module's docstring promises - same
        # mechanism notifications_cog.py already relies on.
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="plugin_sync",
        description="[Staff] Re-sync installed plugins' Discord commands with umbrella-core right now.",
    )
    @app_commands.default_permissions(administrator=True)
    async def plugin_sync(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        outcome = await self.sync_service.sync()
        await interaction.followup.send(self._format_outcome(outcome), ephemeral=True)

    @staticmethod
    def _format_outcome(outcome: SyncOutcome) -> str:
        """Separated from the command body so it's testable without a live
        discord.Interaction - same reasoning as every other _format_* in
        this project."""
        if not outcome.added and not outcome.removed and not outcome.warnings:
            return "No changes — plugin commands already match umbrella-core."
        lines = []
        if outcome.added:
            lines.append(f"Registered/updated: {', '.join(f'/{n}' for n in outcome.added)}")
        if outcome.removed:
            lines.append(f"Removed: {', '.join(f'/{n}' for n in outcome.removed)}")
        if outcome.warnings:
            lines.append(f"{len(outcome.warnings)} command(s) skipped — see bot logs for details.")
        return "\n".join(lines)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MarketplaceCog(bot))
