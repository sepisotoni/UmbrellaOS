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
from models import AITask, Player

router = APIRouter(prefix="/api/v1/anticheat", tags=["anticheat"])


class AnticheatFlagRequest(BaseModel):
    player_uuid: str
    username: str | None = None
    check_name: str
    verbose: str
    vl: int = 0


class ViolationRecord(BaseModel):
    id: int
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
    )


@router.get("/violations", response_model=list[ViolationRecord])
async def list_violations(
    player_uuid: Optional[str] = Query(None, description="Filter by player UUID"),
    server_id: Optional[str] = Query(None, description="Filter by server ID (not tracked currently, reserved)"),
    check_name: Optional[str] = Query(None, description="Filter by Grim check name"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("punishments.view")),
) -> list[ViolationRecord]:
    """List stored Grim anticheat violations (flags written to DB via POST /flag).

    Violations are stored as AITask rows with task_type='anticheat_review'.
    The ai_summary encodes 'check_name' and 'vl'; evidence holds the verbose string.
    """
    query = (
        select(AITask)
        .where(AITask.task_type == "anticheat_review")
        .order_by(AITask.created_at.desc())
        .limit(limit)
    )
    if player_uuid:
        query = query.where(AITask.player_uuid == player_uuid)
    if check_name:
        # check_name is embedded in ai_recommendation and ai_summary; filter on ai_summary substring
        query = query.where(AITask.ai_summary.ilike(f"%{check_name}%"))

    result = await db.execute(query)
    tasks = result.scalars().all()

    # Resolve player usernames in one go
    uuids = list({t.player_uuid for t in tasks if t.player_uuid})
    player_map: dict[str, str] = {}
    if uuids:
        pr = await db.execute(select(Player).where(Player.uuid.in_(uuids)))
        for p in pr.scalars().all():
            player_map[p.uuid] = p.username

    violations = []
    for task in tasks:
        # Parse check_name and vl from ai_summary: "Grim flagged <user> for <check> (VL <n>) — action: <a>"
        parsed_check = ""
        parsed_vl = 0
        summary = task.ai_summary or ""
        import re as _re
        m = _re.search(r"for (.+?) \(VL (\d+)\)", summary)
        if m:
            parsed_check = m.group(1)
            parsed_vl = int(m.group(2))

        if check_name and parsed_check and check_name.lower() not in parsed_check.lower():
            continue

        violations.append(ViolationRecord(
            id=task.id,
            player_uuid=task.player_uuid or "",
            player_name=player_map.get(task.player_uuid or "", task.player_uuid or ""),
            server_id=None,  # not tracked in the current schema
            check_name=parsed_check or check_name or "",
            verbose=task.evidence or "",
            vl=parsed_vl,
            created_at=task.created_at,
        ))

    return violations
