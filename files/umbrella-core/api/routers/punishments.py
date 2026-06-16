"""
api/routers/punishments.py — Punishment endpoints.

GET  /api/v1/punishments           — list all punishments
POST /api/v1/punishments           — create a new punishment
PATCH /api/v1/punishments/{id}     — update a punishment
POST /api/v1/punishments/{id}/revoke — revoke a punishment

All responses require admin key authentication.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import Punishment, Player
from api.middleware.auth import require_admin_key

router = APIRouter(prefix="/api/v1/punishments", tags=["punishments"])


class PunishmentCreateRequest(BaseModel):
    player_uuid: str
    staff_id: str | None = None
    type: str  # "ban", "mute", "warn", etc.
    reason: str
    expires_at: datetime | None = None


class PunishmentUpdateRequest(BaseModel):
    type: str | None = None
    reason: str | None = None
    expires_at: datetime | None = None


class PunishmentSchema(BaseModel):
    id: str
    player_uuid: str
    staff_id: str | None
    type: str
    reason: str
    created_at: datetime
    expires_at: datetime | None
    active: bool

    class Config:
        from_attributes = True


@router.get("", response_model=list[PunishmentSchema])
async def list_punishments(
    player_uuid: str | None = Query(None, description="Filter by player UUID"),
    active_only: bool = Query(True, description="Only return active punishments"),
    skip: int = Query(0, ge=0, description="Number of punishments to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of punishments to return"),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> list[PunishmentSchema]:
    """List all punishments with optional filtering."""
    query = select(Punishment)

    if player_uuid:
        query = query.where(Punishment.player_uuid == player_uuid)

    if active_only:
        query = query.where(Punishment.active == True)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    punishments = result.scalars().all()

    return [PunishmentSchema.model_validate(p) for p in punishments]


@router.post("", response_model=PunishmentSchema, status_code=201)
async def create_punishment(
    body: PunishmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> PunishmentSchema:
    """Create a new punishment for a player."""
    # Verify player exists
    player_result = await db.execute(
        select(Player).where(Player.uuid == body.player_uuid)
    )
    player = player_result.scalar_one_or_none()

    if player is None:
        raise HTTPException(status_code=404, detail=f"Player '{body.player_uuid}' not found")

    # Create punishment
    punishment = Punishment(
        player_uuid=body.player_uuid,
        staff_id=body.staff_id,
        type=body.type,
        reason=body.reason,
        expires_at=body.expires_at,
        active=True,
    )

    db.add(punishment)
    await db.flush()

    return PunishmentSchema.model_validate(punishment)


@router.patch("/{punishment_id}", response_model=PunishmentSchema)
async def update_punishment(
    punishment_id: str,
    body: PunishmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> PunishmentSchema:
    """Update a punishment (type, reason, or expiry)."""
    result = await db.execute(
        select(Punishment).where(Punishment.id == punishment_id)
    )
    punishment = result.scalar_one_or_none()

    if punishment is None:
        raise HTTPException(status_code=404, detail=f"Punishment '{punishment_id}' not found")

    # Update fields if provided
    if body.type is not None:
        punishment.type = body.type
    if body.reason is not None:
        punishment.reason = body.reason
    if body.expires_at is not None:
        punishment.expires_at = body.expires_at

    await db.flush()

    return PunishmentSchema.model_validate(punishment)


@router.post("/{punishment_id}/revoke", response_model=PunishmentSchema)
async def revoke_punishment(
    punishment_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> PunishmentSchema:
    """Revoke (deactivate) a punishment."""
    result = await db.execute(
        select(Punishment).where(Punishment.id == punishment_id)
    )
    punishment = result.scalar_one_or_none()

    if punishment is None:
        raise HTTPException(status_code=404, detail=f"Punishment '{punishment_id}' not found")

    punishment.active = False
    await db.flush()

    return PunishmentSchema.model_validate(punishment)
