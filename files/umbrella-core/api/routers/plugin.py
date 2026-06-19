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
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from datetime import datetime, timezone
from database import get_db
from models.setting import Setting
from models.plugin_heartbeat import PluginHeartbeat
from models.plugin_command import PluginCommand
from api.middleware.auth import require_plugin_key
from api.schemas.plugin_control import PluginControlRequest

router = APIRouter(prefix="/api/v1/plugin", tags=["plugin"])


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


@router.post("/control")
async def plugin_control(
    body: PluginControlRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_plugin_key),
) -> dict:
    """
    Send a control command to a specific Minecraft plugin instance.
    """
    command = PluginCommand(
        plugin_name=body.plugin_name,
        action=body.action,
        status="pending",
    )
    db.add(command)
    await db.flush()
    return {"ok": True, "command_id": command.id}
