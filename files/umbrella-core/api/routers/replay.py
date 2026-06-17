"""
api/routers/replay.py — Replay endpoints.

POST /api/v1/replay/sessions
GET  /api/v1/replay/sessions
GET  /api/v1/replay/sessions/{replay_id}
POST /api/v1/replay/sessions/{replay_id}/events
POST /api/v1/replay/sessions/{replay_id}/finalize
GET  /api/v1/replay/sessions/{replay_id}/events
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from api.middleware.auth import require_admin_key
from services import replay_service

router = APIRouter(prefix="/api/v1/replay", tags=["replay"])


class CreateReplayRequest(BaseModel):
    trigger: str
    triggered_by: str
    minecraft_uuid: str
    incident_at: str
    started_at: str | None = None
    notes: str | None = None


class IngestEventsRequest(BaseModel):
    events: list[dict]


@router.post("/sessions", status_code=201)
async def create_replay_session(
    body: CreateReplayRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Create a new replay session.
    started_at defaults to incident_at minus 5 minutes if not provided.
    """
    incident_at = datetime.fromisoformat(body.incident_at.replace("Z", "+00:00"))
    started_at = None
    if body.started_at:
        started_at = datetime.fromisoformat(body.started_at.replace("Z", "+00:00"))

    session = await replay_service.create_replay(
        db,
        body.trigger,
        body.triggered_by,
        body.minecraft_uuid,
        incident_at,
        started_at=started_at,
        notes=body.notes,
    )

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


@router.get("/sessions")
async def list_replay_sessions(
    minecraft_uuid: str | None = None,
    trigger: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    List replay sessions, newest first.
    Supports optional filtering by minecraft_uuid and trigger.
    """
    sessions = await replay_service.list_replays(
        db,
        minecraft_uuid=minecraft_uuid,
        trigger=trigger,
        limit=limit,
        offset=offset,
    )
    return sessions


@router.get("/sessions/{replay_id}")
async def get_replay_session(
    replay_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Get a replay session by ID.
    Returns 404 if not found.
    """
    session = await replay_service.get_replay(db, replay_id)
    if not session:
        raise HTTPException(status_code=404, detail="Replay session not found")
    return session


@router.post("/sessions/{replay_id}/events")
async def ingest_replay_events(
    replay_id: str,
    body: IngestEventsRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Ingest events into a replay session.
    Returns count of events inserted.
    """
    inserted = await replay_service.ingest_events(db, replay_id, body.events)
    return {"inserted": inserted}


@router.post("/sessions/{replay_id}/finalize")
async def finalize_replay_session(
    replay_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Finalize a replay session by setting ended_at.
    Returns 404 if session not found.
    """
    session = await replay_service.finalize_replay(db, replay_id)
    if not session:
        raise HTTPException(status_code=404, detail="Replay session not found")

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


@router.get("/sessions/{replay_id}/events")
async def get_replay_session_events(
    replay_id: str,
    event_type: str | None = None,
    minecraft_uuid: str | None = None,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Get events for a replay session, ordered by timestamp ASC.
    Supports optional filtering by event_type and minecraft_uuid.
    """
    events = await replay_service.get_replay_events(
        db,
        replay_id,
        event_type=event_type,
        minecraft_uuid=minecraft_uuid,
        limit=limit,
        offset=offset,
    )
    return events
