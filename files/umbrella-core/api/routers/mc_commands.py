"""
api/routers/mc_commands.py — Minecraft command execution endpoints.

POST /api/v1/mc/command           — Queue a command for execution
GET  /api/v1/mc/commands/pending  — Get pending commands
POST /api/v1/mc/commands/{id}/complete — Mark command as completed
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import MCCommand, AuditLog
from api.middleware.auth import require_admin_key
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
    _auth: str = Depends(require_admin_key),
) -> MCCommandResponse:
    """
    Queue a Minecraft command for execution.
    
    The Discord bot calls this to request command execution.
    The plugin polls pending commands and executes them.
    """
    if not body.command or not body.command.strip():
        raise HTTPException(status_code=400, detail="Command cannot be empty")
    
    # Create MC command record
    mc_command = MCCommand(
        command=body.command.strip(),
        requested_by_discord_id=body.requested_by_discord_id,
        requested_by_username=body.requested_by_username,
        status="pending",
        created_at=datetime.utcnow(),
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
    _auth: str = Depends(require_admin_key),
) -> list[MCCommandResponse]:
    """
    Get all pending Minecraft commands.
    
    The plugin calls this every 5 seconds to poll for new commands.
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
    _auth: str = Depends(require_admin_key),
):
    """
    Mark a Minecraft command as completed.
    
    The plugin calls this after executing a command to report the result.
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
    mc_command.completed_at = datetime.utcnow()
    
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
