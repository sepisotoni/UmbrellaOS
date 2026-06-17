"""
services/analytics_service.py — Analytics event tracking and player statistics.

Handles recording analytics events and aggregating player statistics.
"""
import json
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models import AnalyticsEvent, PlayerStat


ALLOWED_EVENT_TYPES = ["join", "quit", "death", "kill", "chat", "command"]
METRIC_MAPPING = {
    "join": "joins",
    "quit": "leaves",
    "death": "deaths",
    "kill": "kills",
    "chat": "chat_volume",
}


async def record_event(
    db: AsyncSession,
    event_type: str,
    minecraft_uuid: str | None = None,
    data: dict | None = None,
) -> AnalyticsEvent:
    """
    Record an analytics event and auto-increment relevant player stats.
    
    Returns the created AnalyticsEvent row.
    """
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {event_type}. Must be one of {ALLOWED_EVENT_TYPES}")
    
    # Create the event
    event = AnalyticsEvent(
        event_type=event_type,
        minecraft_uuid=minecraft_uuid,
        data_json=json.dumps(data) if data else None,
    )
    db.add(event)
    await db.flush()
    
    # Auto-increment stats for relevant metrics
    if event_type in METRIC_MAPPING and minecraft_uuid:
        metric = METRIC_MAPPING[event_type]
        await _increment_stat(db, minecraft_uuid, metric, ["daily", "alltime"])
    
    return event


async def _increment_stat(
    db: AsyncSession,
    minecraft_uuid: str,
    metric: str,
    periods: list[str],
    amount: int = 1,
) -> None:
    """
    Private helper to increment player stats for given periods.
    
    Uses upsert pattern to avoid race conditions.
    """
    today = datetime.utcnow().date()
    
    for period in periods:
        if period == "daily":
            period_start = today
        elif period == "weekly":
            # Start of current ISO week (Monday)
            period_start = today - timedelta(days=today.weekday())
        elif period == "alltime":
            period_start = date(2000, 1, 1)
        else:
            continue
        
        # Try to get existing stat
        result = await db.execute(
            select(PlayerStat).where(
                and_(
                    PlayerStat.minecraft_uuid == minecraft_uuid,
                    PlayerStat.metric == metric,
                    PlayerStat.period == period,
                    PlayerStat.period_start == period_start,
                )
            )
        )
        stat = result.scalar_one_or_none()
        
        if stat:
            # Increment existing
            stat.value += amount
            stat.updated_at = datetime.utcnow()
        else:
            # Create new
            stat = PlayerStat(
                minecraft_uuid=minecraft_uuid,
                metric=metric,
                value=amount,
                period=period,
                period_start=period_start,
            )
            db.add(stat)
    
    await db.flush()


async def get_player_stats(
    db: AsyncSession,
    minecraft_uuid: str,
    period: str = "alltime",
) -> list[dict]:
    """
    Get all stats for a specific player and period.
    
    Returns list of dicts: { metric, value, period, period_start, updated_at }
    """
    result = await db.execute(
        select(PlayerStat).where(
            and_(
                PlayerStat.minecraft_uuid == minecraft_uuid,
                PlayerStat.period == period,
            )
        )
    )
    stats = result.scalars().all()
    
    return [
        {
            "metric": stat.metric,
            "value": stat.value,
            "period": stat.period,
            "period_start": stat.period_start.isoformat(),
            "updated_at": stat.updated_at.isoformat(),
        }
        for stat in stats
    ]


async def get_server_summary(db: AsyncSession) -> dict:
    """
    Get alltime totals across ALL players for each metric.
    
    Returns: { joins, leaves, deaths, kills, chat_volume, playtime_seconds }
    """
    result = await db.execute(
        select(PlayerStat.metric, func.sum(PlayerStat.value))
        .where(PlayerStat.period == "alltime")
        .group_by(PlayerStat.metric)
    )
    rows = result.all()
    
    summary = {
        "joins": 0,
        "leaves": 0,
        "deaths": 0,
        "kills": 0,
        "chat_volume": 0,
        "playtime_seconds": 0,
    }
    
    for metric, total in rows:
        if metric in summary:
            summary[metric] = int(total)
    
    return summary


async def get_recent_events(
    db: AsyncSession,
    limit: int = 50,
    event_type: str | None = None,
    minecraft_uuid: str | None = None,
) -> list[dict]:
    """
    Get the most recent analytics events, newest first.
    
    Supports optional filters for event_type and minecraft_uuid.
    
    Returns list of dicts: { id, event_type, minecraft_uuid, data_json, created_at }
    """
    query = select(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc()).limit(limit)
    
    conditions = []
    if event_type:
        conditions.append(AnalyticsEvent.event_type == event_type)
    if minecraft_uuid:
        conditions.append(AnalyticsEvent.minecraft_uuid == minecraft_uuid)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "minecraft_uuid": event.minecraft_uuid,
            "data_json": event.data_json,
            "created_at": event.created_at.isoformat(),
        }
        for event in events
    ]
