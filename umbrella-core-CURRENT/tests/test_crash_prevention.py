"""
tests/test_crash_prevention.py — Tests for
services/operational_intelligence/crash_prevention.py.
"""
import datetime as dt

import pytest

from config import get_settings
from models.server_metrics import ServerMetricSnapshot
from services.operational_intelligence.crash_prevention import CrashRiskLevel, assess_crash_risk


async def _add_snapshots(db, server_id: str, tps_values: list[float]):
    now = dt.datetime.now(dt.timezone.utc)
    for i, tps in enumerate(tps_values):
        # oldest first, spaced one minute apart, all within the lookback window
        recorded_at = now - dt.timedelta(minutes=(len(tps_values) - i))
        db.add(ServerMetricSnapshot(server_id=server_id, tps=tps, online_count=5, recorded_at=recorded_at))
    await db.flush()


@pytest.mark.asyncio
async def test_insufficient_data_below_min_samples(db_session):
    async with db_session() as db:
        await _add_snapshots(db, "srv-1", [20.0])
        result = await assess_crash_risk(db, "srv-1")
        assert result.risk_level == CrashRiskLevel.INSUFFICIENT_DATA


@pytest.mark.asyncio
async def test_no_risk_for_stable_healthy_tps(db_session):
    async with db_session() as db:
        await _add_snapshots(db, "srv-2", [20.0, 19.8, 20.0, 19.9, 20.0])
        result = await assess_crash_risk(db, "srv-2")
        assert result.risk_level == CrashRiskLevel.NONE


@pytest.mark.asyncio
async def test_critical_when_current_tps_below_critical_threshold(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "crash_prevention_critical_tps", 10.0)
    async with db_session() as db:
        await _add_snapshots(db, "srv-3", [19.0, 15.0, 12.0, 8.0, 5.0])
        result = await assess_crash_risk(db, "srv-3")
        assert result.risk_level == CrashRiskLevel.CRITICAL
        assert result.current_tps == 5.0


@pytest.mark.asyncio
async def test_watch_when_trending_down_and_below_watch_threshold(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "crash_prevention_watch_tps", 18.0)
    monkeypatch.setattr(get_settings(), "crash_prevention_critical_tps", 10.0)
    monkeypatch.setattr(get_settings(), "crash_prevention_trend_drop_threshold", 2.0)
    async with db_session() as db:
        # first half avg ~20, second half avg ~16 -> trending down by ~4, current 15 < watch(18)
        await _add_snapshots(db, "srv-4", [20.0, 20.0, 17.0, 16.0, 15.0])
        result = await assess_crash_risk(db, "srv-4")
        assert result.risk_level == CrashRiskLevel.WATCH


@pytest.mark.asyncio
async def test_no_watch_if_trending_down_but_still_above_watch_threshold(db_session, monkeypatch):
    """A mild dip that's still comfortably above the watch threshold
    shouldn't alarm anyone - trending down alone isn't sufficient."""
    monkeypatch.setattr(get_settings(), "crash_prevention_watch_tps", 15.0)
    monkeypatch.setattr(get_settings(), "crash_prevention_trend_drop_threshold", 1.0)
    async with db_session() as db:
        await _add_snapshots(db, "srv-5", [20.0, 20.0, 19.0, 18.5, 18.0])
        result = await assess_crash_risk(db, "srv-5")
        assert result.risk_level == CrashRiskLevel.NONE


@pytest.mark.asyncio
async def test_reasoning_is_human_readable(db_session):
    async with db_session() as db:
        await _add_snapshots(db, "srv-6", [1])
        result = await assess_crash_risk(db, "srv-6")
        assert "sample" in result.reasoning.lower()
