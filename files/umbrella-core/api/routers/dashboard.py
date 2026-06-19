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
    """List connected plugins (Umbrella + Grim status per server)."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=3)
    result = await db.execute(
        select(PluginHeartbeat).where(PluginHeartbeat.last_seen >= cutoff)
    )
    plugins = []
    for hb in result.scalars().all():
        ms = int((datetime.now(timezone.utc) - hb.last_seen).total_seconds() * 1000)
        plugins.append({
            "id": f"umbrella-{hb.server_id}",
            "name": "UmbrellaOS",
            "version": hb.plugin_version,
            "server": hb.server_name,
            "status": "connected",
            "heartbeatMs": ms,
            "lastSeen": hb.last_seen.isoformat(),
        })
        if hb.grim_connected:
            plugins.append({
                "id": f"grim-{hb.server_id}",
                "name": "GrimAC",
                "version": "2.3.x",
                "server": hb.server_name,
                "status": "connected",
                "heartbeatMs": ms,
                "lastSeen": hb.last_seen.isoformat(),
            })
    return plugins
