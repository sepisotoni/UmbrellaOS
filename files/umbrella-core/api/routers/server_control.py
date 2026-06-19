"""Server control — power, restart, maintenance."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from api.dependencies.permissions import require_permission
from models import User
from services.server_control_service import ServerControlError, execute_server_control

router = APIRouter(prefix="/api/v1/server", tags=["server"])


class ServerControlRequest(BaseModel):
    server_id: str = Field(..., min_length=1, max_length=64)
    action: Literal["power", "restart", "maintenance"]
    enabled: bool | None = None


@router.post("/control")
async def server_control(
    body: ServerControlRequest,
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_permission("server.control")),
) -> dict:
    """
    Control a Minecraft server process.
    - power: enabled=false stop, enabled=true start (configured commands)
    - restart: run restart command
    - maintenance: toggle or set maintenance mode (enabled=true/false)
    """
    actor = auth.username if isinstance(auth, User) else "admin"
    try:
        return await execute_server_control(
            db,
            body.server_id,
            body.action,
            enabled=body.enabled,
            actor=actor,
        )
    except ServerControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
