"""
services/operational_intelligence/nl_query.py — Natural-language
operational queries (Phase 5's third "novel capability").

"Why did the server lag at 3pm" resolved by cross-referencing the TPS/
online-count time series (models/server_metrics.py) and audit trail
activity (models.audit_log.AuditLog, filtered to actor_type="plugin" for
what the roadmap calls "plugin activity" - AuditLog already distinguishes
plugin-originated entries explicitly, a genuine match, not a stretch) from
the given window, then asking the AI orchestrator to synthesize an answer
grounded in that data rather than free-associating.

The window is required, not inferred from the question text itself ("at
3pm" -> parsing a specific date/time out of a free-form NL string is a
real natural-language-understanding problem in its own right, and getting
it wrong silently would mean confidently answering about the wrong window).
Whoever calls this resolves "3pm" to an actual (start, end) datetime pair
first - a Discord bot's NL front-end (Phase 6) or a dashboard time-range
picker are both natural places for that resolution to happen, not this
capability's job to guess at.

**Gap closed (Phase 7, Decision 1's proof case):** see
services/operational_intelligence/postmortem.py's module docstring for the
full reasoning - the same fix applies here: `result.escalated` now writes
a StaffEscalation row (source="operational") and publishes a
"staff_escalation.created" event in the same transaction, instead of only
being returned in the response dict and going nowhere.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog
from services.ai.constitution_service import ConstitutionService
from services.ai.orchestrator import Orchestrator
from services.events.bus import EventBus
from services.moderation_intelligence.repository import ModerationIntelRepository
from services.operational_intelligence.metrics import recent_snapshots

_TASK_TYPE = "operational_query"


async def _gather_window_evidence(
    db: AsyncSession, server_id: str, window_start: dt.datetime, window_end: dt.datetime
) -> str:
    snapshots = await recent_snapshots(db, server_id, since=window_start, limit=500)

    def _aware(value: dt.datetime) -> dt.datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=dt.timezone.utc)

    snapshots = [s for s in snapshots if _aware(s.recorded_at) <= window_end]

    activity_stmt = (
        select(AuditLog)
        .where(
            AuditLog.actor_type == "plugin",
            AuditLog.created_at >= window_start,
            AuditLog.created_at <= window_end,
        )
        .order_by(AuditLog.created_at.asc())
        .limit(50)
    )
    activity = list((await db.execute(activity_stmt)).scalars().all())

    lines = [f"Server metrics from {window_start.isoformat()} to {window_end.isoformat()}:"]
    if snapshots:
        tps_values = [s.tps for s in snapshots]
        online_values = [s.online_count for s in snapshots]
        lines.append(
            f"- TPS ranged from {min(tps_values):.1f} to {max(tps_values):.1f} "
            f"(started at {tps_values[0]:.1f}, ended at {tps_values[-1]:.1f})"
        )
        lines.append(
            f"- Online player count ranged from {min(online_values)} to {max(online_values)} "
            f"(started at {online_values[0]}, ended at {online_values[-1]})"
        )
    else:
        lines.append("- No server metric snapshots were recorded in this window.")

    if activity:
        lines.append("Plugin/server activity in this window:")
        for entry in activity:
            lines.append(f"- {entry.created_at.isoformat()}: {entry.action} (target: {entry.target or 'n/a'})")
    else:
        lines.append("No plugin/server activity was logged in this window.")

    return "\n".join(lines)


async def answer_operational_query(
    db: AsyncSession,
    *,
    server_id: str,
    question: str,
    window_start: dt.datetime,
    window_end: dt.datetime,
    requested_by: str | None = None,
) -> dict:
    """Answers a natural-language operational question, grounded in the
    actual metric/activity data from the given window - never asks the
    model to answer from its own general knowledge about Minecraft server
    performance instead of this server's actual recorded data."""
    evidence = await _gather_window_evidence(db, server_id, window_start, window_end)
    system_prompt = await ConstitutionService.build_system_prompt(
        db,
        "You are answering a staff member's question about this server's operational history. "
        "Base your answer ONLY on the evidence provided below - if the evidence doesn't support a "
        "clear answer, say so plainly rather than speculating.",
    )
    task_prompt = f"Question: {question}\n\n{evidence}"

    result = await Orchestrator.run(db, _TASK_TYPE, task_prompt, requested_by=requested_by)

    if result.escalated:
        escalation = await ModerationIntelRepository.create_escalation(
            db,
            source="operational",
            summary=f"Operational query on server '{server_id}' needs staff review: {question[:200]}",
            confidence=result.confidence,
        )
        await EventBus.publish(
            db,
            topic="staff_escalation.created",
            payload={
                "escalation_id": escalation.id,
                "source": "operational",
                "confidence": result.confidence,
                "server_id": server_id,
            },
        )

    return {
        "answer": result.text,
        "confidence": result.confidence,
        "escalated": result.escalated,
        "evidence": evidence,
    }
