"""
services/operational_intelligence/metrics.py — Records periodic snapshots
from PluginHeartbeat into ServerMetricSnapshot (the time-series history
that doesn't otherwise exist - see models/server_metrics.py's module
docstring), and the query helpers predictive crash prevention / NL ops
queries read from.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.plugin_heartbeat import PluginHeartbeat
from models.server_metrics import ServerMetricSnapshot


async def sample_all_servers(db: AsyncSession) -> int:
    """
    Snapshots every currently-known PluginHeartbeat row. Returns the
    number of snapshots recorded. Intended to be called periodically by
    a background loop (services/operational_intelligence/sampler_loop.py),
    the same pattern as services/scheduler_loop.py.
    """
    result = await db.execute(select(PluginHeartbeat))
    heartbeats = list(result.scalars().all())

    for hb in heartbeats:
        db.add(ServerMetricSnapshot(server_id=hb.server_id, tps=hb.tps, online_count=hb.online_count))

    await db.flush()
    return len(heartbeats)


async def recent_snapshots(
    db: AsyncSession, server_id: str, *, since: dt.datetime, limit: int = 500
) -> list[ServerMetricSnapshot]:
    stmt = (
        select(ServerMetricSnapshot)
        .where(ServerMetricSnapshot.server_id == server_id, ServerMetricSnapshot.recorded_at >= since)
        .order_by(ServerMetricSnapshot.recorded_at.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def purge_old_snapshots(db: AsyncSession) -> int:
    """Sweeps snapshots older than settings.server_metric_retention_hours.
    Safe to call periodically - an unbounded history for every server,
    sampled every server_metric_sample_interval_seconds, would otherwise
    grow forever."""
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=get_settings().server_metric_retention_hours)
    stmt = delete(ServerMetricSnapshot).where(ServerMetricSnapshot.recorded_at < cutoff)
    result = await db.execute(stmt)
    return result.rowcount
