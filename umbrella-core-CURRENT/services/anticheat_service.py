"""Anticheat flag handling — Grim integration via Umbrella plugin."""
import asyncio
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
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
    check_name: str,
    verbose: str,
    vl: int,
    username: str,
    prior_punishments: int,
) -> tuple[float, str]:
    """Call Claude to assess how likely this flag is a real cheat vs false positive.
    Returns (confidence 0.0-1.0, short_reason).
    Falls back to VL-math if the API call fails."""
    import httpx, os, json
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return min(0.95, 0.5 + vl * 0.05), "vl_math_fallback"

    prompt = (
        f"You are an anticheat analyst for a Minecraft server.\n"
        f"A player named {username!r} was flagged by GrimAC.\n"
        f"Check: {check_name}\nVerbose: {verbose}\nVL: {vl}\n"
        f"Prior punishments on record: {prior_punishments}\n\n"
        f"Rate the likelihood this is a REAL cheat (not a false positive) from 0.0 to 1.0.\n"
        f"Reply ONLY with a JSON object: {{\"confidence\": <float>, \"reason\": \"<one sentence>\"}}"
    )
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 80,
                      "messages": [{"role": "user", "content": prompt}]},
            )
            data = resp.json()
            text = data["content"][0]["text"].strip()
            parsed = json.loads(text)
            conf = float(parsed.get("confidence", 0.5))
            reason = str(parsed.get("reason", ""))
            return max(0.0, min(1.0, conf)), reason
    except Exception as e:
        return min(0.95, 0.5 + vl * 0.05), f"ai_error:{e}"


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
    tempban_hours  = await _int_setting(db, "anticheat.tempban_hours", 24)
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

    # AI confidence review — calls Claude to assess real-cheat likelihood.
    # Falls back to VL-math if the API key is absent or the call fails.
    # Run before the AITask write so the confidence is stored immediately
    # rather than being overwritten by a background job later (DEAD-1 fix).
    ai_confidence, ai_reason = await _ai_confidence_review(
        check_name, verbose, vl, username or player_uuid, prior_count
    )

    # --- Retain AITask write for audit history and tempban context ---
    task = AITask(
        task_type="anticheat_review",
        status="completed",
        player_uuid=player_uuid,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        ai_summary=f"Grim flagged {username or player_uuid} for {check_name} (VL {vl}) — action: {action}. AI: {ai_reason}",
        ai_recommendation="warn" if action == "warn" else ("kick" if action == "kick" else "confirm_tempban"),
        ai_confidence=ai_confidence,
        evidence=verbose[:2000],
    )
    db.add(task)
    await db.flush()

    return {
        "processed": True,
        "action": action,          # "warn" | "kick" | "tempban"
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
        "notify_staff": True,      # always notify — plugin decides channel/method
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
