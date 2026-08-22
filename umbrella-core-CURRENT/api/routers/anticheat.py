"""Anticheat endpoints — Grim flag ingestion from Umbrella plugin."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from api.middleware.auth import require_plugin_key
from api.dependencies.permissions import require_permission
from services.anticheat_service import handle_cheat_flag
from models.anticheat_violation import AnticheatViolation

router = APIRouter(prefix="/api/v1/anticheat", tags=["anticheat"])


class AnticheatFlagRequest(BaseModel):
    player_uuid: str
    username: str | None = None
    check_name: str
    verbose: str
    vl: int = 0
    # server_id added in P15 Task 5 plugin update; nullable for old plugin versions
    server_id: str | None = None


class ViolationRecord(BaseModel):
    id: str
    player_uuid: str
    player_name: str
    server_id: str | None
    check_name: str
    verbose: str
    vl: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/flag")
async def report_cheat_flag(
    body: AnticheatFlagRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_plugin_key),
) -> dict:
    """Receive a Grim anticheat flag from the Minecraft plugin."""
    return await handle_cheat_flag(
        db,
        body.player_uuid,
        body.username or "",
        body.check_name,
        body.verbose,
        body.vl,
        server_id=body.server_id,
    )


@router.get("/violations", response_model=list[ViolationRecord])
async def list_violations(
    player_uuid: Optional[str] = Query(None, description="Filter by player UUID"),
    server_id: Optional[str] = Query(None, description="Filter by server ID"),
    check_name: Optional[str] = Query(None, description="Filter by Grim check name"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("punishments.view")),
) -> list[ViolationRecord]:
    """List stored Grim anticheat violations from the dedicated violations table.

    All filters (player_uuid, server_id, check_name) are now first-class indexed
    column lookups — no more regex parsing of ai_summary strings.
    """
    query = (
        select(AnticheatViolation)
        .order_by(AnticheatViolation.timestamp.desc())
        .limit(limit)
    )
    if player_uuid:
        query = query.where(AnticheatViolation.player_uuid == player_uuid)
    if server_id:
        query = query.where(AnticheatViolation.server_id == server_id)
    if check_name:
        query = query.where(AnticheatViolation.check_name.ilike(f"%{check_name}%"))

    result = await db.execute(query)
    violations = result.scalars().all()

    return [
        ViolationRecord(
            id=v.id,
            player_uuid=v.player_uuid,
            player_name=v.player_name,
            server_id=v.server_id,
            check_name=v.check_name,
            verbose=v.verbose,
            vl=v.vl,
            created_at=v.timestamp,
        )
        for v in violations
    ]
