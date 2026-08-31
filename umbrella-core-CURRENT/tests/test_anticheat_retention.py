"""
tests/test_anticheat_retention.py — Tests for
services/anticheat_service.py::purge_old_violations (and its capability
wrapper, capabilities/anticheat_maintenance.py::purge_old).
"""
import datetime as dt

import pytest

from config import get_settings
from models.anticheat_violation import AnticheatViolation
from services.anticheat_service import purge_old_violations


@pytest.mark.asyncio
async def test_purge_old_violations_removes_only_expired(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "anticheat_violation_retention_days", 1)
    async with db_session() as db:
        old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)
        recent = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        db.add(AnticheatViolation(
            player_uuid=None, player_name="OldOffender", check_name="Fly",
            verbose="test", vl=5, timestamp=old,
        ))
        db.add(AnticheatViolation(
            player_uuid=None, player_name="RecentOffender", check_name="Speed",
            verbose="test", vl=3, timestamp=recent,
        ))
        await db.flush()

        removed = await purge_old_violations(db)
        assert removed == 1

        from sqlalchemy import select
        result = await db.execute(select(AnticheatViolation))
        remaining = list(result.scalars().all())
        assert len(remaining) == 1
        assert remaining[0].player_name == "RecentOffender"


@pytest.mark.asyncio
async def test_purge_old_violations_with_nothing_expired_removes_nothing(db_session):
    async with db_session() as db:
        recent = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        db.add(AnticheatViolation(
            player_uuid=None, player_name="RecentOffender", check_name="Speed",
            verbose="test", vl=3, timestamp=recent,
        ))
        await db.flush()

        removed = await purge_old_violations(db)
        assert removed == 0


@pytest.mark.asyncio
async def test_purge_old_violations_with_no_rows_is_a_safe_noop(db_session):
    async with db_session() as db:
        removed = await purge_old_violations(db)
        assert removed == 0
