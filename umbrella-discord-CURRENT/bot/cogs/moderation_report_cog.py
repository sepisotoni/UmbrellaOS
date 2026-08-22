"""
bot/cogs/moderation_report_cog.py — Second proof of the "thin caller"
pattern, same shape as investigation_cog.py: a slash command that calls
into umbrella-core and formats the result. No moderation logic lives
here — that's services/moderation_intelligence/service.py on the core
side.

One real difference from Moo-assistant's moderation_intel_cog.py worth
noting rather than silently carrying over: Moo's bot.moderation_intel_service
.analyze_report() does report-creation and AI analysis as a single
in-process call, because it's a monolith. umbrella-core exposes those as
two separate capabilities — moderation_intelligence.report.create and
moderation_intelligence.report.analyze — matching the Capability Registry's
one-capability-one-action shape (create_report() and analyze_report() are
two separate functions in capabilities/moderation_intelligence.py, not one).
This cog calls both in sequence to reproduce the single-command UX Moo had;
that's still "thin" — it's plumbing two existing operations together, not
implementing any judgment of its own about what happens between them.

Deliberately NOT ported here: Moo's spam/raid heuristic listeners
(on_message, on_member_join in moderation_intel_cog.py) and the prefix
!report command. Both need a live-gateway decision (where do heuristic
detectors run, what rate-limits/state do they need) that's exactly the
kind of thing flagged rather than silently built past — see the handoff
doc's "not started" list. Only the explicit /report slash command — the
part with a direct, unambiguous umbrella-core capability to call — is
built now.
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.umbrella_core_client import UmbrellaCoreError

logger = logging.getLogger(__name__)


class ModerationReportCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="report", description="Report a member for AI-assisted moderation review.")
    @app_commands.describe(member="The member to report", reason="What happened?")
    async def report(self, interaction: discord.Interaction, member: discord.Member, reason: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            created = await self.bot.core.invoke(
                "moderation_intelligence.report.create",
                {
                    "reported_user_id": str(member.id),
                    "reason": reason,
                    "channel_id": str(interaction.channel_id) if interaction.channel_id else None,
                },
                discord_user_id=str(interaction.user.id),
            )
            analysis = await self.bot.core.invoke(
                "moderation_intelligence.report.analyze",
                {"report_id": created["id"]},
                discord_user_id=str(interaction.user.id),
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc), ephemeral=True)
            return

        await interaction.followup.send(self._format_result(member, analysis), ephemeral=True)

    @staticmethod
    def _format_error(exc: UmbrellaCoreError) -> str:
        """Separated from the command body so it's testable without a
        live discord.Interaction - see tests/test_moderation_report_cog.py."""
        if exc.status_code == 403:
            return "You don't have permission to submit moderation reports."
        return f"Report failed: {exc}"

    @staticmethod
    def _format_result(member: discord.Member, analysis: dict) -> str:
        """Separated from the command body for the same reason as
        _format_error - pure function, testable without discord.py's
        interaction/gateway machinery. Takes the already-invoked analysis
        result (moderation_intelligence.report.analyze's response), not
        the raw create response - the create call only returns the report
        shell, analysis is what has anything worth showing the reporter."""
        status = (
            "⚠️ Escalated to staff for review."
            if analysis.get("escalated")
            else f"Recommended action: **{analysis.get('recommended_action', 'none')}**"
        )
        return (
            f"Report submitted for {member.mention}. {status}\n"
            f"Risk: {analysis.get('risk_score', 0):.2f} | Confidence: {analysis.get('confidence', 0):.0%}"
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationReportCog(bot))
