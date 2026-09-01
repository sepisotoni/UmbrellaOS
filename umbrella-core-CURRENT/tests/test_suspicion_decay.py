"""
tests/test_suspicion_decay.py — Tests for
services/alt_detection_service.py::decay_stale_suspicion_scores (and its
capability wrapper,
capabilities/alt_detection_maintenance.py::decay_stale).
"""
import datetime as dt
import uuid as uuid_lib

import pytest

from config import get_settings
from models import Player, SuspicionEvent
from services.alt_detection_service import decay_stale_suspicion_scores


def _make_player(suspicion_score: int) -> Player:
    return Player(
        uuid=str(uuid_lib.uuid4()),
        username=f"player_{uuid_lib.uuid4().hex[:8]}",
        suspicion_score=suspicion_score,
    )


@pytest.mark.asyncio
async def test_decay_reduces_score_for_player_with_no_recent_trigger(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "suspicion_score_decay_points", 10)
    monkeypatch.setattr(get_settings(), "suspicion_score_decay_after_days", 30)
    async with db_session() as db:
        stale_player = _make_player(suspicion_score=50)
        db.add(stale_player)
        old_event = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=60)
        db.add(SuspicionEvent(
            player_uuid=stale_player.uuid, trigger="alt_ip_match",
            points=50, created_at=old_event,
        ))
        await db.flush()

        decayed_count = await decay_stale_suspicion_scores(db)
        assert decayed_count == 1

        await db.refresh(stale_player)
        assert stale_player.suspicion_score == 40


@pytest.mark.asyncio
async def test_decay_exempts_player_with_recent_trigger(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "suspicion_score_decay_points", 10)
    monkeypatch.setattr(get_settings(), "suspicion_score_decay_after_days", 30)
    async with db_session() as db:
        active_player = _make_player(suspicion_score=50)
        db.add(active_player)
        recent_event = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
        db.add(SuspicionEvent(
            player_uuid=active_player.uuid, trigger="alt_ip_match",
            points=50, created_at=recent_event,
        ))
        await db.flush()

        decayed_count = await decay_stale_suspicion_scores(db)
        assert decayed_count == 0

        await db.refresh(active_player)
        assert active_player.suspicion_score == 50


@pytest.mark.asyncio
async def test_decay_floors_at_zero_rather_than_going_negative(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "suspicion_score_decay_points", 100)
    monkeypatch.setattr(get_settings(), "suspicion_score_decay_after_days", 30)
    async with db_session() as db:
        low_score_player = _make_player(suspicion_score=5)
        db.add(low_score_player)
        await db.flush()

        decayed_count = await decay_stale_suspicion_scores(db)
        assert decayed_count == 1

        await db.refresh(low_score_player)
        assert low_score_player.suspicion_score == 0


@pytest.mark.asyncio
async def test_decay_skips_players_already_at_zero(db_session):
    async with db_session() as db:
        clean_player = _make_player(suspicion_score=0)
        db.add(clean_player)
        await db.flush()

        decayed_count = await decay_stale_suspicion_scores(db)
        assert decayed_count == 0


@pytest.mark.asyncio
async def test_decay_with_no_players_is_a_safe_noop(db_session):
    async with db_session() as db:
        decayed_count = await decay_stale_suspicion_scores(db)
        assert decayed_count == 0
