"""
services/operational_intelligence/postmortem.py — AI-authored incident
postmortems (Phase 5's second "novel capability").

"On crash or major incident, auto-drafts a summary from logs + audit
trail + recent config changes, for staff review (never auto-published)."

One honest scope note, not silently glossed over: there is no raw server
log storage or fetching anywhere in this codebase (DaemonClient has no
logs method - confirmed while scoping this capability). This draws from
structured signals instead: the crash metadata already tracked on
models.hosting.Server (crash_count, last_crash_at, is_suspended - Phase
4's self-healing work), and the audit trail (settings changes with
old/new values, and capability actions) in the window around the crash.
A real, honest capability, just not literally "from logs."

"Never auto-published" is enforced by what this function does NOT do:
it returns a draft dict for a caller to show a staff member. Nothing here
posts anywhere, resolves the incident, or marks anything as reviewed -
that's a deliberate, structural absence, not an oversight.

**Gap closed (Phase 7, Decision 1's proof case):** `result.escalated`
used to be returned in the dict and nowhere else - a genuine signal from
Orchestrator.run (services/ai/orchestrator.py's own generic, task-type-
agnostic "confidence too low or dual-review disagreement" flag) that
never reached the staff escalation queue, confirmed by grep during Phase
6 (only services/moderation_intelligence/*.py wrote to StaffEscalation).
Now, when escalated, this writes a StaffEscalation row - reusing
ModerationIntelRepository.create_escalation directly rather than
duplicating it, since StaffEscalation is explicitly a table shared across
domains (see its own model docstring in models/moderation_intelligence.py:
"support" | "moderation" | "investigation", now also "operational") - and
publishes a "staff_escalation.created" event via EventBus.publish in the
SAME db session/transaction as the escalation row, so the two either both
commit or neither does (the outbox pattern's whole point).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import ResourceNotFoundException
from models.audit_log import AuditLog
from models.hosting import Server
from services.ai.constitution_service import ConstitutionService
from services.ai.orchestrator import Orchestrator
from services.events.bus import EventBus
from services.moderation_intelligence.repository import ModerationIntelRepository

_TASK_TYPE = "incident_postmortem"

# How far back from the crash to pull audit trail context - config
# changes or actions well before this are unlikely to be causally related,
# and pulling too wide a window risks diluting the actual signal with noise.
_LOOKBACK_HOURS = 2


async def _gather_incident_evidence(db: AsyncSession, server: Server) -> str:
    lines = [
        f"Server: {server.name} (status: {server.status}, suspended: {server.is_suspended})",
        f"Crash count (consecutive, unattended): {server.crash_count}",
    ]

    if server.last_crash_at is None:
        lines.append("No crash has been recorded for this server.")
        return "\n".join(lines)

    last_crash_at = server.last_crash_at
    if last_crash_at.tzinfo is None:
        last_crash_at = last_crash_at.replace(tzinfo=dt.timezone.utc)
    lines.append(f"Last crash at: {last_crash_at.isoformat()}")

    window_start = last_crash_at - dt.timedelta(hours=_LOOKBACK_HOURS)
    stmt = (
        select(AuditLog)
        .where(AuditLog.created_at >= window_start, AuditLog.created_at <= last_crash_at)
        .order_by(AuditLog.created_at.asc())
        .limit(50)
    )
    activity = list((await db.execute(stmt)).scalars().all())

    if activity:
        lines.append(f"Audit trail in the {_LOOKBACK_HOURS}h before the crash:")
        for entry in activity:
            lines.append(
                f"- {entry.created_at.isoformat()} [{entry.actor_type}:{entry.actor}] "
                f"{entry.action} (target: {entry.target or 'n/a'})"
            )
    else:
        lines.append(f"No audit trail activity was logged in the {_LOOKBACK_HOURS}h before the crash.")

    return "\n".join(lines)


async def draft_postmortem(db: AsyncSession, server_id: str, *, requested_by: str | None = None) -> dict:
    """Drafts an incident postmortem for staff review. Raises
    ResourceNotFoundException if server_id doesn't exist. Returns a draft
    even if no crash has been recorded (a genuinely useful "nothing to
    report" result is better than raising for a server that's simply
    healthy)."""
    server = await db.get(Server, server_id)
    if server is None:
        raise ResourceNotFoundException("Server", server_id)

    evidence = await _gather_incident_evidence(db, server)
    system_prompt = await ConstitutionService.build_system_prompt(
        db,
        "You are drafting an incident postmortem for staff review. This draft will NEVER be "
        "automatically published or shown to anyone other than staff - write it as an internal "
        "engineering document: what happened, likely contributing factors based only on the evidence "
        "given, and what staff should check next. If the evidence doesn't point to a clear cause, "
        "say so rather than speculating.",
    )
    task_prompt = f"Draft a postmortem for this incident.\n\n{evidence}"

    result = await Orchestrator.run(db, _TASK_TYPE, task_prompt, requested_by=requested_by)

    if result.escalated:
        escalation = await ModerationIntelRepository.create_escalation(
            db,
            source="operational",
            summary=f"Postmortem for server '{server.name}' needs staff review: {result.text[:300]}",
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
        "server_id": server_id,
        "draft": result.text,
        "confidence": result.confidence,
        "escalated": result.escalated,
        "evidence": evidence,
        "status": "draft",  # never anything else - this function has no path that publishes or resolves
    }
