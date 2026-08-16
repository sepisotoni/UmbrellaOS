"""
services/investigation/tools.py — Ported from Moo-assistant's
bot/investigation/tools.py.

Adaptations from the source:
- InvestigationContext drops `guild` (single-tenant, see models/investigation.py),
  `requester` and `question` (none of the five tools below actually read
  either - confirmed by checking the source, not assumed) - down to just
  `target_user_id`.
- InvestigationTool.run() takes `db: AsyncSession` directly rather than
  opening its own session, matching every other service in this codebase.
- RecentAnnouncementsTool is NOT ported here - it depends on
  KnowledgeRetriever, which needs the knowledge-channel-indexing pipeline
  (a separate, much larger piece of the knowledge domain not yet built).
  It belongs alongside that work, not stubbed speculatively now.
- PunishmentHistoryTool queries models.moderation_intelligence.ModerationAction,
  already ported for the moderation_intelligence domain - no new dependency.
- LinkedAccountTool queries models.discord.DiscordAccount (umbrella-core's
  pre-existing account link table), not a separate LinkedAccount model.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.moderation_intelligence import ModerationAction
from models.player import Player
from services.investigation.repository import InvestigationRepository
from services.knowledge.service import KnowledgeService


@dataclass(frozen=True)
class InvestigationContext:
    target_user_id: str | None
    question: str = ""


@dataclass(frozen=True)
class ToolFinding:
    tool_key: str
    finding_text: str
    confidence: float


class InvestigationTool(ABC):
    """A single, pluggable, read-only diagnostic. Each one is also
    registered as its own capability (see capabilities/investigation.py) -
    this class exists so investigation.run (the aggregator) can loop over
    all of them uniformly, not as a separate plugin mechanism of its own."""

    key: str = "base"

    @abstractmethod
    async def run(self, db: AsyncSession, context: InvestigationContext) -> ToolFinding:
        raise NotImplementedError


class WhitelistStatusTool(InvestigationTool):
    key = "whitelist_status"

    async def run(self, db: AsyncSession, context: InvestigationContext) -> ToolFinding:
        if context.target_user_id is None:
            return ToolFinding(self.key, "No target user was specified to check whitelist status for.", 0.2)
        entry = await InvestigationRepository.whitelist_entry(db, discord_user_id=context.target_user_id)
        if entry is None:
            return ToolFinding(self.key, "No whitelist record found for this user.", 0.5)
        return ToolFinding(
            self.key, f"Whitelist status for '{entry.ingame_username}': {entry.status.value}.", 0.9
        )


class KnownIssuesTool(InvestigationTool):
    """Surfaces open known issues (e.g. maintenance, outages) staff have logged."""

    key = "known_issues"

    async def run(self, db: AsyncSession, context: InvestigationContext) -> ToolFinding:
        issues = await InvestigationRepository.known_issues(db, only_open=True)
        if not issues:
            return ToolFinding(self.key, "No open known issues are logged for this server right now.", 0.7)
        lines = "; ".join(f"{i.title}: {i.description}" for i in issues[:5])
        return ToolFinding(self.key, f"Open known issues: {lines}", 0.85)


class PunishmentHistoryTool(InvestigationTool):
    """Looks up moderation_actions history for the target user."""

    key = "punishment_history"

    async def run(self, db: AsyncSession, context: InvestigationContext) -> ToolFinding:
        if context.target_user_id is None:
            return ToolFinding(self.key, "No target user was specified to check punishment history for.", 0.2)

        stmt = (
            select(ModerationAction)
            .where(ModerationAction.user_id == context.target_user_id)
            .order_by(ModerationAction.created_at.desc())
            .limit(5)
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())

        if not rows:
            return ToolFinding(self.key, "No moderation actions on record for this user.", 0.6)

        lines = "; ".join(
            f"{r.action_type.value} on {r.created_at:%Y-%m-%d} ({r.reason or 'no reason given'})" for r in rows
        )
        return ToolFinding(self.key, f"Recent moderation history: {lines}", 0.9)


class LinkedAccountTool(InvestigationTool):
    key = "linked_account"

    async def run(self, db: AsyncSession, context: InvestigationContext) -> ToolFinding:
        if context.target_user_id is None:
            return ToolFinding(self.key, "No target user was specified to check account linking for.", 0.2)
        link = await InvestigationRepository.linked_account(db, context.target_user_id)
        if link is None or link.player_uuid is None:
            return ToolFinding(self.key, "This Discord account is not linked to a verified in-game account.", 0.7)

        player = await db.get(Player, link.player_uuid)
        username = player.username if player is not None else link.player_uuid
        return ToolFinding(self.key, f"Linked in-game username: {username}.", 0.9)


class MaintenanceStatusTool(InvestigationTool):
    """A known-issue-backed maintenance check (no external server-status API
    in this skeleton, same as the source - wire a real integration in here
    when one is available)."""

    key = "maintenance_status"

    async def run(self, db: AsyncSession, context: InvestigationContext) -> ToolFinding:
        issues = await InvestigationRepository.known_issues(db, only_open=True)
        maintenance_terms = ("maintenance", "outage", "downtime", "restart")
        hits = [
            i for i in issues
            if any(term in i.title.lower() or term in i.description.lower() for term in maintenance_terms)
        ]
        if not hits:
            return ToolFinding(self.key, "No active maintenance or outage is currently logged.", 0.6)
        lines = "; ".join(f"{i.title}: {i.description}" for i in hits)
        return ToolFinding(self.key, f"Active maintenance/outage: {lines}", 0.9)


class RecentAnnouncementsTool(InvestigationTool):
    """
    Searches the knowledge base (services/knowledge/service.py) for
    content relevant to the investigation's question. Was deferred when
    the investigation domain was first ported - it depends on the
    knowledge retriever, which didn't exist yet. Built now that
    services/knowledge/service.py's search() is real.
    """

    key = "recent_announcements"

    async def run(self, db: AsyncSession, context: InvestigationContext) -> ToolFinding:
        entries = await KnowledgeService.search(db, context.question, limit=3)
        if not entries:
            return ToolFinding(self.key, "No relevant knowledge base entries found.", 0.4)
        lines = "; ".join(e.content for e in entries)
        return ToolFinding(self.key, f"Relevant knowledge base entries: {lines}", 0.8)


ALL_TOOLS: list[InvestigationTool] = [
    WhitelistStatusTool(),
    KnownIssuesTool(),
    PunishmentHistoryTool(),
    LinkedAccountTool(),
    MaintenanceStatusTool(),
    RecentAnnouncementsTool(),
]
