"""
tests/test_operational_intelligence_metrics.py — Tests for
services/operational_intelligence/metrics.py.
"""
import datetime as dt

import pytest

from config import get_settings
from models.plugin_heartbeat import PluginHeartbeat
from models.server_metrics import ServerMetricSnapshot
from services.operational_intelligence.metrics import purge_old_snapshots, recent_snapshots, sample_all_servers


@pytest.mark.asyncio
async def test_sample_all_servers_snapshots_every_heartbeat(db_session):
    async with db_session() as db:
        db.add(PluginHeartbeat(server_id="srv-1", tps=19.8, online_count=5))
        db.add(PluginHeartbeat(server_id="srv-2", tps=15.2, online_count=12))
        await db.flush()

        count = await sample_all_servers(db)
        assert count == 2

        snaps = await recent_snapshots(db, "srv-1", since=dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1))
        assert len(snaps) == 1
        assert snaps[0].tps == 19.8
        assert snaps[0].online_count == 5


@pytest.mark.asyncio
async def test_sample_all_servers_with_no_heartbeats_records_nothing(db_session):
    async with db_session() as db:
        count = await sample_all_servers(db)
        assert count == 0


@pytest.mark.asyncio
async def test_recent_snapshots_excludes_older_than_since(db_session):
    async with db_session() as db:
        old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)
        recent = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)
        db.add(ServerMetricSnapshot(server_id="srv-3", tps=20.0, online_count=1, recorded_at=old))
        db.add(ServerMetricSnapshot(server_id="srv-3", tps=18.0, online_count=2, recorded_at=recent))
        await db.flush()

        since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        snaps = await recent_snapshots(db, "srv-3", since=since)
        assert len(snaps) == 1
        assert snaps[0].tps == 18.0


@pytest.mark.asyncio
async def test_recent_snapshots_orders_oldest_first(db_session):
    async with db_session() as db:
        t1 = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=10)
        t2 = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=5)
        db.add(ServerMetricSnapshot(server_id="srv-4", tps=15.0, online_count=1, recorded_at=t2))
        db.add(ServerMetricSnapshot(server_id="srv-4", tps=20.0, online_count=1, recorded_at=t1))
        await db.flush()

        snaps = await recent_snapshots(db, "srv-4", since=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1))
        assert [s.tps for s in snaps] == [20.0, 15.0]  # oldest first


@pytest.mark.asyncio
async def test_purge_old_snapshots_removes_only_expired(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "server_metric_retention_hours", 1)
    async with db_session() as db:
        old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)
        recent = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)
        db.add(ServerMetricSnapshot(server_id="srv-5", tps=20.0, online_count=1, recorded_at=old))
        db.add(ServerMetricSnapshot(server_id="srv-5", tps=18.0, online_count=1, recorded_at=recent))
        await db.flush()

        removed = await purge_old_snapshots(db)
        assert removed == 1

        remaining = await recent_snapshots(db, "srv-5", since=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3))
        assert len(remaining) == 1
        assert remaining[0].tps == 18.0
