"""
api/routers/bot_registration.py — Bot webhook registration + command manifest + guild data.

POST /api/v1/bot/register   — Bot registers its callback URL on startup.
GET  /api/v1/bot/register   — Dashboard reads current bot registration status.
POST /api/v1/bot/commands   — Bot pushes its full slash command manifest on startup.
GET  /api/v1/bot/commands   — Dashboard reads the command manifest.
POST /api/v1/bot/channels   — Bot pushes guild text channel list on startup.
GET  /api/v1/bot/channels   — Dashboard reads channel list for broadcaster dropdown.
POST /api/v1/bot/roles      — Bot pushes guild mentionable role list on startup.
GET  /api/v1/bot/roles      — Dashboard reads role list for role-mention dropdown.

Auth: require_admin_hmac_or_session (only the bot or a dashboard session).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import require_admin_hmac_or_session
from database import get_db
from models.bot_registration import BotRegistration
from models.bot_command_manifest import BotCommandManifest
from models.bot_guild_channels import BotGuildChannels
from models.bot_guild_roles import BotGuildRoles
import services.bot_push_service as bot_push_service

router = APIRouter(prefix="/api/v1/bot", tags=["bot"])


# ─── Bot Registration ──────────────────────────────────────────────────────────

class BotRegisterRequest(BaseModel):
    callback_url: str


class BotRegisterResponse(BaseModel):
    registered: bool
    callback_url: str
    registered_at: str | None = None


@router.post("/register", response_model=BotRegisterResponse)
async def register_bot(
    body: BotRegisterRequest,
    auth: str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> BotRegisterResponse:
    """
    Upsert the bot's webhook callback URL. Always writes to id=1 so there
    is at most one registration. Subsequent bot restarts overwrite the URL
    with the (potentially new) HeavenCloud address.
    """
    if not body.callback_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="callback_url must be an http(s) URL")

    now = datetime.now(timezone.utc)
    existing = await db.get(BotRegistration, 1)
    if existing:
        existing.callback_url = body.callback_url
        existing.registered_at = now
    else:
        db.add(BotRegistration(id=1, callback_url=body.callback_url))

    await db.commit()
    bot_push_service.invalidate_cache()

    return BotRegisterResponse(
        registered=True,
        callback_url=body.callback_url,
        registered_at=now.isoformat(),
    )


@router.get("/register")
async def get_bot_registration(
    auth: str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return current bot registration status. Dashboard uses this to show
    whether the bot has registered its callback URL and when it last did so.
    """
    row = await db.get(BotRegistration, 1)
    if not row:
        return {"registered": False, "callback_url": None, "registered_at": None}
    return {
        "registered": True,
        "callback_url": row.callback_url,
        "registered_at": row.registered_at.isoformat() if row.registered_at else None,
    }


# ─── Bot Command Manifest ──────────────────────────────────────────────────────

class CommandSchema(BaseModel):
    name: str
    description: str
    args: str          # e.g. "<server_id>" or "[player]" or ""
    owner_only: bool   # True if require_owner_role() is applied


class CommandManifestRequest(BaseModel):
    commands: list[CommandSchema]


@router.post("/commands")
async def push_command_manifest(
    body: CommandManifestRequest,
    auth: str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bot pushes its full slash command list on startup."""
    payload = json.dumps([c.model_dump() for c in body.commands])
    now = datetime.now(timezone.utc)

    existing = await db.get(BotCommandManifest, 1)
    if existing:
        existing.commands = payload
        existing.pushed_at = now
    else:
        db.add(BotCommandManifest(id=1, commands=payload, pushed_at=now))

    await db.commit()
    return {"ok": True, "count": len(body.commands)}


@router.get("/commands")
async def get_command_manifest(
    auth: str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Dashboard reads the command manifest."""
    row = await db.get(BotCommandManifest, 1)
    if not row:
        return {"commands": [], "pushed_at": None}
    return {
        "commands": json.loads(row.commands),
        "pushed_at": row.pushed_at.isoformat() if row.pushed_at else None,
    }


# ─── Guild Channels ────────────────────────────────────────────────────────────

class ChannelSchema(BaseModel):
    id: str            # Discord snowflake as string
    name: str          # channel name without #
    category: str | None = None  # parent category name, if any


class GuildChannelsRequest(BaseModel):
    channels: list[ChannelSchema]


@router.post("/channels")
async def push_guild_channels(
    body: GuildChannelsRequest,
    auth: str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bot pushes its full guild text-channel list on startup."""
    payload = json.dumps([c.model_dump() for c in body.channels])
    now = datetime.now(timezone.utc)

    existing = await db.get(BotGuildChannels, 1)
    if existing:
        existing.channels = payload
        existing.pushed_at = now
    else:
        db.add(BotGuildChannels(id=1, channels=payload, pushed_at=now))

    await db.commit()
    return {"ok": True, "count": len(body.channels)}


@router.get("/channels")
async def get_guild_channels(
    auth: str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Dashboard reads guild channel list for broadcaster dropdown."""
    row = await db.get(BotGuildChannels, 1)
    if not row:
        return {"channels": [], "pushed_at": None}
    return {
        "channels": json.loads(row.channels),
        "pushed_at": row.pushed_at.isoformat() if row.pushed_at else None,
    }


# ─── Guild Roles ───────────────────────────────────────────────────────────────

class RoleSchema(BaseModel):
    id: str    # Discord snowflake as string
    name: str  # role name (e.g. "Staff", "@everyone")
    color: int = 0  # Discord role color as int (0 = no color)


class GuildRolesRequest(BaseModel):
    roles: list[RoleSchema]


@router.post("/roles")
async def push_guild_roles(
    body: GuildRolesRequest,
    auth: str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bot pushes mentionable guild role list on startup."""
    payload = json.dumps([r.model_dump() for r in body.roles])
    now = datetime.now(timezone.utc)

    existing = await db.get(BotGuildRoles, 1)
    if existing:
        existing.roles = payload
        existing.pushed_at = now
    else:
        db.add(BotGuildRoles(id=1, roles=payload, pushed_at=now))

    await db.commit()
    return {"ok": True, "count": len(body.roles)}


@router.get("/roles")
async def get_guild_roles(
    auth: str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Dashboard reads mentionable role list for broadcaster role-mention dropdown."""
    row = await db.get(BotGuildRoles, 1)
    if not row:
        return {"roles": [], "pushed_at": None}
    return {
        "roles": json.loads(row.roles),
        "pushed_at": row.pushed_at.isoformat() if row.pushed_at else None,
    }
