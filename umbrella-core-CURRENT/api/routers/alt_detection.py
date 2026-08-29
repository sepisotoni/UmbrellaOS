"""
api/routers/alt_detection.py — Alt detection endpoints.

POST /api/v1/alts/check
GET  /api/v1/alts/flagged
GET  /api/v1/alts/player/{uuid}
POST /api/v1/alts/false-positive
POST /api/v1/alts/group
GET  /api/v1/alts/groups
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel

from database import get_db
from models import SuspicionEvent, AltGroup, AltGroupMember, Player
from api.middleware.auth import require_admin_key, require_plugin_key
from api.dependencies.permissions import require_permission
from services.alt_detection_service import calculate_suspicion, flag_player

router = APIRouter(prefix="/api/v1/alts", tags=["alt_detection"])


class AltCheckRequest(BaseModel):
    player_uuid: str
    ip_address: str
    username: str


class AltCheckResponse(BaseModel):
    score: int
    risk_level: str
    triggers: list[str]
    flagged: bool


class FalsePositiveRequest(BaseModel):
    event_id: int | None = None
    player_uuid: str | None = None
    reviewed_by: str


class AltGroupRequest(BaseModel):
    player_uuids: list[str]
    notes: str | None = None
    confirmed: bool = False


class SuspicionEventSchema(BaseModel):
    id: int
    player_uuid: str
    trigger: str
    points: int
    metadata_json: str | None
    created_at: str
    reviewed: bool
    reviewed_by: str | None
    false_positive: bool

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            player_uuid=obj.player_uuid,
            trigger=obj.trigger,
            points=obj.points,
            metadata_json=obj.metadata_json,
            created_at=obj.created_at.isoformat() if obj.created_at else "",
            reviewed=obj.reviewed,
            reviewed_by=obj.reviewed_by,
            false_positive=obj.false_positive,
        )

    class Config:
        from_attributes = True


class AltGroupSchema(BaseModel):
    id: int
    created_at: str
    notes: str | None
    confirmed: bool

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            created_at=obj.created_at.isoformat() if obj.created_at else "",
            notes=obj.notes,
            confirmed=obj.confirmed,
        )

    class Config:
        from_attributes = True


class AltGroupMemberSchema(BaseModel):
    id: int
    group_id: int
    player_uuid: str
    added_at: str
    added_by: str | None

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            group_id=obj.group_id,
            player_uuid=obj.player_uuid,
            added_at=obj.added_at.isoformat() if obj.added_at else "",
            added_by=obj.added_by,
        )

    class Config:
        from_attributes = True


class FlaggedPlayerSchema(BaseModel):
    uuid: str
    username: str
    suspicion_score: int
    first_seen: str

    @classmethod
    def from_orm(cls, obj):
        return cls(
            uuid=obj.uuid,
            username=obj.username,
            suspicion_score=obj.suspicion_score,
            first_seen=obj.first_seen.isoformat() if obj.first_seen else "",
        )

    class Config:
        from_attributes = True


@router.post("/check", response_model=AltCheckResponse)
async def check_alt(
    body: AltCheckRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> AltCheckResponse:
    """
    Check a player for alt detection.
    Called by plugin when player joins.
    """
    result = await calculate_suspicion(
        body.player_uuid,
        body.ip_address,
        body.username,
        db,
    )
    
    flag_result = await flag_player(
        body.player_uuid,
        result["score"],
        result["triggers"],
        db,
    )
    
    return AltCheckResponse(
        score=result["score"],
        risk_level=flag_result["risk_level"],
        triggers=result["triggers"],
        flagged=flag_result["flagged"],
    )


@router.get("/flagged", response_model=list[FlaggedPlayerSchema])
async def list_flagged_players(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.view")),
) -> list[FlaggedPlayerSchema]:
    """List players with suspicion_score >= 80."""
    result = await db.execute(
        select(Player)
        .where(Player.suspicion_score >= 80)
        .offset(skip)
        .limit(limit)
    )
    players = result.scalars().all()
    
    return [FlaggedPlayerSchema.from_orm(p) for p in players]


@router.get("/player/{uuid}")
async def get_player_suspicion(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.view")),
):
    """Get suspicion history for a specific player."""
    # Get player
    result = await db.execute(
        select(Player).where(Player.uuid == uuid)
    )
    player = result.scalar_one_or_none()
    
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Get suspicion events
    result = await db.execute(
        select(SuspicionEvent).where(SuspicionEvent.player_uuid == uuid)
    )
    events = result.scalars().all()
    
    # Get alt groups
    result = await db.execute(
        select(AltGroupMember).where(AltGroupMember.player_uuid == uuid)
    )
    group_members = result.scalars().all()
    
    alt_groups = []
    # FIX: N+1 replaced with a single IN query.
    group_ids = [m.group_id for m in group_members]
    if group_ids:
        groups_result = await db.execute(
            select(AltGroup).where(AltGroup.id.in_(group_ids))
        )
        for g in groups_result.scalars().all():
            alt_groups.append(AltGroupSchema.from_orm(g))
    
    return {
        "score": player.suspicion_score,
        "events": [SuspicionEventSchema.from_orm(e) for e in events],
        "alt_groups": alt_groups,
    }


@router.post("/false-positive")
async def mark_false_positive(
    body: FalsePositiveRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.manage")),
):
    """Mark a suspicion event as false positive."""
    if body.event_id is not None:
        event_query = select(SuspicionEvent).where(SuspicionEvent.id == body.event_id)
    elif body.player_uuid:
        event_query = (
            select(SuspicionEvent)
            .where(
                SuspicionEvent.player_uuid == body.player_uuid,
                SuspicionEvent.false_positive.is_(False),
            )
            .order_by(SuspicionEvent.created_at.desc())
            .limit(1)
        )
    else:
        raise HTTPException(status_code=422, detail="event_id or player_uuid is required")

    result = await db.execute(event_query)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.false_positive = True
    event.reviewed = True
    event.reviewed_by = body.reviewed_by
    
    # Reduce player suspicion_score by event points
    result = await db.execute(
        select(Player).where(Player.uuid == event.player_uuid)
    )
    player = result.scalar_one_or_none()
    if player:
        player.suspicion_score = max(0, player.suspicion_score - event.points)
    
    await db.flush()
    
    return {"success": True}


@router.post("/group", response_model=AltGroupSchema)
async def create_alt_group(
    body: AltGroupRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.manage")),
) -> AltGroupSchema:
    """Create an alt group linking multiple players."""
    # Create alt group
    alt_group = AltGroup(
        notes=body.notes,
        confirmed=body.confirmed,
    )
    db.add(alt_group)
    await db.flush()
    
    # Add members
    for player_uuid in body.player_uuids:
        member = AltGroupMember(
            group_id=alt_group.id,
            player_uuid=player_uuid,
        )
        db.add(member)
    
    await db.flush()
    
    return AltGroupSchema.from_orm(alt_group)


@router.get("/groups", response_model=list[AltGroupSchema])
async def list_alt_groups(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.view")),
) -> list[AltGroupSchema]:
    """List all confirmed alt groups."""
    result = await db.execute(
        select(AltGroup).where(AltGroup.confirmed == True)
    )
    groups = result.scalars().all()
    
    return [AltGroupSchema.from_orm(g) for g in groups]


class AltTrackRequest(BaseModel):
    uuid: str
    name: str
    ip: str | None = None
    brand: str | None = None


@router.post("/track", status_code=200)
async def track_player_alt(
    body: AltTrackRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_plugin_key),
) -> dict:
    """
    Called by the Minecraft plugin on every player join/quit via PlayerTelemetryListener.
    Runs alt-detection suspicion scoring for the player and flags if threshold exceeded.

    Auth: X-Plugin-Key — the plugin has no admin-key credential; this mirrors
    the same auth pattern as every other plugin-facing endpoint (plugin.py,
    anticheat.py, players.py snapshot).

    The existing POST /check endpoint does the same work but requires X-Admin-Key,
    making it permanently unreachable by the plugin. This endpoint is the
    plugin-key-auth equivalent.
    """
    ip = body.ip or "127.0.0.1"

    if ip in ("127.0.0.1", "0.0.0.0"):
        # Loopback IPs carry no alt-detection signal — skip scoring to avoid
        # false positives when the plugin runs on localhost (e.g. dev servers).
        return {"processed": False, "reason": "loopback_ip_skipped"}

    result = await calculate_suspicion(body.uuid, ip, body.name, db)
    flag_result = await flag_player(body.uuid, result["score"], result["triggers"], db)

    return {
        "processed": True,
        "score": result["score"],
        "risk_level": flag_result["risk_level"],
        "flagged": flag_result["flagged"],
        "triggers": result["triggers"],
    }
