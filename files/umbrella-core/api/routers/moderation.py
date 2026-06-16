"""
api/routers/moderation.py — Moderation endpoints.

POST /api/v1/moderation/kick       — Kick a player from server
POST /api/v1/moderation/warn       — Warn a player
POST /api/v1/moderation/ban        — Ban a player
POST /api/v1/moderation/unban      — Unban a player
POST /api/v1/moderation/ipban      — IP ban (requires special permission)
POST /api/v1/moderation/ipunban    — IP unban
GET  /api/v1/moderation/active     — Get active punishments for a player

All responses require admin key authentication.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import Player, Punishment, IPAddress
from api.middleware.auth import require_admin_key

router = APIRouter(prefix="/api/v1/moderation", tags=["moderation"])


class KickRequest(BaseModel):
    player_uuid: str
    reason: str = "No reason provided"
    staff_id: str | None = None


class WarnRequest(BaseModel):
    player_uuid: str
    reason: str
    staff_id: str | None = None


class BanRequest(BaseModel):
    player_uuid: str
    reason: str
    expires_at: datetime | None = None
    staff_id: str | None = None
    is_temporary: bool = False


class UnbanRequest(BaseModel):
    player_uuid: str
    staff_id: str | None = None


class IPBanRequest(BaseModel):
    ip_address: str
    reason: str
    staff_id: str | None = None


class IPUnbanRequest(BaseModel):
    ip_address: str
    staff_id: str | None = None


class ModerationResponseSchema(BaseModel):
    id: str
    player_uuid: str
    type: str
    reason: str
    active: bool
    created_at: datetime
    expires_at: datetime | None = None

    class Config:
        from_attributes = True


@router.post("/kick", response_model=dict, status_code=200)
async def kick_player(
    body: KickRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> dict:
    """Kick a player from the server (disconnects immediately)."""
    player_result = await db.execute(
        select(Player).where(Player.uuid == body.player_uuid)
    )
    player = player_result.scalar_one_or_none()

    if player is None:
        raise HTTPException(status_code=404, detail=f"Player '{body.player_uuid}' not found")

    # Create temporary "kick" record for audit
    kick_record = Punishment(
        player_uuid=body.player_uuid,
        staff_id=body.staff_id,
        type="kick",
        reason=body.reason,
        active=False,  # Kick doesn't persist
    )
    db.add(kick_record)
    await db.flush()

    return {
        "success": True,
        "player_uuid": body.player_uuid,
        "action": "kick",
        "reason": body.reason,
    }


@router.post("/warn", response_model=ModerationResponseSchema, status_code=201)
async def warn_player(
    body: WarnRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> ModerationResponseSchema:
    """Issue a warning to a player."""
    player_result = await db.execute(
        select(Player).where(Player.uuid == body.player_uuid)
    )
    player = player_result.scalar_one_or_none()

    if player is None:
        raise HTTPException(status_code=404, detail=f"Player '{body.player_uuid}' not found")

    warning = Punishment(
        player_uuid=body.player_uuid,
        staff_id=body.staff_id,
        type="warn",
        reason=body.reason,
        active=True,
    )
    db.add(warning)
    await db.flush()

    return ModerationResponseSchema.model_validate(warning)


@router.post("/ban", response_model=ModerationResponseSchema, status_code=201)
async def ban_player(
    body: BanRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> ModerationResponseSchema:
    """Ban a player (permanent or temporary)."""
    player_result = await db.execute(
        select(Player).where(Player.uuid == body.player_uuid)
    )
    player = player_result.scalar_one_or_none()

    if player is None:
        raise HTTPException(status_code=404, detail=f"Player '{body.player_uuid}' not found")

    ban = Punishment(
        player_uuid=body.player_uuid,
        staff_id=body.staff_id,
        type="tempban" if body.is_temporary else "ban",
        reason=body.reason,
        expires_at=body.expires_at,
        active=True,
    )
    db.add(ban)
    await db.flush()

    return ModerationResponseSchema.model_validate(ban)


@router.post("/unban", response_model=ModerationResponseSchema, status_code=200)
async def unban_player(
    body: UnbanRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> ModerationResponseSchema:
    """Revoke a ban for a player."""
    # Get active ban
    ban_result = await db.execute(
        select(Punishment).where(
            (Punishment.player_uuid == body.player_uuid) &
            (Punishment.type.in_(["ban", "tempban"])) &
            (Punishment.active == True)
        )
    )
    ban = ban_result.scalar_one_or_none()

    if ban is None:
        raise HTTPException(
            status_code=404, detail=f"No active ban found for player '{body.player_uuid}'"
        )

    ban.active = False
    await db.flush()

    return ModerationResponseSchema.model_validate(ban)


@router.post("/ipban", response_model=dict, status_code=201)
async def ipban_address(
    body: IPBanRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> dict:
    """Ban an IP address (affects all players from that IP)."""
    # Create a system punishment for IP ban
    ipban = Punishment(
        player_uuid="SYSTEM",  # Special marker for IP-level punishment
        staff_id=body.staff_id,
        type="ipban",
        reason=f"IP: {body.ip_address} - {body.reason}",
        active=True,
    )
    db.add(ipban)
    await db.flush()

    return {
        "success": True,
        "ip_address": body.ip_address,
        "reason": body.reason,
        "punishment_id": ipban.id,
    }


@router.post("/ipunban", response_model=dict, status_code=200)
async def ipunban_address(
    body: IPUnbanRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> dict:
    """Revoke an IP ban."""
    # Find active IP ban
    ipban_result = await db.execute(
        select(Punishment).where(
            (Punishment.type == "ipban") &
            (Punishment.reason.contains(body.ip_address)) &
            (Punishment.active == True)
        )
    )
    ipban = ipban_result.scalar_one_or_none()

    if ipban is None:
        raise HTTPException(
            status_code=404, detail=f"No active IP ban found for '{body.ip_address}'"
        )

    ipban.active = False
    await db.flush()

    return {
        "success": True,
        "ip_address": body.ip_address,
        "action": "ipunban",
    }


@router.get("/active/{player_uuid}", response_model=list[ModerationResponseSchema])
async def get_active_punishments(
    player_uuid: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> list[ModerationResponseSchema]:
    """Get all active punishments for a player."""
    result = await db.execute(
        select(Punishment).where(
            (Punishment.player_uuid == player_uuid) &
            (Punishment.active == True)
        )
    )
    punishments = result.scalars().all()

    return [ModerationResponseSchema.model_validate(p) for p in punishments]
