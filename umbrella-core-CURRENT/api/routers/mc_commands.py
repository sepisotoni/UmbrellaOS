"""
api/routers/mc_commands.py — Minecraft command execution endpoints.

POST /api/v1/mc/command                — Queue a command for execution
                                          (admin/Discord-bot initiated,
                                          X-Auth-MAC/HMAC or X-Admin-Key)
GET  /api/v1/mc/commands/pending       — Get pending commands
                                          (plugin-initiated, X-Plugin-Key)
POST /api/v1/mc/commands/{id}/complete — Mark command as completed
                                          (plugin-initiated, X-Plugin-Key)

The enqueue side and the poll/complete side are different actors with
different auth: staff/bot enqueue via the admin key, the plugin itself
polls and acks via the plugin key. (Phase 13 Step 2 — the poll/complete
pair used to require_admin_key too, which the plugin was never given a
credential for; fixed to match every other plugin-facing router.)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timezone

from database import get_db
from models import MCCommand, AuditLog
from api.middleware.auth import require_admin_hmac_or_session, require_plugin_key
from api.middleware.audit import create_audit_log, AuditAction
from uuid import uuid4

router = APIRouter(prefix="/api/v1/mc", tags=["mc-commands"])


class MCCommandRequest(BaseModel):
    command: str
    requested_by_discord_id: str
    requested_by_username: str


class MCCommandResponse(BaseModel):
    id: int
    command: str
    status: str
    requested_by_username: str
    requested_by_discord_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class MCCommandCompleteRequest(BaseModel):
    output: str
    success: bool


@router.post("/command", status_code=201, response_model=MCCommandResponse)
async def create_mc_command(
    body: MCCommandRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_hmac_or_session),
) -> MCCommandResponse:
    """
    Queue a Minecraft command for execution.

    Auth: require_admin_hmac_or_session — the Discord bot (PBKDF2 MAC),
    raw X-Admin-Key (dashboard/admin tools), or a session token may enqueue
    commands. The plugin itself uses X-Plugin-Key only for the poll/ack pair.
    """
    if not body.command or not body.command.strip():
        raise HTTPException(status_code=400, detail="Command cannot be empty")
    
    # Create MC command record
    mc_command = MCCommand(
        command=body.command.strip(),
        requested_by_discord_id=body.requested_by_discord_id,
        requested_by_username=body.requested_by_username,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(mc_command)
    await db.flush()
    
    # Create audit log entry
    await create_audit_log(
        db=db,
        action=AuditAction.MC_COMMAND_REQUESTED,
        actor=f"discord:{body.requested_by_discord_id}",
        actor_type="bot",
        target=str(mc_command.id),
        details={
            "command": body.command,
            "requested_by": body.requested_by_username,
        },
    )
    
    await db.commit()
    await db.refresh(mc_command)
    
    return MCCommandResponse.model_validate(mc_command)


@router.get("/commands/pending", response_model=list[MCCommandResponse])
async def get_pending_mc_commands(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_plugin_key),
) -> list[MCCommandResponse]:
    """
    Get all pending Minecraft commands.

    The plugin calls this every 5 seconds to poll for new commands.

    Auth: X-Plugin-Key (Phase 13 Step 2 — was require_admin_key, which
    checks a different secret (settings.admin_key) than every other
    plugin-facing endpoint in this codebase (plugin.py, anticheat.py,
    both on require_plugin_key / settings.secret_key). The plugin's
    config.yml only ever holds a plugin key, so the old dependency made
    this endpoint permanently unreachable by the actual plugin — caught
    by reading this file directly rather than trusting the scoping doc's
    endpoint list, which didn't mention auth per-endpoint at all.
    """
    result = await db.execute(
        select(MCCommand).where(MCCommand.status == "pending")
    )
    commands = result.scalars().all()
    
    return [MCCommandResponse.model_validate(cmd) for cmd in commands]


@router.post("/commands/{command_id}/complete")
async def complete_mc_command(
    command_id: int,
    body: MCCommandCompleteRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_plugin_key),
):
    """
    Mark a Minecraft command as completed.

    The plugin calls this after executing a command to report the result.

    Auth: X-Plugin-Key — see get_pending_mc_commands docstring above for
    why this changed from require_admin_key (Phase 13 Step 2).
    """
    result = await db.execute(
        select(MCCommand).where(MCCommand.id == command_id)
    )
    mc_command = result.scalar_one_or_none()
    
    if not mc_command:
        raise HTTPException(status_code=404, detail="MC command not found")
    
    if mc_command.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Command already has status: {mc_command.status}",
        )
    
    # Update command status
    mc_command.status = "completed" if body.success else "failed"
    mc_command.output = body.output
    mc_command.success = body.success
    mc_command.completed_at = datetime.now(timezone.utc)
    
    # Create audit log entry
    await create_audit_log(
        db=db,
        action=AuditAction.MC_COMMAND_EXECUTED,
        actor="plugin",
        actor_type="plugin",
        target=str(mc_command.id),
        details={
            "command": mc_command.command,
            "success": body.success,
            "output": body.output,
        },
    )
    
    await db.commit()
    
    return {"status": "ok", "message": "Command marked as completed"}
