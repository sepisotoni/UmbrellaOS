"""Dashboard-specific endpoints — server/plugin mesh status."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.plugin_heartbeat import PluginHeartbeat
from services.settings_service import SettingsService
from api.dependencies.permissions import require_permission

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/servers")
async def list_servers(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("players.view")),
) -> list[dict]:
    """List Minecraft servers from plugin heartbeats."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=3)
    maintenance = await SettingsService.get_value(db, "server.maintenance_mode")
    in_maintenance = maintenance == "true"
    result = await db.execute(
        select(PluginHeartbeat).where(PluginHeartbeat.last_seen >= cutoff)
    )
    servers = []
    for hb in result.scalars().all():
        online = hb.last_seen >= cutoff and not in_maintenance
        status = "maintenance" if in_maintenance else ("online" if online else "offline")
        servers.append({
            "id": hb.server_id,
            "name": hb.server_name,
            "status": status,
            "tps": round(hb.tps, 1),
            "players": hb.online_count,
            "maxPlayers": 100,
            "ramUsedMb": 0,
            "ramTotalMb": 0,
            "cpu": 0,
            "version": hb.version,
            "pluginsConnected": 1 if hb.grim_connected else 0,
            "pluginsTotal": 2,
        })
    return servers


@router.get("/plugins")
async def list_plugins(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("players.view")),
) -> list[dict]:
    """List UmbrellaOS + GrimAC connection status, one entry per server.

    FIX ([PLUGIN] subsystem audit): previously returned a flat list of
    independent "plugin" rows (one for UmbrellaOS, a SEPARATE optional
    one for GrimAC per server) with lowercase-only status: "connected"
    and no umbrella_status/grimac_status fields at all. The dashboard's
    PluginsView.tsx / api.ts already expects ONE combined object per
    server with BOTH umbrella_status and grimac_status as sibling fields
    (checked against the literal string 'ACTIVE' to control status-badge
    color) -- confirmed by reading api.ts's field-mapping fallback chains
    and PluginsView.tsx's conditional styling directly, not assumed.

    The old shape meant the UmbrellaOS Bridge badge ALWAYS rendered red/
    disconnected on this page (the real "connected" string never equals
    'ACTIVE') even for genuinely healthy, actively-heartbeating servers,
    and the GrimAC Hook badge ALWAYS rendered green/active regardless of
    whether Grim was actually connected on that server (the field was
    never populated by real data at all, so the frontend's hardcoded
    'ACTIVE' fallback always won) -- a monitoring page showing the
    opposite of the true state for one signal and a permanently-false-
    positive for the other. Confirmed via grep that getPluginsHeartbeat()
    in api.ts is this endpoint's only caller anywhere in the codebase, so
    this reshape has no other consumer to break.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=3)
    result = await db.execute(
        select(PluginHeartbeat).where(PluginHeartbeat.last_seen >= cutoff)
    )
    plugins = []
    for hb in result.scalars().all():
        plugins.append({
            "server_id": hb.server_id,
            "server_name": hb.server_name,
            "umbrella_status": "ACTIVE",
            "umbrella_version": hb.plugin_version,
            "grimac_status": "ACTIVE" if hb.grim_connected else "STANDALONE",
            "last_heartbeat": hb.last_seen.isoformat(),
        })
    return plugins
