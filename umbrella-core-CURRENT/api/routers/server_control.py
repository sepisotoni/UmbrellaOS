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

    [PLUGIN] audit, 2026-09-02: "power"/"restart" no longer run a locally
    configured shell command (see services/server_control_service.py's
    module docstring for why that could never work against the real
    ACLClouds deployment — no shell access, different host entirely).
    They now route through the same plugin-push command queue mc_commands.py
    already uses, waiting briefly for the plugin to confirm before
    returning an honest result either way.
    - power: enabled=false sends '/stop' via the plugin queue; enabled=true
      always fails (501) — there is no running plugin to deliver a start
      command to while the server is offline, by definition.
    - restart: same '/stop' mechanism as power-off; whether the process
      actually restarts afterward depends on the hosting panel's own
      auto-restart-on-clean-exit configuration, not this platform.
    - maintenance: toggle or set maintenance mode (enabled=true/false) —
      unchanged, a pure settings write with no server interaction at all.
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
