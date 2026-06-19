"""Anticheat flag handling — Grim integration via Umbrella plugin."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import AITask, Player, Punishment, ReplaySession
from services.settings_service import SettingsService


async def _bool_setting(db: AsyncSession, key: str, default: bool = False) -> bool:
    val = await SettingsService.get_value(db, key)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes")


async def _int_setting(db: AsyncSession, key: str, default: int) -> int:
    val = await SettingsService.get_value(db, key)
    try:
        return int(val) if val else default
    except ValueError:
        return default


async def handle_cheat_flag(
    db: AsyncSession,
    player_uuid: str,
    username: str,
    check_name: str,
    verbose: str,
    vl: int = 0,
) -> dict:
    """Process a Grim anticheat flag: optional tempban, AI review task, replay session."""
    enabled = await _bool_setting(db, "anticheat.enabled", False)
    if not enabled:
        return {"processed": False, "reason": "anticheat_disabled"}

    player = await db.scalar(select(Player).where(Player.uuid == player_uuid))
    if player is None:
        player = Player(uuid=player_uuid, username=username or "Unknown")
        db.add(player)
        await db.flush()
    elif username and player.username != username:
        player.username = username

    auto_tempban = await _bool_setting(db, "anticheat.auto_tempban", True)
    tempban_hours = await _int_setting(db, "anticheat.tempban_hours", 24)
    reason = f"[Grim] {check_name}: {verbose}"[:500]

    punishment_id = None
    if auto_tempban:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=tempban_hours)
        punishment = Punishment(
            player_uuid=player_uuid,
            staff_id=None,
            type="tempban",
            reason=reason,
            expires_at=expires_at,
            active=True,
        )
        db.add(punishment)
        await db.flush()
        punishment_id = punishment.id

    replay = ReplaySession(
        trigger="anticheat",
        triggered_by="grim",
        minecraft_uuid=player_uuid,
        started_at=datetime.now(timezone.utc),
        incident_at=datetime.now(timezone.utc),
        notes=f"{check_name} VL={vl}: {verbose}"[:1000],
    )
    db.add(replay)
    await db.flush()

    task = AITask(
        task_type="anticheat_review",
        status="pending",
        player_uuid=player_uuid,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        ai_summary=f"Grim flagged {username or player_uuid} for {check_name} (VL {vl})",
        ai_recommendation="review" if not auto_tempban else "confirm_tempban",
        ai_confidence=min(0.95, 0.5 + vl * 0.05),
        evidence=verbose[:2000],
    )
    db.add(task)
    await db.flush()

    return {
        "processed": True,
        "punishment_id": punishment_id,
        "tempban": auto_tempban,
        "replay_id": replay.id,
        "ai_task_id": task.id,
        "kick": auto_tempban,
    }
