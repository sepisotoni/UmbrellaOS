"""
services/ai_service.py — AI moderation review service.

Uses the ModelRouter/ProviderFactory/Orchestrator stack (services/ai/) so
that provider routing, key loading, health tracking, and failover all work
correctly — the same path every other AI feature uses.

Previously this file made direct httpx calls to the Anthropic API with a
hardcoded model string, completely bypassing the routing layer.  That meant:
- ai.openrouter_enabled / ai.gemini_enabled settings had no effect
- Rotating the API key in the dashboard did nothing until a restart (it
  re-read the key on startup only in the old code)
- No failover: one provider down = all reviews fail
- ai_model_configs health tracking was never updated for review calls

AI is NEVER called automatically.  These functions are only invoked when staff
explicitly clicks "AI Review" from the dashboard.  See PHASE15-SPEC §Important
Constraint — AI is On-Demand Only.

On any AI failure: raise AIServiceError (caller returns 503) — never fabricate
a result.
"""
import asyncio
import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import (
    AITask, Player, SuspicionEvent, Punishment, Appeal,
    AltGroup, AltGroupMember, DiscordAccount, ChatMessage,
)
from services.ai.orchestrator import Orchestrator
from services.ai.model_router import NoAvailableModelError

# AnticheatViolation is provided by Backend A.
try:
    from models.anticheat_violation import AnticheatViolation
    _HAS_ANTICHEAT = True
except ImportError:
    _HAS_ANTICHEAT = False


class AIServiceError(Exception):
    """Raised when AI service encounters an error."""
    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "unknown"
    return dt.strftime("%Y-%m-%d")


def _build_anticheat_summary(violations: list) -> str:
    """
    Build a structured GrimAC summary string from AnticheatViolation records.
    Collapses repeated checks. Target: under 200 tokens.
    """
    if not violations:
        return "No GrimAC flags in this window."

    by_check: dict[str, dict] = defaultdict(lambda: {"count": 0, "vl_sum": 0, "min_vl": 9999, "max_vl": 0})
    for v in violations:
        entry = by_check[v.check_name]
        entry["count"] += 1
        entry["vl_sum"] += v.vl
        if v.vl < entry["min_vl"]:
            entry["min_vl"] = v.vl
        if v.vl > entry["max_vl"]:
            entry["max_vl"] = v.vl

    lines = []
    for check_name, data in sorted(by_check.items(), key=lambda x: -x[1]["count"]):
        avg_vl = round(data["vl_sum"] / data["count"], 1)
        lines.append(
            f"- {check_name}: {data['count']} flags, "
            f"VL {data['min_vl']}-{data['max_vl']}, avg {avg_vl}"
        )
    return "\n".join(lines)


async def _orchestrate(
    db: AsyncSession,
    task_type: str,
    system_prompt: str,
    user_content: str,
    requested_by: str = "ai_service",
) -> dict:
    """
    Route a prompt through the Orchestrator (ModelRouter → ProviderFactory →
    provider.generate()) and parse the AI's JSON response.

    Uses task_type to select the correct AIModelConfig rows, so provider
    routing, key loading, health tracking, and failover all work.

    Raises AIServiceError on orchestrator failure or non-JSON response.
    """
    # The constitution's system prompt wraps the task prompt automatically
    # inside Orchestrator.run() via ConstitutionService.build_system_prompt().
    # For review tasks we supply a structured JSON-enforcing prompt as the
    # task prompt so the constitution appears before it in the final system
    # prompt (tier ordering: PLATFORM_SAFETY < CORE_PLATFORM < TASK).
    combined_prompt = f"{system_prompt}\n\n{user_content}"

    try:
        result = await Orchestrator.run(
            db=db,
            task_type=task_type,
            task_prompt=combined_prompt,
            requested_by=requested_by,
            require_dual_review=False,  # review tasks are staff-confirmed; no need for dual review
        )
    except NoAvailableModelError as exc:
        raise AIServiceError(
            f"No AI provider available for task_type={task_type!r}: {exc}"
        ) from exc
    except Exception as exc:
        raise AIServiceError(f"AI orchestrator error: {exc}") from exc

    content_text = result.text

    # Strip markdown fences if the model wraps its JSON
    clean = content_text.strip()
    if clean.startswith("```"):
        clean = clean.split("```", 2)[1]
        if clean.startswith("json"):
            clean = clean[4:]
        clean = clean.rsplit("```", 1)[0].strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        raise AIServiceError(
            f"AI returned non-JSON response: {content_text[:300]}"
        ) from exc


# ---------------------------------------------------------------------------
# P15 Task 5 — Player review with GrimAC history
# ---------------------------------------------------------------------------

async def review_flagged_player(
    player_uuid: str,
    db: AsyncSession,
) -> AITask:
    """
    AI review of a flagged player.

    Pulls:
    - Player record
    - AnticheatViolation records (last 30 days)
    - Punishment history
    - Suspicion events (last 10)

    Routes through the ModelRouter (provider_factory + health tracking)
    using task_type="moderation_review".  Raises AIServiceError on failure.
    """
    # Fetch player
    player = await db.scalar(select(Player).where(Player.uuid == player_uuid))
    if not player:
        raise AIServiceError(f"Player not found: {player_uuid}")

    cutoff_30d = datetime.now(tz=timezone.utc) - timedelta(days=30)

    # Parallel queries
    async def _fetch_punishments():
        result = await db.execute(
            select(Punishment)
            .where(Punishment.player_uuid == player_uuid)
            .order_by(Punishment.created_at.desc())
        )
        return list(result.scalars().all())

    async def _fetch_suspicion():
        result = await db.execute(
            select(SuspicionEvent)
            .where(SuspicionEvent.player_uuid == player_uuid)
            .order_by(SuspicionEvent.created_at.desc())
            .limit(10)
        )
        return list(result.scalars().all())

    async def _fetch_anticheat():
        if not _HAS_ANTICHEAT:
            return []
        result = await db.execute(
            select(AnticheatViolation)
            .where(
                AnticheatViolation.player_uuid == player_uuid,
                AnticheatViolation.timestamp >= cutoff_30d,
            )
            .order_by(AnticheatViolation.timestamp.desc())
        )
        return list(result.scalars().all())

    punishments, suspicion_events, violations = await asyncio.gather(
        _fetch_punishments(),
        _fetch_suspicion(),
        _fetch_anticheat(),
    )

    # Build punishment breakdown
    ptype_counts = Counter(p.type for p in punishments)
    punishment_breakdown = ", ".join(f"{v}x {k}" for k, v in ptype_counts.items()) or "none"

    # Build VL escalation timeline
    vl_milestones: list[str] = []
    for v in reversed(violations):  # chronological
        for threshold in (5, 10, 20, 50):
            if v.vl >= threshold:
                vl_milestones.append(
                    f"  VL≥{threshold} at {_fmt_dt(v.timestamp)} ({v.check_name})"
                )
                break

    # Notable verbose strings (up to 5, deduplicated)
    seen_verbose: set[str] = set()
    notable: list[str] = []
    for v in violations:
        vb = (getattr(v, "verbose", "") or "").strip()
        if vb and vb not in seen_verbose:
            seen_verbose.add(vb)
            notable.append(f"  {v.check_name}: {vb[:120]}")
        if len(notable) >= 5:
            break

    anticheat_section = _build_anticheat_summary(violations)

    context_str = f"""PLAYER REVIEW CONTEXT
=====================
Player: {player.username} ({player.uuid})
First seen: {_fmt_dt(player.first_seen)} | Last seen: {_fmt_dt(player.last_seen)}
Playtime: {player.playtime} minutes | Risk score: {player.risk_score} | Suspicion score: {player.suspicion_score}

GrimAC History (last 30 days):
- Total flags: {len(violations)}
- By check:
{anticheat_section}
{"- VL escalation milestones:" + chr(10) + chr(10).join(vl_milestones[:10]) if vl_milestones else "- No VL escalation milestones"}
{"- Notable flags:" + chr(10) + chr(10).join(notable) if notable else "- No notable verbose strings"}

Punishment History:
- {len(punishments)} total | {punishment_breakdown}
"""

    system_prompt = (
        "You are UmbrellaOS Player Risk Assessor for a Minecraft server.\n"
        "Analyze this player's anticheat data and history objectively.\n"
        "Return JSON only:\n"
        "{\n"
        '  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",\n'
        '  "confidence": 0.0-1.0,\n'
        '  "reasoning": "2-3 sentences",\n'
        '  "recommendation": "MONITOR|WARN|TEMP_BAN|PERMANENT_BAN|FALSE_POSITIVE",\n'
        '  "key_findings": ["list of specific concerning patterns"],\n'
        '  "mitigating_factors": ["list"]\n'
        "}"
    )

    ai_result = await _orchestrate(
        db, "moderation_review", system_prompt, context_str,
        requested_by=f"player_review:{player_uuid}",
    )

    # Build evidence blob for AITask
    evidence = {
        "player": {
            "uuid": player.uuid,
            "username": player.username,
            "risk_score": player.risk_score,
            "suspicion_score": player.suspicion_score,
        },
        "anticheat_flags_30d": len(violations),
        "punishment_count": len(punishments),
        "ai_result": ai_result,
    }

    recommendation = ai_result.get("recommendation", "MONITOR")
    confidence = float(ai_result.get("confidence", 0.5))
    reasoning = ai_result.get("reasoning", "")
    risk_level = ai_result.get("risk_level", "UNKNOWN")
    summary = f"[{risk_level}] {reasoning}"

    task = AITask(
        task_type="moderation_review",
        status="pending",
        player_uuid=player_uuid,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        ai_summary=summary[:500],
        ai_recommendation=recommendation,
        ai_confidence=confidence,
        evidence=json.dumps(evidence),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return task


# ---------------------------------------------------------------------------
# P15 Task 4 — Appeal review with full context
# ---------------------------------------------------------------------------

async def review_appeal(
    appeal_id: str,
    db: AsyncSession,
) -> AITask:
    """
    AI review of an appeal.

    Routes through the ModelRouter using task_type="appeal_review".
    Raises AIServiceError on failure — sets ai_review_status=FAILED and
    re-raises so caller can return 503.  Never fakes a result.
    """
    appeal = await db.scalar(select(Appeal).where(Appeal.id == appeal_id))
    if not appeal:
        raise AIServiceError(f"Appeal not found: {appeal_id}")

    # Mark as pending while we work
    appeal.ai_review_status = "PENDING"
    await db.flush()

    try:
        result = await _do_appeal_review(appeal, db)
    except AIServiceError:
        appeal.ai_review_status = "FAILED"
        await db.commit()
        raise

    return result


async def _do_appeal_review(appeal: Appeal, db: AsyncSession) -> AITask:
    """Inner implementation — separated so we can set FAILED status on raise."""

    punishment_id = appeal.punishment_id
    player_uuid = appeal.player_uuid
    appeal_id = appeal.id

    async def _fetch_punishment():
        return await db.scalar(
            select(Punishment).where(Punishment.id == punishment_id)
        )

    async def _fetch_player():
        return await db.scalar(
            select(Player).where(Player.uuid == player_uuid)
        )

    async def _fetch_all_punishments():
        result = await db.execute(
            select(Punishment)
            .where(Punishment.player_uuid == player_uuid)
            .order_by(Punishment.created_at.desc())
        )
        return list(result.scalars().all())

    async def _fetch_previous_appeals():
        result = await db.execute(
            select(Appeal)
            .where(
                Appeal.player_uuid == player_uuid,
                Appeal.id != appeal.id,
            )
            .order_by(Appeal.created_at.desc())
        )
        return list(result.scalars().all())

    punishment, player, all_punishments, prev_appeals = await asyncio.gather(
        _fetch_punishment(),
        _fetch_player(),
        _fetch_all_punishments(),
        _fetch_previous_appeals(),
    )

    # GrimAC ±72hr window around punishment issued date
    anticheat_section = "No GrimAC flags in this window."
    if _HAS_ANTICHEAT and punishment and punishment.created_at:
        punishment_dt = punishment.created_at
        if punishment_dt.tzinfo is None:
            punishment_dt = punishment_dt.replace(tzinfo=timezone.utc)
        window_start = punishment_dt - timedelta(hours=72)
        window_end = punishment_dt + timedelta(hours=72)

        violations_result = await db.execute(
            select(AnticheatViolation)
            .where(
                AnticheatViolation.player_uuid == player_uuid,
                AnticheatViolation.timestamp >= window_start,
                AnticheatViolation.timestamp <= window_end,
            )
            .order_by(AnticheatViolation.timestamp.asc())
        )
        violations = list(violations_result.scalars().all())
        anticheat_section = _build_anticheat_summary(violations)

    ptype_counts = Counter(p.type for p in all_punishments)
    punishment_breakdown = ", ".join(f"{v}x {k}" for k, v in ptype_counts.items()) or "none"

    if prev_appeals:
        prev_appeal_lines = []
        for pa in prev_appeals[:5]:
            outcome = getattr(pa, "action_taken", None) or pa.status
            prev_appeal_lines.append(f"  #{pa.id[:8]} — {outcome} on {_fmt_dt(pa.created_at)}")
        prev_appeals_text = "\n".join(prev_appeal_lines)
    else:
        prev_appeals_text = "  None"

    username = player.username if player else player_uuid
    punishment_type = punishment.type if punishment else "unknown"
    punishment_reason = punishment.reason if punishment else "unknown"
    staff_id = punishment.staff_id if punishment else "unknown"
    punishment_date = _fmt_dt(punishment.created_at if punishment else None)
    first_offence = len(all_punishments) == 1

    context_str = f"""APPEAL REVIEW CONTEXT
=====================
Appeal: #{appeal_id} | Submitted: {_fmt_dt(appeal.created_at)}
Player: {username} ({player_uuid})
Original Punishment: {punishment_type} | Reason: {punishment_reason} | Issued by: {staff_id} on {punishment_date}

Player History:
- Total punishments: {len(all_punishments)} ({punishment_breakdown})
- {"First offence" if first_offence else f"Repeat offender ({len(all_punishments)} total punishments)"}
- Previous appeals: {len(prev_appeals)} outcomes:
{prev_appeals_text}

GrimAC Context (±72hr around punishment):
{anticheat_section}

Appeal Statement:
{appeal.message}
"""

    system_prompt = (
        "You are UmbrellaOS Appeal Reviewer. Analyze this Minecraft server ban appeal objectively.\n"
        "Return JSON only:\n"
        "{\n"
        '  "recommendation": "ACCEPT|REDUCE_SENTENCE|REJECT|ESCALATE|SCHEDULE_REVIEW",\n'
        '  "confidence": 0.0-1.0,\n'
        '  "reasoning": "2-3 sentences",\n'
        '  "punishment_context": "first offence / repeat offender summary",\n'
        '  "flag_summary": "GrimAC context or null",\n'
        '  "risk_factors": ["list"],\n'
        '  "mitigating_factors": ["list"]\n'
        "}"
    )

    ai_result = await _orchestrate(
        db, "appeal_review", system_prompt, context_str,
        requested_by=f"appeal_review:{appeal_id}",
    )

    appeal.ai_review_result = json.dumps(ai_result)
    appeal.ai_review_status = "COMPLETED"

    recommendation = ai_result.get("recommendation", "SCHEDULE_REVIEW")
    confidence = float(ai_result.get("confidence", 0.5))
    reasoning = ai_result.get("reasoning", "")

    evidence = {
        "appeal_id": appeal_id,
        "punishment_type": punishment_type,
        "punishment_reason": punishment_reason,
        "punishment_count": len(all_punishments),
        "previous_appeals": len(prev_appeals),
        "ai_result": ai_result,
    }

    task = AITask(
        task_type="appeal_review",
        status="pending",
        player_uuid=player_uuid,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        ai_summary=reasoning[:500],
        ai_recommendation=recommendation,
        ai_confidence=confidence,
        evidence=json.dumps(evidence),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return task


# ---------------------------------------------------------------------------
# Chat review — now also routed through ModelRouter
# ---------------------------------------------------------------------------

async def review_chat_message(
    message_id: int,
    db: AsyncSession,
) -> AITask:
    """
    AI review of a chat message.
    Routes through the ModelRouter using task_type="chat_review".
    """
    message = await db.scalar(select(ChatMessage).where(ChatMessage.id == message_id))
    if not message:
        raise AIServiceError(f"Chat message not found: {message_id}")

    player = None
    if message.player_uuid:
        player = await db.scalar(select(Player).where(Player.uuid == message.player_uuid))

    punishments = []
    if player:
        punishment_result = await db.execute(
            select(Punishment)
            .where(Punishment.player_uuid == player.uuid)
            .order_by(Punishment.created_at.desc())
            .limit(5)
        )
        punishments = punishment_result.scalars().all()

    context = {
        "message": {
            "id": message.id,
            "source": message.source,
            "message": message.message,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "filtered": message.filtered,
        },
        "player": {
            "uuid": player.uuid if player else None,
            "username": player.username if player else None,
            "suspicion_score": player.suspicion_score if player else None,
        } if player else None,
        "history": [
            {
                "type": p.type,
                "reason": p.reason,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in punishments
        ],
    }

    system_prompt = (
        "You are a Minecraft server moderator AI assistant. "
        "Review the following chat message and assess if it violates server rules. "
        "Return JSON only with keys: summary (str), recommendation (mute|warn|delete|no_action), confidence (float 0-1)."
    )

    user_content = json.dumps(context, indent=2)

    ai_response = await _orchestrate(
        db, "chat_review", system_prompt, user_content,
        requested_by=f"chat_review:{message_id}",
    )

    task = AITask(
        task_type="chat_review",
        status="pending",
        player_uuid=message.player_uuid,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        ai_summary=ai_response.get("summary", "")[:500],
        ai_recommendation=ai_response.get("recommendation", "review"),
        ai_confidence=float(ai_response.get("confidence", 0.5)),
        evidence=json.dumps(context),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return task
