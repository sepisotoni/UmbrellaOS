"""
api/routers/snapshot.py — Snapshot endpoints.

POST /api/v1/snapshots
GET  /api/v1/snapshots/players/{minecraft_uuid}
GET  /api/v1/snapshots/players/{minecraft_uuid}/latest
GET  /api/v1/snapshots/{snapshot_id}
GET  /api/v1/snapshots/replay/{replay_id}
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from api.middleware.auth import require_admin_key
from services import snapshot_service

router = APIRouter(prefix="/api/v1/snapshots", tags=["snapshots"])


class CreateSnapshotRequest(BaseModel):
    minecraft_uuid: str
    trigger: str = "scheduled"
    health: float | None = None
    food: int | None = None
    xp: float | None = None
    inventory: dict | None = None
    armor: dict | None = None
    offhand: dict | None = None
    x: float | None = None
    y: float | None = None
    z: float | None = None
    yaw: float | None = None
    pitch: float | None = None
    world: str | None = None
    dimension: str | None = None
    replay_id: str | None = None
    timestamp: str | None = None


@router.post("", status_code=201)
async def create_snapshot(
    body: CreateSnapshotRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Create a new player snapshot.
    Returns 422 if trigger is invalid.
    """
    timestamp = None
    if body.timestamp:
        timestamp = datetime.fromisoformat(body.timestamp.replace("Z", "+00:00"))

    try:
        snapshot = await snapshot_service.create_snapshot(
            db,
            body.minecraft_uuid,
            trigger=body.trigger,
            health=body.health,
            food=body.food,
            xp=body.xp,
            inventory=body.inventory,
            armor=body.armor,
            offhand=body.offhand,
            x=body.x,
            y=body.y,
            z=body.z,
            yaw=body.yaw,
            pitch=body.pitch,
            world=body.world,
            dimension=body.dimension,
            replay_id=body.replay_id,
            timestamp=timestamp,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "id": snapshot.id,
        "minecraft_uuid": snapshot.minecraft_uuid,
        "timestamp": snapshot.timestamp.isoformat(),
        "trigger": snapshot.trigger,
        "health": snapshot.health,
        "food": snapshot.food,
        "xp": snapshot.xp,
        "inventory_json": snapshot.inventory_json,
        "armor_json": snapshot.armor_json,
        "offhand_json": snapshot.offhand_json,
        "x": snapshot.x,
        "y": snapshot.y,
        "z": snapshot.z,
        "yaw": snapshot.yaw,
        "pitch": snapshot.pitch,
        "world": snapshot.world,
        "dimension": snapshot.dimension,
        "replay_id": snapshot.replay_id,
    }


@router.get("/players/{minecraft_uuid}")
async def list_player_snapshots(
    minecraft_uuid: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    trigger: str | None = None,
    since: str | None = None,
    until: str | None = None,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    List snapshots for a player, newest first.
    Supports optional filtering by trigger, since, until.
    """
    since_dt = None
    if since:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
    until_dt = None
    if until:
        until_dt = datetime.fromisoformat(until.replace("Z", "+00:00"))

    snapshots = await snapshot_service.list_snapshots(
        db,
        minecraft_uuid,
        limit=limit,
        offset=offset,
        trigger=trigger,
        since=since_dt,
        until=until_dt,
    )
    return snapshots


@router.get("/players/{minecraft_uuid}/latest")
async def get_latest_player_snapshot(
    minecraft_uuid: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Get the most recent snapshot for a player.
    Returns 404 if none exist.
    """
    snapshot = await snapshot_service.get_latest_snapshot(db, minecraft_uuid)
    if not snapshot:
        raise HTTPException(status_code=404, detail="No snapshots found for player")
    return snapshot


@router.get("/{snapshot_id}")
async def get_snapshot(
    snapshot_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Get a snapshot by ID.
    Returns 404 if not found.
    """
    snapshot = await snapshot_service.get_snapshot(db, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot


@router.get("/replay/{replay_id}")
async def get_snapshots_near_replay(
    replay_id: str,
    window_minutes: int = Query(10, ge=1, le=60),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Get snapshots for the player associated with a replay session,
    within ±window_minutes of the incident_at time.
    """
    snapshots = await snapshot_service.get_snapshots_near_replay(
        db,
        replay_id,
        window_minutes=window_minutes,
    )
    return snapshots
