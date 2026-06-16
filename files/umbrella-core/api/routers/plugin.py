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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from database import get_db
from models.setting import Setting
from api.middleware.auth import require_plugin_key

router = APIRouter(prefix="/api/v1/plugin", tags=["plugin"])


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
