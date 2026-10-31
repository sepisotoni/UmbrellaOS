"""Anticheat flag handling — Grim integration via Umbrella plugin."""

from datetime import datetime, timedelta, timezone
from math import isfinite

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import delete, select

from config import get_settings
from models import AITask, Player, Punishment, ReplaySession
from models.anticheat_violation import AnticheatViolation
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


async def _ai_confidence_review(
    db: AsyncSession,
    check_name: str,
    verbose: str,
    vl: int,
    username: str,
    prior_punishments: int,
) -> tuple[float, str]:
    """Assess GrimAC evidence through the configured AI model router.

    If no provider is available or it produces invalid JSON, preserve the
    historical deterministic VL-based fallback and never fake an AI result.
    """
    from services.ai.orchestrator import Orchestrator

    instructions = (
        "You are a Minecraft anticheat analyst. Assess whether the flag "
        "represents a real cheat rather than a false positive. Reply ONLY "
        "with a JSON object containing a numeric confidence between 0 and 1 "
        "and a one-sentence reason."
    )
    evidence = (
        f"Player: {username}\n"
        f"Check: {check_name}\nVerbose: {verbose}\nVL: {vl}\n"
        f"Prior punishments: {prior_punishments}"
    )
    try:
        result = await Orchestrator.run(
            db=db,
            task_type="moderation_review",
            task_prompt=evidence,
            system_instructions=instructions,
            requested_by="grim_anticheat",
            require_dual_review=False,
        )
        import json

        parsed = json.loads(result.text)
        conf = float(parsed.get("confidence", 0.5))
        if not isfinite(conf):
            raise ValueError("non-finite AI confidence")
        reason = str(parsed.get("reason", ""))
        return max(0.0, min(1.0, conf)), reason
    except SQLAlchemyError:
        # A broken transaction cannot be safely hidden by a model fallback.
        raise
    except Exception:
        # AI remains advisory: a provider outage must not break the flag API.
        return min(0.95, 0.5 + vl * 0.05), "vl_math_fallback"

async def handle_cheat_flag(
    db: AsyncSession,
    player_uuid: str,
    username: str,
    check_name: str,
    verbose: str,
    vl: int = 0,
    server_id: str | None = None,
) -> dict:
    """Process a Grim anticheat flag with severity tiers based on VL.

    Tiers (all configurable in Settings):
      VL < anticheat.warn_vl_threshold  (default 10)  -> warn only
      VL < anticheat.kick_vl_threshold  (default 30)  -> kick
      VL >= anticheat.kick_vl_threshold                -> tempban

    Now writes to both AnticheatViolation (new dedicated table) and AITask
    (retained for backward-compatible audit history and tempban tracking).
    The server_id parameter is forwarded from the plugin payload — may be
    None for old plugin versions that pre-date the Task 5 update.
    """
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

    warn_threshold = await _int_setting(db, "anticheat.warn_vl_threshold", 10)
    kick_threshold = await _int_setting(db, "anticheat.kick_vl_threshold", 30)
    tempban_hours = await _int_setting(db, "anticheat.tempban_hours", 24)
    reason = f"[Grim] {check_name}: {verbose}"[:500]

    # Determine action tier
    if vl < warn_threshold:
        action = "warn"
    elif vl < kick_threshold:
        action = "kick"
    else:
        action = "tempban"

    punishment_id = None
    if action == "tempban":
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

    # --- Write to dedicated AnticheatViolation table (P15 Task 3) ---
    violation = AnticheatViolation(
        player_uuid=player_uuid,
        player_name=username or player_uuid,
        server_id=server_id or None,
        check_name=check_name,
        verbose=verbose[:2000] if verbose else "",
        vl=vl,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(violation)
    await db.flush()

    # Count prior punishments for AI context
    prior_punishments_result = await db.execute(
        select(Punishment).where(Punishment.player_uuid == player_uuid)
    )
    prior_count = len(prior_punishments_result.scalars().all())

    # AI confidence review uses the configured moderation_review provider.
    # Run before AITask persistence, with deterministic fallback on failure.
    ai_confidence, ai_reason = await _ai_confidence_review(
        db, check_name, verbose, vl, username or player_uuid, prior_count
    )

    # --- Retain AITask write for audit history and tempban context ---
    task = AITask(
        task_type="anticheat_review",
        status="completed",
        player_uuid=player_uuid,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        ai_summary=f"Grim flagged {username or player_uuid} for {check_name} (VL {vl}) — action: {action}. AI: {ai_reason}",
        ai_recommendation="warn"
        if action == "warn"
        else ("kick" if action == "kick" else "confirm_tempban"),
        ai_confidence=ai_confidence,
        evidence=verbose[:2000],
    )
    db.add(task)
    await db.flush()

    return {
        "processed": True,
        "action": action,  # "warn" | "kick" | "tempban"
        "punishment_id": punishment_id,
        "tempban": action == "tempban",
        "kick": action in ("kick", "tempban"),
        "warn": action == "warn",
        "reason": reason,
        "vl": vl,
        "check_name": check_name,
        "username": username or player_uuid,
        "replay_id": replay.id,
        "ai_task_id": task.id,
        "violation_id": violation.id,
        "notify_staff": True,  # always notify — plugin decides channel/method
    }


async def purge_old_violations(db: AsyncSession) -> int:
    """
    Sweeps anticheat_violations older than
    settings.anticheat_violation_retention_days. Mirrors
    services/operational_intelligence/metrics.py::purge_old_snapshots —
    same reasoning: an unbounded, ever-growing security/audit log for
    every GrimAC flag ever forwarded by the plugin would otherwise
    accumulate forever with no cap. Intended to be called periodically
    via a Schedule pointing at the
    anticheat.violations.purge_old capability
    (capabilities/anticheat_maintenance.py), the same
    scheduler-driven pattern as everything else in this codebase that
    needs a recurring maintenance task — no bespoke background loop.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(
        days=get_settings().anticheat_violation_retention_days
    )
    stmt = delete(AnticheatViolation).where(AnticheatViolation.timestamp < cutoff)
    result = await db.execute(stmt)
    return result.rowcount
