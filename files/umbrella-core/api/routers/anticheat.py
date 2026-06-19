"""Anticheat endpoints — Grim flag ingestion from Umbrella plugin."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from api.middleware.auth import require_plugin_key
from services.anticheat_service import handle_cheat_flag

router = APIRouter(prefix="/api/v1/anticheat", tags=["anticheat"])


class AnticheatFlagRequest(BaseModel):
    player_uuid: str
    username: str | None = None
    check_name: str
    verbose: str
    vl: int = 0


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
