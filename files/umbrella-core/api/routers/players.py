"""
api/routers/players.py — Player endpoints.

GET  /api/v1/players           — list all players (with optional search by username)
GET  /api/v1/players/{uuid}    — get a single player by UUID

All responses require admin key or session authentication.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import Player
from api.dependencies.permissions import require_permission

router = APIRouter(prefix="/api/v1/players", tags=["players"])


class IPAddressSchema(BaseModel):
    id: str
    ip_address: str
    first_seen: datetime
    last_seen: datetime

    class Config:
        from_attributes = True


class PlayerSchema(BaseModel):
    uuid: str
    username: str
    first_seen: datetime
    last_seen: datetime
    playtime: int
    joins: int
    deaths: int
    risk_score: int
    discord_id: str | None

    class Config:
        from_attributes = True


class PlayerDetailSchema(PlayerSchema):
    ip_addresses: list[IPAddressSchema] = []

    class Config:
        from_attributes = True


@router.get("", response_model=list[PlayerSchema])
async def list_players(
    username: str | None = Query(None, description="Optional username substring to search"),
    skip: int = Query(0, ge=0, description="Number of players to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of players to return"),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.view")),
) -> list[PlayerSchema]:
    """
    List all players with optional username search.
    Supports pagination via skip and limit parameters.
    """
    query = select(Player)

    # If username filter is provided, search for it
    if username:
        query = query.where(
            Player.username.ilike(f"%{username}%")
        )

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    players = result.scalars().all()

    return [PlayerSchema.model_validate(p) for p in players]


@router.get("/{uuid}", response_model=PlayerDetailSchema)
async def get_player(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.view")),
) -> PlayerDetailSchema:
    """Get a player by UUID with all related data (IP addresses)."""
    result = await db.execute(
        select(Player)
        .options(selectinload(Player.ip_addresses))
        .where(Player.uuid == uuid)
    )
    player = result.scalar_one_or_none()

    if player is None:
        raise HTTPException(status_code=404, detail=f"Player '{uuid}' not found")

    return PlayerDetailSchema.model_validate(player)
