"""
services/replay_service.py — Replay system service.

Methods for managing replay sessions and events.
"""
import json
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from models import ReplaySession, ReplayEvent, AuditLog
from models.player import Player


VALID_EVENT_TYPES = {"movement", "inventory", "combat", "command", "damage", "block"}


async def create_replay(
    db: AsyncSession,
    trigger: str,
    triggered_by: str,
    minecraft_uuid: str,
    incident_at: datetime,
    started_at: datetime | None = None,
    notes: str | None = None,
) -> ReplaySession:
    """
    Create a new replay session.
    started_at defaults to incident_at minus 5 minutes if not provided.
    Writes an audit log entry.
    """
    if started_at is None:
        started_at = incident_at - timedelta(minutes=5)

    session = ReplaySession(
        trigger=trigger,
        triggered_by=triggered_by,
        minecraft_uuid=minecraft_uuid,
        started_at=started_at,
        incident_at=incident_at,
        notes=notes,
    )
    db.add(session)
    await db.flush()

    # Write audit log
    actor_type = "system" if triggered_by == "system" else "staff"
    audit = AuditLog(
        action="replay.created",
        actor=triggered_by,
        actor_type=actor_type,
        target=minecraft_uuid,
        details_json=json.dumps({"trigger": trigger, "replay_id": session.id}),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(session)

    return session


async def ingest_events(
    db: AsyncSession,
    replay_id: str,
    events: list[dict],
) -> int:
    """
    Ingest events into a replay session.
    Validates event_type and bulk-inserts valid events.
    Updates ReplaySession.event_count.
    Returns count of events inserted.
    """
    valid_events = []
    for event in events:
        event_type = event.get("event_type")
        if event_type not in VALID_EVENT_TYPES:
            continue

        timestamp = event.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        valid_events.append(
            ReplayEvent(
                replay_id=replay_id,
                minecraft_uuid=event["minecraft_uuid"],
                event_type=event_type,
                event_data_json=event["event_data_json"],
                timestamp=timestamp,
                world=event.get("world"),
            )
        )

    if not valid_events:
        return 0

    db.add_all(valid_events)

    # Update event_count
    await db.execute(
        update(ReplaySession)
        .where(ReplaySession.id == replay_id)
        .values(event_count=ReplaySession.event_count + len(valid_events))
    )

    await db.commit()
    return len(valid_events)


async def finalize_replay(
    db: AsyncSession,
    replay_id: str,
) -> ReplaySession | None:
    """
    Finalize a replay session by setting ended_at.
    Returns the updated session, or None if not found.
    """
    result = await db.execute(
        update(ReplaySession)
        .where(ReplaySession.id == replay_id)
        .values(ended_at=datetime.utcnow())
        .returning(ReplaySession)
    )
    row = result.scalar_one_or_none()
    if row:
        await db.commit()
        await db.refresh(row)
    return row


async def get_replay(
    db: AsyncSession,
    replay_id: str,
) -> dict | None:
    """
    Get a replay session as a dict.
    Returns None if not found.
    """
    result = await db.execute(
        select(ReplaySession).where(ReplaySession.id == replay_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        return None

    return {
        "id": session.id,
        "trigger": session.trigger,
        "triggered_by": session.triggered_by,
        "minecraft_uuid": session.minecraft_uuid,
        "started_at": session.started_at.isoformat(),
        "incident_at": session.incident_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "event_count": session.event_count,
        "created_at": session.created_at.isoformat(),
        "notes": session.notes,
    }


async def get_replay_events(
    db: AsyncSession,
    replay_id: str,
    event_type: str | None = None,
    minecraft_uuid: str | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> list[dict]:
    """
    Get events for a replay session, ordered by timestamp ASC.
    Supports optional filtering by event_type and minecraft_uuid.
    Paginated with limit/offset.
    """
    query = select(ReplayEvent).where(ReplayEvent.replay_id == replay_id)

    if event_type:
        query = query.where(ReplayEvent.event_type == event_type)
    if minecraft_uuid:
        query = query.where(ReplayEvent.minecraft_uuid == minecraft_uuid)

    query = query.order_by(ReplayEvent.timestamp.asc()).limit(limit).offset(offset)

    result = await db.execute(query)
    events = result.scalars().all()

    return [
        {
            "id": event.id,
            "replay_id": event.replay_id,
            "minecraft_uuid": event.minecraft_uuid,
            "event_type": event.event_type,
            "event_data_json": event.event_data_json,
            "timestamp": event.timestamp.isoformat(),
            "world": event.world,
        }
        for event in events
    ]


async def list_replays(
    db: AsyncSession,
    minecraft_uuid: str | None = None,
    trigger: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """
    List replay sessions, newest first.
    Supports optional filtering by minecraft_uuid and trigger.
    Paginated with limit/offset.
    """
    query = select(ReplaySession)

    if minecraft_uuid:
        query = query.where(ReplaySession.minecraft_uuid == minecraft_uuid)
    if trigger:
        query = query.where(ReplaySession.trigger == trigger)

    query = query.order_by(ReplaySession.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    sessions = result.scalars().all()

    return [
        {
            "id": session.id,
            "trigger": session.trigger,
            "triggered_by": session.triggered_by,
            "minecraft_uuid": session.minecraft_uuid,
            "started_at": session.started_at.isoformat(),
            "incident_at": session.incident_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "event_count": session.event_count,
            "created_at": session.created_at.isoformat(),
            "notes": session.notes,
        }
        for session in sessions
    ]
