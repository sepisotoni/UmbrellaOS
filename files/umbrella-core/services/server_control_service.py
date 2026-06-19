"""Secure server process control via configured commands (no shell injection)."""
import asyncio
import shlex
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.plugin_heartbeat import PluginHeartbeat
from services.settings_service import SettingsService

ALLOWED_ACTIONS = frozenset({"power", "restart", "maintenance"})
ACTION_CMD_KEYS = {
    "power_off": "server.control.stop_cmd",
    "power_on": "server.control.start_cmd",
    "restart": "server.control.restart_cmd",
}
COMMAND_TIMEOUT_SEC = 60


class ServerControlError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def _validate_server(db: AsyncSession, server_id: str) -> PluginHeartbeat | None:
    """Return heartbeat row if known; allow control when registry is empty."""
    hb = await db.scalar(select(PluginHeartbeat).where(PluginHeartbeat.server_id == server_id))
    if hb is not None:
        return hb
    any_hb = await db.scalar(select(PluginHeartbeat).limit(1))
    if any_hb is None:
        return None
    raise ServerControlError(f"Unknown server_id '{server_id}'", 404)


async def _run_configured_command(db: AsyncSession, setting_key: str) -> dict:
    cmd_raw = await SettingsService.get_value(db, setting_key)
    if not cmd_raw or not cmd_raw.strip():
        raise ServerControlError(
            f"Command not configured — set {setting_key} in Settings",
            503,
        )

    try:
        args = shlex.split(cmd_raw, posix=False)
    except ValueError as exc:
        raise ServerControlError(f"Invalid command syntax: {exc}") from exc

    if not args:
        raise ServerControlError("Configured command is empty")

    workdir = await SettingsService.get_value(db, "server.control.workdir")

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=workdir or None,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=COMMAND_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        proc.kill()
        raise ServerControlError("Command timed out", 504) from None

    return {
        "exit_code": proc.returncode,
        "stdout": (stdout or b"").decode(errors="replace")[-2000:],
        "stderr": (stderr or b"").decode(errors="replace")[-2000:],
        "command": args[0],
    }


async def execute_server_control(
    db: AsyncSession,
    server_id: str,
    action: Literal["power", "restart", "maintenance"],
    *,
    enabled: bool | None = None,
    actor: str = "dashboard",
) -> dict:
    if action not in ALLOWED_ACTIONS:
        raise ServerControlError(f"Invalid action '{action}'")

    await _validate_server(db, server_id)

    if action == "maintenance":
        current = await SettingsService.get_value(db, "server.maintenance_mode")
        new_val = ("true" if enabled else "false") if enabled is not None else (
            "false" if current == "true" else "true"
        )
        await SettingsService.update(
            db, "server.maintenance_mode", new_val, actor=actor, actor_type="staff",
        )
        return {
            "server_id": server_id,
            "action": "maintenance",
            "maintenance": new_val == "true",
            "success": True,
        }

    if action == "restart":
        result = await _run_configured_command(db, ACTION_CMD_KEYS["restart"])
    else:
        key = ACTION_CMD_KEYS["power_on"] if enabled else ACTION_CMD_KEYS["power_off"]
        result = await _run_configured_command(db, key)

    success = result.get("exit_code", 1) == 0
    return {
        "server_id": server_id,
        "action": action,
        "enabled": enabled,
        "success": success,
        **result,
    }
