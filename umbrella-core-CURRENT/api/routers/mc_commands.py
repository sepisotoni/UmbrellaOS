"""
api/routers/mc_commands.py — Minecraft command execution endpoints.

POST /api/v1/mc/command                — Queue a command for execution
                                          (admin/Discord-bot initiated,
                                          X-Auth-MAC/HMAC or X-Admin-Key)
GET  /api/v1/mc/commands/pending       — Get pending commands
                                          (plugin-initiated, server-bound key)
POST /api/v1/mc/commands/{id}/complete?server_id=... — Mark command as completed
                                                       (plugin-initiated, server-bound key)

The enqueue side and the poll/complete side are different actors with
different auth: staff/bot enqueue via the admin key, the plugin itself
polls and acks via the plugin key. (Phase 13 Step 2 — the poll/complete
pair used to require_admin_key too, which the plugin was never given a
credential for; fixed to match every other plugin-facing router.)

Every command carries a server_id (default "default" for enqueue callers
that omit one). Polling and completion are scoped to that ID. This is queue
routing and, when X-Plugin-Server-Key is configured, authorization bound to
that ID. Shared-key authentication remains a temporary migration fallback
controlled by PLUGIN_SERVER_LEGACY_AUTH_ENABLED.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timezone

from database import get_db
from models import MCCommand, AuditLog
from api.middleware.auth import (
    require_admin_hmac_or_session,
    require_server_plugin_key,
)
from api.middleware.audit import create_audit_log, AuditAction
from uuid import uuid4

router = APIRouter(prefix="/api/v1/mc", tags=["mc-commands"])


class MCCommandRequest(BaseModel):
    command: str
    requested_by_discord_id: str
    requested_by_username: str
    # FIX ([PLUGIN] audit): default "default" preserves existing behavior
    # for callers that don't specify one (single-server deployments,
    # anything not yet updated) — see models/mc_commands.py for the full
    # fleet-routing rationale.
    server_id: str = "default"


class MCCommandResponse(BaseModel):
    id: int
    command: str
    status: str
    server_id: str
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
    commands. The plugin uses its server-bound key for poll/ack after
    migration, or the shared plugin key while legacy auth remains enabled.
    """
    if not body.command or not body.command.strip():
        raise HTTPException(status_code=400, detail="Command cannot be empty")

    # Create MC command record
    mc_command = MCCommand(
        command=body.command.strip(),
        server_id=body.server_id,
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
            "server_id": body.server_id,
            "requested_by": body.requested_by_username,
        },
    )

    await db.commit()
    await db.refresh(mc_command)

    return MCCommandResponse.model_validate(mc_command)


@router.get("/commands/pending", response_model=list[MCCommandResponse])
async def get_pending_mc_commands(
    server_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_server_plugin_key),
) -> list[MCCommandResponse]:
    """
    Get all pending Minecraft commands for one server.

    The plugin calls this every 5 seconds to poll for new commands.

    FIX ([PLUGIN] audit): previously returned every pending command
    globally, with no server_id filter at all — see models/mc_commands.py
    for the full fleet-routing bug this caused. Defaults to "default" so a
    plugin instance that hasn't been updated to send its own server_id yet
    keeps working exactly as before (scoped to the implicit "default"
    queue every existing row already uses via the column's default).

    A configured X-Plugin-Server-Key is bound to this server ID. The
    shared-key fallback can be disabled after the fleet has migrated.

    Auth: X-Plugin-Server-Key (with a temporary X-Plugin-Key fallback).
    Before the server-bound key was added this used require_admin_key, which
    checks a different secret (settings.admin_key) than every other
    plugin-facing endpoint in this codebase (plugin.py, anticheat.py,
    both on require_plugin_key / settings.secret_key). The plugin's
    config.yml only ever holds a plugin key, so the old dependency made
    this endpoint permanently unreachable by the actual plugin — caught
    by reading this file directly rather than trusting the scoping doc's
    endpoint list, which didn't mention auth per-endpoint at all.
    """
    result = await db.execute(
        select(MCCommand).where(
            MCCommand.status == "pending",
            MCCommand.server_id == server_id,
        )
    )
    commands = result.scalars().all()

    return [MCCommandResponse.model_validate(cmd) for cmd in commands]


@router.post("/commands/{command_id}/complete")
async def complete_mc_command(
    command_id: int,
    body: MCCommandCompleteRequest,
    server_id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_server_plugin_key),
):
    """
    Mark a Minecraft command as completed.

    The plugin calls this after executing a command to report the result.
    A matching server_id query parameter is required; omitted or mismatched
    IDs cannot complete the command.

    Auth: X-Plugin-Server-Key (with a temporary X-Plugin-Key fallback).
    """
    result = await db.execute(
        select(MCCommand).where(
            MCCommand.id == command_id,
            MCCommand.server_id == server_id,
        )
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
