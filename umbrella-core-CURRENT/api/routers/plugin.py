"""
api/routers/plugin.py — Plugin-facing endpoints.

All routes here require X-Plugin-Key authentication.
The Minecraft plugin calls these on startup and periodically for heartbeat.

Phase 1:
    GET /api/v1/plugin/health  — authenticated heartbeat

Phase 2 (Client Config Integration):
    GET /api/v1/plugin/config  — non-sensitive settings bundle for plugin consumption

Phase 8 will expand with:
    POST /api/v1/events/player-join  — join check (verification, bans)
    POST /api/v1/events/batch        — bulk event ingestion for replay buffer
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, delete, func
from datetime import datetime, timezone
from database import get_db
from models.setting import Setting
from models.plugin_heartbeat import PluginHeartbeat
from models.plugin_command import PluginCommand
from models.player import Punishment
from models.plugin_console_line import PluginConsoleLine
from api.middleware.auth import require_plugin_key, require_admin_hmac_or_session
from api.schemas.plugin_control import PluginControlRequest

router = APIRouter(prefix="/api/v1/plugin", tags=["plugin"])

# Punishment types that block a player from joining. Mirrors the check
# constraint in ck_punishments_type (warn/mute/tempban/ban) — only the
# two ban variants are join-blocking; warn/mute are not.
_BAN_TYPES = ("ban", "tempban")


class ActivePunishmentSchema(BaseModel):
    id: str
    type: str
    reason: str
    staff_id: str | None
    created_at: datetime
    expires_at: datetime | None
    ban_ip_address: str | None = None  # Set for type='ipban'; None for player bans

    class Config:
        from_attributes = True


class ActiveBanCheckResponse(BaseModel):
    banned: bool
    punishment: ActivePunishmentSchema | None = None


class HeartbeatRequest(BaseModel):
    server_id: str | None = None
    server_name: str = "Minecraft Server"
    online_count: int = 0
    tps: float = 20.0
    version: str = "unknown"
    plugin_version: str = "1.0.0"
    grim_connected: bool = False


@router.get("/health")
async def plugin_health(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_plugin_key),
) -> dict:
    """
    Authenticated heartbeat for the Minecraft plugin.

    The plugin calls this endpoint periodically to:
      1. Confirm its API key is still valid (401 = key rotated, reconnect refused).
      2. Confirm Core and its database are reachable.
      3. Receive the canonical Core version for compatibility checks.

    Returns 200 on success, 401 on bad/missing key, 200 degraded if DB is down.
    """
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if db_ok else "degraded",
        "version": "1.0.0",
        "database": "connected" if db_ok else "unreachable",
        "service": "umbrella-core",
        "client": "plugin",
    }


@router.post("/heartbeat")
async def plugin_heartbeat_post(
    body: HeartbeatRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_plugin_key),
) -> dict:
    """Record plugin heartbeat for dashboard server/plugin views."""
    server_id = body.server_id or "default"
    hb = await db.scalar(select(PluginHeartbeat).where(PluginHeartbeat.server_id == server_id))
    now = datetime.now(timezone.utc)
    if hb is None:
        hb = PluginHeartbeat(
            server_id=server_id,
            server_name=body.server_name,
            online_count=body.online_count,
            tps=body.tps,
            version=body.version,
            plugin_version=body.plugin_version,
            grim_connected=body.grim_connected,
            last_seen=now,
        )
        db.add(hb)
    else:
        hb.server_name = body.server_name
        hb.online_count = body.online_count
        hb.tps = body.tps
        hb.version = body.version
        hb.plugin_version = body.plugin_version
        hb.grim_connected = body.grim_connected
        hb.last_seen = now
    await db.flush()
    return {"ok": True, "server_id": server_id}


@router.get("/config")
async def plugin_config(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_plugin_key),
) -> dict:
    """
    Non-sensitive settings bundle for the Minecraft plugin.

    Returns all settings where sensitive=False as a flat key→value map
    alongside a grouped-by-category view. The plugin fetches this once on
    startup and after any reconnect to Core.

    Sensitive settings (tokens, passwords, API keys) are never included —
    the plugin has no need for them and including them would widen the
    attack surface if a plugin server were compromised.

    Response shape:
        {
            "settings": {"server.name": "UmbrellaMC", "rcon.host": "localhost", ...},
            "by_category": {
                "server":      {"server.name": "UmbrellaMC", "server.max_players": "50"},
                "rcon":        {"rcon.host": "localhost", "rcon.port": "25575"},
                "moderation":  {"moderation.require_discord_link": "true", ...},
                "sync":        {"sync.mutes_interval_seconds": "30", ...},
            }
        }
    """
    result = await db.execute(
        select(Setting)
        .where(Setting.sensitive == False)  # noqa: E712 — SQLAlchemy requires == not 'is'
        .order_by(Setting.category, Setting.key)
    )
    rows = result.scalars().all()

    flat: dict[str, str] = {}
    by_category: dict[str, dict[str, str]] = {}

    for row in rows:
        flat[row.key] = row.value
        by_category.setdefault(row.category, {})[row.key] = row.value

    return {
        "settings": flat,
        "by_category": by_category,
    }


@router.get("/punishments/{player_uuid}/active", response_model=ActiveBanCheckResponse)
async def plugin_active_punishment_check(
    player_uuid: str,
    ip: str | None = Query(default=None, description="Connecting player IP — used to check ipban records"),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_plugin_key),
) -> ActiveBanCheckResponse:
    """
    Ban-check for the Minecraft plugin — read-only, plugin-key authorized.

    Phase 13 Step 2. Added because the only existing "is this player
    banned" endpoint (GET /api/v1/punishments) requires real RBAC
    (punishments.view via require_permission), not the plugin-key auth
    every other plugin-facing endpoint uses — the plugin has no user/role
    identity to present. This mirrors that same auth pattern instead of
    inventing a service-account concept (the scoping doc's rejected
    option 2).

    Returns the single most relevant active ban/tempban for the player,
    if any — permanent bans (expires_at is null) take priority over a
    tempban, since that's the one that actually determines whether the
    player can ever rejoin. Mutes and warns are intentionally excluded;
    they don't block a join.

    Migration 041 made punishments.player_uuid nullable for IP-level bans
    (type='ipban'). The optional ?ip= parameter allows the plugin to also
    check whether the connecting IP is banned — without it, ipbans would
    be silently unenforced after the migration.
    """
    now = datetime.now(timezone.utc)

    # --- Check player-specific bans (ban, tempban) ---
    result = await db.execute(
        select(Punishment)
        .where(Punishment.player_uuid == player_uuid)
        .where(Punishment.active == True)  # noqa: E712
        .where(Punishment.type.in_(_BAN_TYPES))
        .where(
            (Punishment.expires_at == None)  # noqa: E711
            | (Punishment.expires_at > now)
        )
        .order_by(Punishment.expires_at.is_(None).desc(), Punishment.created_at.desc())
    )
    punishment = result.scalars().first()

    if punishment is not None:
        return ActiveBanCheckResponse(
            banned=True,
            punishment=ActivePunishmentSchema.model_validate(punishment),
        )

    # --- Check IP-level bans if IP was provided ---
    if ip:
        ip_result = await db.execute(
            select(Punishment)
            .where(Punishment.ban_ip_address == ip)
            .where(Punishment.type == "ipban")
            .where(Punishment.active == True)  # noqa: E712
            .where(
                (Punishment.expires_at == None)  # noqa: E711
                | (Punishment.expires_at > now)
            )
            .order_by(Punishment.created_at.desc())
        )
        ip_ban = ip_result.scalars().first()
        if ip_ban is not None:
            return ActiveBanCheckResponse(
                banned=True,
                punishment=ActivePunishmentSchema.model_validate(ip_ban),
            )

    return ActiveBanCheckResponse(banned=False, punishment=None)


@router.post("/control", status_code=202)
async def plugin_control(
    body: PluginControlRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_plugin_key),
) -> dict:
    """
    Send a control command to a specific Minecraft plugin instance.

    NOT CURRENTLY FUNCTIONAL — [PLUGIN] subsystem audit. This endpoint
    writes a PluginCommand row (status="pending") but nothing anywhere in
    this codebase ever reads it: not the Minecraft plugin's CommandPoller
    (which only polls the unrelated mc_commands table — see
    api/routers/mc_commands.py), not the sandboxed-plugin execution system
    in services/plugins/, not the dashboard, not a test. Confirmed via
    full-repo grep for both "PluginCommand" and "/control" before writing
    this note. Before this fix, calling this endpoint returned
    {"ok": True, "command_id": ...} — a false-success response implying an
    action would actually happen, when nothing was ever going to read that
    row or act on it. plugin_name + a reload/toggle action strongly
    suggests this was designed for the sandboxed third-party plugin system
    (services/plugins/, capabilities/marketplace.py) rather than the
    single Bukkit plugin this router otherwise serves, but no consumer
    exists for either interpretation. Left the write behavior in place
    (so the historical PluginCommand row still gets created for whoever
    eventually builds the real consumer) but stopped claiming success —
    now returns 202 Accepted with an explicit note, rather than 200 OK
    implying completion. Flagged in coordination for whoever has design
    context on which system this was meant to control.
    """
    command = PluginCommand(
        plugin_name=body.plugin_name,
        action=body.action,
        status="pending",
    )
    db.add(command)
    await db.flush()
    return {
        "ok": True,
        "command_id": command.id,
        "status": "pending",
        "note": (
            "This command has been recorded but nothing currently polls or "
            "executes PluginCommand rows — no system consumes this queue yet. "
            "It will remain 'pending' indefinitely."
        ),
    }


# ---------------------------------------------------------------------------
# Console line push/pull — plugin pushes batches, dashboard polls to read.
# ---------------------------------------------------------------------------

_CONSOLE_CAP = 500  # max lines kept per server_id


class ConsoleLinesPayload(BaseModel):
    lines: list[str]


class ConsoleLineRecord(BaseModel):
    ts: str  # ISO 8601 of captured_at
    line: str


class RecentConsoleResponse(BaseModel):
    server_id: str
    lines: list[ConsoleLineRecord]


@router.post("/servers/{server_id}/console/lines")
async def push_console_lines(
    server_id: str,
    payload: ConsoleLinesPayload,
    _auth: str = Depends(require_plugin_key),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Plugin pushes batches of console lines here.  Core stores them, capped
    at 500 per server_id — oldest rows are deleted when over the cap.
    """
    now = datetime.now(timezone.utc)

    # Bulk-insert new lines
    new_rows = [
        PluginConsoleLine(server_id=server_id, line=line, captured_at=now)
        for line in payload.lines
        if line  # skip empty strings
    ]
    if new_rows:
        db.add_all(new_rows)
        await db.flush()

        # Trim to cap: keep the newest _CONSOLE_CAP rows, delete the rest.
        count_result = await db.execute(
            select(func.count(PluginConsoleLine.id)).where(
                PluginConsoleLine.server_id == server_id
            )
        )
        total = count_result.scalar_one()

        if total > _CONSOLE_CAP:
            # Find the id of the (_CONSOLE_CAP + 1)-th newest row — everything
            # older than that gets deleted.
            cutoff_result = await db.execute(
                select(PluginConsoleLine.id)
                .where(PluginConsoleLine.server_id == server_id)
                .order_by(PluginConsoleLine.captured_at.desc())
                .offset(_CONSOLE_CAP)
                .limit(1)
            )
            cutoff_id = cutoff_result.scalar_one_or_none()
            if cutoff_id is not None:
                await db.execute(
                    delete(PluginConsoleLine).where(
                        PluginConsoleLine.server_id == server_id,
                        PluginConsoleLine.id <= cutoff_id,
                    )
                )

    return {"ok": True, "stored": len(new_rows)}


@router.get("/servers/{server_id}/console/recent", response_model=RecentConsoleResponse)
async def get_recent_console(
    server_id: str,
    n: int = Query(default=100, ge=1, le=500),
    _auth: str = Depends(require_admin_hmac_or_session),
    db: AsyncSession = Depends(get_db),
) -> RecentConsoleResponse:
    """
    Return the N most recent console lines for this server.
    Accepts plugin key, admin key, HMAC, or a valid dashboard session token
    so both the dashboard and the plugin can call it.
    Lines are returned in chronological order (oldest first within the N).
    """
    result = await db.execute(
        select(PluginConsoleLine)
        .where(PluginConsoleLine.server_id == server_id)
        .order_by(PluginConsoleLine.captured_at.desc())
        .limit(n)
    )
    rows = result.scalars().all()
    # rows are newest-first; reverse for chronological output
    rows = list(reversed(rows))

    return RecentConsoleResponse(
        server_id=server_id,
        lines=[
            ConsoleLineRecord(ts=row.captured_at.isoformat(), line=row.line)
            for row in rows
        ],
    )
