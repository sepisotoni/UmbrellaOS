"""
tests/test_risk_score.py — Tests for services/player_risk/risk_score.py.
"""
import datetime as dt

import pytest

from config import get_settings
from models.alt_detection import AltGroup, AltGroupMember, SuspicionEvent
from models.discord import DiscordAccount
from models.investigation import Investigation
from models.moderation_intelligence import ModerationAction, ModerationActionType
from models.player import Player
from services.player_risk.risk_score import compute_risk_score


@pytest.mark.asyncio
async def test_no_signals_gives_zero_score(db_session):
    async with db_session() as db:
        result = await compute_risk_score(db, "no-signals-uuid")
        assert result.total_score == 0
        assert result.discord_id is None


@pytest.mark.asyncio
async def test_anticheat_points_contribute_to_score(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "risk_score_anticheat_points_cap", 100)
    async with db_session() as db:
        db.add(SuspicionEvent(player_uuid="uuid-1", trigger="fly_hack", points=40, false_positive=False))
        await db.flush()

        result = await compute_risk_score(db, "uuid-1")
        assert result.total_score == 40
        assert result.breakdown.anticheat_points == 40


@pytest.mark.asyncio
async def test_false_positive_suspicion_events_are_excluded(db_session):
    async with db_session() as db:
        db.add(SuspicionEvent(player_uuid="uuid-2", trigger="fly_hack", points=40, false_positive=True))
        await db.flush()

        result = await compute_risk_score(db, "uuid-2")
        assert result.total_score == 0


@pytest.mark.asyncio
async def test_anticheat_points_are_capped(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "risk_score_anticheat_points_cap", 50)
    async with db_session() as db:
        db.add(SuspicionEvent(player_uuid="uuid-3", trigger="fly_hack", points=200, false_positive=False))
        await db.flush()

        result = await compute_risk_score(db, "uuid-3")
        assert result.breakdown.anticheat_component == 50  # capped, not 200
        assert result.breakdown.anticheat_points == 200  # raw value still reported


@pytest.mark.asyncio
async def test_confirmed_alt_group_adds_penalty(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "risk_score_confirmed_alt_penalty", 30)
    async with db_session() as db:
        group = AltGroup(confirmed=True)
        db.add(group)
        await db.flush()
        db.add(AltGroupMember(group_id=group.id, player_uuid="uuid-4"))
        await db.flush()

        result = await compute_risk_score(db, "uuid-4")
        assert result.breakdown.confirmed_alt_group is True
        assert result.total_score == 30


@pytest.mark.asyncio
async def test_unconfirmed_alt_group_does_not_add_penalty(db_session):
    async with db_session() as db:
        group = AltGroup(confirmed=False)
        db.add(group)
        await db.flush()
        db.add(AltGroupMember(group_id=group.id, player_uuid="uuid-5"))
        await db.flush()

        result = await compute_risk_score(db, "uuid-5")
        assert result.breakdown.confirmed_alt_group is False
        assert result.total_score == 0


@pytest.mark.asyncio
async def test_moderation_and_investigation_signals_bridge_via_discord_account(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "risk_score_per_moderation_action", 5)
    monkeypatch.setattr(get_settings(), "risk_score_moderation_action_cap", 30)
    monkeypatch.setattr(get_settings(), "risk_score_per_investigation", 2)
    monkeypatch.setattr(get_settings(), "risk_score_investigation_cap", 10)

    async with db_session() as db:
        db.add(Player(uuid="uuid-6", username="Bridged"))
        db.add(DiscordAccount(discord_id="discord-6", player_uuid="uuid-6", verified=True))
        db.add(ModerationAction(user_id="discord-6", moderator_id="staff-1", action_type=ModerationActionType.WARN))
        db.add(Investigation(requested_by="staff-1", target_user_id="discord-6", question="q", summary="s", confidence=0.5))
        await db.flush()

        result = await compute_risk_score(db, "uuid-6")
        assert result.discord_id == "discord-6"
        assert result.breakdown.moderation_action_count == 1
        assert result.breakdown.investigation_count == 1
        assert result.total_score == 5 + 2


@pytest.mark.asyncio
async def test_unverified_discord_link_is_not_bridged(db_session):
    """An unverified link shouldn't pull in moderation/investigation
    signals - matches investigation.LinkedAccountTool's own verified-only
    rule."""
    async with db_session() as db:
        db.add(Player(uuid="uuid-7", username="Unverified"))
        db.add(DiscordAccount(discord_id="discord-7", player_uuid="uuid-7", verified=False))
        db.add(ModerationAction(user_id="discord-7", moderator_id="staff-1", action_type=ModerationActionType.WARN))
        await db.flush()

        result = await compute_risk_score(db, "uuid-7")
        assert result.discord_id is None
        assert result.breakdown.moderation_action_count == 0


@pytest.mark.asyncio
async def test_missing_discord_link_is_not_itself_a_risk_signal(db_session):
    async with db_session() as db:
        result = await compute_risk_score(db, "uuid-8")
        assert "not itself a risk signal" in result.reasoning


@pytest.mark.asyncio
async def test_total_score_is_capped_at_100(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "risk_score_anticheat_points_cap", 100)
    monkeypatch.setattr(get_settings(), "risk_score_confirmed_alt_penalty", 30)
    async with db_session() as db:
        db.add(SuspicionEvent(player_uuid="uuid-9", trigger="x", points=100, false_positive=False))
        group = AltGroup(confirmed=True)
        db.add(group)
        await db.flush()
        db.add(AltGroupMember(group_id=group.id, player_uuid="uuid-9"))
        await db.flush()

        result = await compute_risk_score(db, "uuid-9")
        assert result.total_score == 100  # 100 + 30 capped down to 100
