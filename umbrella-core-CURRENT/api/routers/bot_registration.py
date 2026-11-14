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
POST /api/v1/bot/guilds/sync — Bot syncs all joined guilds and their resources.
GET  /api/v1/bot/guilds      — Dashboard and bot read per-guild config.
GET  /api/v1/bot/runtime-state — Bot fetches only changed runtime settings.
PATCH /api/v1/bot/guilds/{id} — Owner updates a guild's role/channel mappings.

Auth: require_admin_hmac_or_session (only the bot or a dashboard session).
"""

from __future__ import annotations

import json
import hashlib
import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from api.dependencies.permissions import require_owner
from api.middleware.auth import require_admin_hmac_or_session
from database import get_db
from models.bot_registration import BotRegistration
from models.bot_command_manifest import BotCommandManifest
from models.bot_guild import BotGuild
from models.bot_guild_channels import BotGuildChannels
from models.bot_guild_roles import BotGuildRoles
from models.setting import Setting
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
        raise HTTPException(
            status_code=422, detail="callback_url must be an http(s) URL"
        )

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
    args: str  # e.g. "<server_id>" or "[player]" or ""
    owner_only: bool  # True if require_owner_role() is applied


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
    id: str  # Discord snowflake as string
    name: str  # channel name without #
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
    id: str  # Discord snowflake as string
    name: str  # role name (e.g. "Staff", "@everyone")
    color: int = 0  # Discord role color as int (0 = no color)
    mentionable: bool = True
    is_default: bool = False


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


# ─── Per-Guild Configuration ──────────────────────────────────────────────────


class GuildSyncSchema(BaseModel):
    guild_id: str
    name: str
    channels: list[ChannelSchema]
    roles: list[RoleSchema]


class GuildSyncRequest(BaseModel):
    guilds: list[GuildSyncSchema]


class GuildConfigPatch(BaseModel):
    staff_alert_channel_id: str | None = None
    verified_role_id: str | None = None
    owner_role_id: str | None = None
    admin_role_id: str | None = None
    moderator_role_id: str | None = None
    helper_role_id: str | None = None


def _guild_to_dict(guild: BotGuild) -> dict:
    return {
        "guild_id": guild.guild_id,
        "name": guild.name,
        "channels": json.loads(guild.channels),
        "roles": json.loads(guild.roles),
        "staff_alert_channel_id": guild.staff_alert_channel_id,
        "verified_role_id": guild.verified_role_id,
        "owner_role_id": guild.owner_role_id,
        "admin_role_id": guild.admin_role_id,
        "moderator_role_id": guild.moderator_role_id,
        "helper_role_id": guild.helper_role_id,
        "pushed_at": guild.pushed_at.isoformat() if guild.pushed_at else None,
    }


@router.get("/guilds")
async def get_bot_guilds(
    auth: str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = await db.scalars(
        select(BotGuild).where(BotGuild.is_active.is_(True)).order_by(BotGuild.name)
    )
    return {"guilds": [_guild_to_dict(guild) for guild in rows.all()]}


@router.get("/runtime-state", response_model=None)
async def get_bot_runtime_state(
    response: Response,
    config_revision: str | None = None,
    token_revision: str | None = None,
    auth: str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict | Response:
    """Return bot config only when its revision changes; disclose tokens only on token changes."""
    if auth != "hmac":
        raise HTTPException(
            status_code=403, detail="Bot runtime state requires HMAC authentication"
        )

    setting_rows = await db.scalars(
        select(Setting).where(
            Setting.key.in_(
                (
                    "discord.bot_token",
                    "discord.callback_url",
                    "discord.callback_port",
                    "discord.command_prefix",
                )
            )
        )
    )
    settings = {setting.key: setting.value for setting in setting_rows.all()}
    token = settings.get("discord.bot_token", "").strip()
    try:
        callback_port = int(settings.get("discord.callback_port", "") or 8080)
    except ValueError:
        callback_port = 8080

    guild_rows = await db.scalars(
        select(BotGuild).where(BotGuild.is_active.is_(True)).order_by(BotGuild.name)
    )
    guilds = []
    for guild in guild_rows.all():
        guild_data = _guild_to_dict(guild)
        guild_data.pop("pushed_at", None)
        guilds.append(guild_data)

    config = {
        "remote": {
            "callback_url": settings.get("discord.callback_url") or None,
            "callback_port": callback_port,
            "command_prefix": settings.get("discord.command_prefix") or "!",
        },
        "guilds": guilds,
    }
    config_payload = json.dumps(config, sort_keys=True, separators=(",", ":"))
    current_config_revision = hashlib.sha256(config_payload.encode()).hexdigest()
    current_token_revision = hmac.new(
        get_settings().admin_key.encode(), token.encode(), hashlib.sha256
    ).hexdigest()

    changes: dict = {
        "ok": True,
        "changed": False,
        "config_revision": current_config_revision,
        "token_revision": current_token_revision,
    }
    response.headers["Cache-Control"] = "no-store"
    if config_revision != current_config_revision:
        changes["config"] = config
    if token_revision != current_token_revision:
        changes["discord_token"] = token or None

    changes["changed"] = "config" in changes or "discord_token" in changes
    return changes


@router.post("/guilds/sync")
async def sync_bot_guilds(
    body: GuildSyncRequest,
    auth: str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    now = datetime.now(timezone.utc)
    rows = await db.scalars(select(BotGuild))
    for row in rows.all():
        row.is_active = False

    legacy_keys = (
        "discord.guild_id",
        "discord.staff_alert_channel_id",
        "discord.verified_role_id",
        "discord.owner_role_id",
        "discord.admin_role_id",
        "discord.moderator_role_id",
        "discord.helper_role_id",
    )
    setting_rows = await db.execute(
        select(Setting.key, Setting.value).where(Setting.key.in_(legacy_keys))
    )
    legacy_settings = dict(setting_rows.all())
    legacy_guild_id = legacy_settings.get("discord.guild_id", "")

    synced: list[BotGuild] = []
    for item in body.guilds:
        guild_id = item.guild_id.strip()
        if not guild_id.isdecimal():
            raise HTTPException(status_code=422, detail="guild_id must be numeric")

        guild = await db.get(BotGuild, guild_id)
        if guild is None:
            is_legacy_guild = guild_id == legacy_guild_id
            guild = BotGuild(
                guild_id=guild_id,
                name=item.name,
                channels="[]",
                roles="[]",
                staff_alert_channel_id=(
                    legacy_settings.get("discord.staff_alert_channel_id")
                    if is_legacy_guild
                    else None
                ),
                verified_role_id=(
                    legacy_settings.get("discord.verified_role_id")
                    if is_legacy_guild
                    else None
                ),
                owner_role_id=(
                    legacy_settings.get("discord.owner_role_id")
                    if is_legacy_guild
                    else None
                ),
                admin_role_id=(
                    legacy_settings.get("discord.admin_role_id")
                    if is_legacy_guild
                    else None
                ),
                moderator_role_id=(
                    legacy_settings.get("discord.moderator_role_id")
                    if is_legacy_guild
                    else None
                ),
                helper_role_id=(
                    legacy_settings.get("discord.helper_role_id")
                    if is_legacy_guild
                    else None
                ),
            )
            db.add(guild)

        guild.name = item.name
        guild.channels = json.dumps([channel.model_dump() for channel in item.channels])
        guild.roles = json.dumps([role.model_dump() for role in item.roles])
        channel_ids = {channel.id for channel in item.channels}
        role_ids = {role.id for role in item.roles if not role.is_default}
        if guild.staff_alert_channel_id not in channel_ids:
            guild.staff_alert_channel_id = None
        for field in (
            "verified_role_id",
            "owner_role_id",
            "admin_role_id",
            "moderator_role_id",
            "helper_role_id",
        ):
            if getattr(guild, field) not in role_ids:
                setattr(guild, field, None)
        guild.is_active = True
        guild.pushed_at = now
        synced.append(guild)

    await db.commit()
    return {"guilds": [_guild_to_dict(guild) for guild in synced]}


@router.patch("/guilds/{guild_id}")
async def update_bot_guild_config(
    guild_id: str,
    body: GuildConfigPatch,
    _auth=Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> dict:
    guild = await db.get(BotGuild, guild_id)
    if guild is None or not guild.is_active:
        raise HTTPException(status_code=404, detail="Active Discord guild not found")

    channels = {channel["id"] for channel in json.loads(guild.channels)}
    roles = {
        role["id"]
        for role in json.loads(guild.roles)
        if not role.get("is_default", False)
    }
    role_fields = (
        "verified_role_id",
        "owner_role_id",
        "admin_role_id",
        "moderator_role_id",
        "helper_role_id",
    )
    for field in body.model_fields_set:
        value = getattr(body, field)
        if not value:
            setattr(guild, field, None)
            continue
        allowed_ids = channels if field == "staff_alert_channel_id" else roles
        if value not in allowed_ids:
            kind = "channel" if field == "staff_alert_channel_id" else "role"
            raise HTTPException(
                status_code=422,
                detail=f"{field} must identify a {kind} in this guild",
            )
        if field in role_fields or field == "staff_alert_channel_id":
            setattr(guild, field, value)

    await db.commit()
    await db.refresh(guild)
    return _guild_to_dict(guild)
