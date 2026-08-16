"""
tests/test_investigation.py — Tests for services/investigation/*.py at the
service/tool layer (not through REST - see
tests/registry/test_capabilities_investigation.py for the capability/RBAC
layer).
"""
from datetime import datetime, timezone

import pytest

from models.discord import DiscordAccount
from models.investigation import Investigation
from models.knowledge import KnownIssue, WhitelistEntry, WhitelistStatus
from models.moderation_intelligence import ModerationAction, ModerationActionType
from models.player import Player
from services.investigation.repository import InvestigationRepository
from services.investigation.service import run_investigation
from services.investigation.tools import (
    InvestigationContext,
    KnownIssuesTool,
    LinkedAccountTool,
    MaintenanceStatusTool,
    PunishmentHistoryTool,
    WhitelistStatusTool,
)


@pytest.mark.asyncio
async def test_whitelist_status_tool_reports_no_target(db_session):
    async with db_session() as db:
        finding = await WhitelistStatusTool().run(db, InvestigationContext(target_user_id=None))
        assert "No target user" in finding.finding_text
        assert finding.confidence < 0.5


@pytest.mark.asyncio
async def test_whitelist_status_tool_reports_no_record(db_session):
    async with db_session() as db:
        finding = await WhitelistStatusTool().run(db, InvestigationContext(target_user_id="user-nowhere"))
        assert "No whitelist record" in finding.finding_text


@pytest.mark.asyncio
async def test_whitelist_status_tool_reports_status(db_session):
    async with db_session() as db:
        db.add(WhitelistEntry(ingame_username="Steve", discord_user_id="user-1", status=WhitelistStatus.APPROVED))
        await db.flush()

        finding = await WhitelistStatusTool().run(db, InvestigationContext(target_user_id="user-1"))
        assert "Steve" in finding.finding_text
        assert "approved" in finding.finding_text


@pytest.mark.asyncio
async def test_known_issues_tool_reports_open_issues_only(db_session):
    async with db_session() as db:
        db.add(KnownIssue(title="EU outage", description="EU nodes down", is_resolved=False, created_by="staff-1"))
        db.add(KnownIssue(title="Old fixed issue", description="was fixed", is_resolved=True, created_by="staff-1"))
        await db.flush()

        finding = await KnownIssuesTool().run(db, InvestigationContext(target_user_id=None))
        assert "EU outage" in finding.finding_text
        assert "Old fixed issue" not in finding.finding_text


@pytest.mark.asyncio
async def test_maintenance_status_tool_matches_maintenance_terms(db_session):
    async with db_session() as db:
        db.add(KnownIssue(title="Scheduled maintenance", description="Restarting at 3am", is_resolved=False, created_by="staff-1"))
        db.add(KnownIssue(title="Chat bug", description="Emoji rendering wrong", is_resolved=False, created_by="staff-1"))
        await db.flush()

        finding = await MaintenanceStatusTool().run(db, InvestigationContext(target_user_id=None))
        assert "Scheduled maintenance" in finding.finding_text
        assert "Chat bug" not in finding.finding_text


@pytest.mark.asyncio
async def test_punishment_history_tool_reports_recent_actions(db_session):
    async with db_session() as db:
        db.add(
            ModerationAction(
                user_id="user-2", moderator_id="staff-1", action_type=ModerationActionType.WARN,
                reason="spam", created_at=datetime.now(timezone.utc),
            )
        )
        await db.flush()

        finding = await PunishmentHistoryTool().run(db, InvestigationContext(target_user_id="user-2"))
        assert "warn" in finding.finding_text
        assert "spam" in finding.finding_text


@pytest.mark.asyncio
async def test_linked_account_tool_uses_existing_discord_account_table(db_session):
    """Confirms LinkedAccountTool queries models.discord.DiscordAccount,
    not a separate table - the whole point of not porting Moo's
    LinkedAccount model."""
    async with db_session() as db:
        db.add(Player(uuid="11111111-1111-1111-1111-111111111111", username="Alexei"))
        db.add(DiscordAccount(discord_id="user-3", player_uuid="11111111-1111-1111-1111-111111111111", verified=True))
        await db.flush()

        finding = await LinkedAccountTool().run(db, InvestigationContext(target_user_id="user-3"))
        assert "Alexei" in finding.finding_text


@pytest.mark.asyncio
async def test_linked_account_tool_ignores_unverified_links(db_session):
    async with db_session() as db:
        db.add(Player(uuid="22222222-2222-2222-2222-222222222222", username="Unverified"))
        db.add(DiscordAccount(discord_id="user-4", player_uuid="22222222-2222-2222-2222-222222222222", verified=False))
        await db.flush()

        finding = await LinkedAccountTool().run(db, InvestigationContext(target_user_id="user-4"))
        assert "not linked" in finding.finding_text


@pytest.mark.asyncio
async def test_recent_announcements_tool_searches_knowledge_base(db_session, monkeypatch):
    """Closes the loop on the tool deferred when the investigation domain
    was first ported - now that services/knowledge/service.py exists."""
    from config import get_settings
    from services.investigation.tools import RecentAnnouncementsTool
    from services.knowledge.service import KnowledgeService

    monkeypatch.setattr(get_settings(), "knowledge_channel_names", "ai-faq")
    async with db_session() as db:
        await KnowledgeService.index_entry(
            db, channel_id="chan-1", channel_name="ai-faq", discord_message_id="msg-ra1",
            author_id="user-1", author_name="Alice", content="The store restocks every Friday",
        )
        await db.flush()

        finding = await RecentAnnouncementsTool().run(
            db, InvestigationContext(target_user_id=None, question="store")
        )
        assert "Friday" in finding.finding_text


@pytest.mark.asyncio
async def test_run_investigation_aggregates_every_tool(db_session):
    async with db_session() as db:
        result = await run_investigation(
            db, requested_by="staff-1", target_user_id="user-5", question="Why can't they join?"
        )
        await db.commit()

        assert len(result["findings"]) == 6  # every ported tool ran, including recent_announcements now
        assert result["investigation_id"]

        investigation = await db.get(Investigation, result["investigation_id"])
        assert investigation.question == "Why can't they join?"


@pytest.mark.asyncio
async def test_run_investigation_persists_one_finding_per_tool(db_session):
    async with db_session() as db:
        result = await run_investigation(db, requested_by="staff-1", target_user_id=None, question="test")
        await db.commit()

        stmt_result = await InvestigationRepository.recent(db, limit=1)
        assert len(stmt_result) == 1
        assert stmt_result[0].id == result["investigation_id"]
