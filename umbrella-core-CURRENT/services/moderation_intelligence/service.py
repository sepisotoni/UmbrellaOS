"""
services/moderation_intelligence/service.py — Ported from Moo-assistant's
bot/moderation/intelligence_service.py (analysis pipeline only -
maybe_auto_apply() is Phase 6 scope; see the module-level note below).

Two confirmed bugs from the source, fixed here rather than ported:

Bug B — an out-of-enum AI response used to crash the whole pipeline.
`RecommendedAction(parsed.get("recommended_action"))` had no error
handling; a single instruction-non-compliant model response (LLMs are not
100% instruction-compliant - this will happen in production) raised an
uncaught ValueError. Fixed: wrapped in try/except, falls back to ESCALATE -
the same fail-safe direction _safe_parse already uses for malformed JSON.

Bug C — inconsistent code-fence stripping caused spurious escalations.
`_safe_parse` stripped markdown fences before parsing; the agreement
comparison used for dual review did not, so a fenced response caused a
JSON-parse failure there specifically, which was scored as "disagreement"
(triggering an unnecessary escalation) purely due to formatting, not real
model disagreement. Fixed: both paths now share `_strip_fences`.

Not ported: Moo's `maybe_auto_apply()`, which executes a recommended
action against live Discord objects (member.timeout(), message.delete()).
umbrella-core has no live Discord connection until Phase 6 - see
docs/adr/phase-7-notes-from-phase-5.md's sibling discussion and
current-blockers.md history. This service produces a persisted
ModerationAnalysis and, when warranted, a StaffEscalation; actually
executing the recommended action is Phase 6's job, once
registry/adapters/ai.py:call_tool() has real warn/timeout/delete_message
capabilities to call.

Known, unsolved limitation carried forward from the source, not something
fixable by careful coding alone: the reported user's own recent messages
and the report's freeform `reason` field are both user-controlled text fed
directly into the LLM's evidence context - a real prompt-injection surface.
Mitigated only by the existing structural guards (the closed
RecommendedAction enum, action_guard's capability-level enforcement once
Phase 6 wires up execution, and the confidence/agreement escalation below),
not eliminated.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.discord import ChatMessage
from models.moderation_intelligence import (
    ModerationReport,
    RecommendedAction,
    ReportStatus,
)
from services.ai.constitution_service import ConstitutionService
from services.ai.orchestrator import Orchestrator
from services.moderation_intelligence.repository import ModerationIntelRepository

_CODE_FENCE_RE = re.compile(r"```(?:json)?|```")

_TASK_TYPE = "moderation_report_analysis"

_RESULT_SCHEMA_INSTRUCTIONS = """
Respond with ONLY a JSON object (no prose, no markdown code fences) with exactly these fields:
{
  "risk_score": <0.0-1.0, how likely this report describes genuinely harmful behavior>,
  "recommended_action": <one of: "none", "warn", "delete_message", "timeout", "escalate">,
  "evidence_summary": <1-3 sentences citing what in the evidence actually supports this conclusion>
}
"escalate" means you are not confident enough to recommend a specific action - use it whenever the
evidence is ambiguous, contradictory, or insufficient. Never recommend an action beyond this list.
""".strip()


def _strip_fences(text: str) -> str:
    """Strips markdown code fences a model may have wrapped its JSON in,
    despite being asked not to. Shared by both _safe_parse and the
    dual-review agreement comparison below - Bug C in the source was these
    two call sites disagreeing on whether to do this."""
    return _CODE_FENCE_RE.sub("", text).strip()


def _safe_parse(text: str) -> dict:
    """Parses a model's JSON response, tolerating markdown fences. Returns
    an empty dict (never raises) on any parse failure - callers must treat
    a missing key as "the model didn't give us this," not assume it's
    present."""
    try:
        return json.loads(_strip_fences(text))
    except (json.JSONDecodeError, TypeError):
        return {}


def _moderation_agreement(text_a: str, text_b: str) -> float:
    """Passed as Orchestrator.run()'s agreement_fn: two analyses "agree"
    if they recommend the same action, regardless of how differently
    their evidence_summary is worded - a structured-field comparison is
    what this task actually needs, not raw text similarity (see the
    agreement_fn addition in services/ai/orchestrator.py for why the
    default text-similarity heuristic would score this kind of agreement
    incorrectly)."""
    a = _safe_parse(text_a).get("recommended_action")
    b = _safe_parse(text_b).get("recommended_action")
    return 1.0 if a is not None and a == b else 0.0


class ModerationIntelligenceService:
    @staticmethod
    async def _gather_evidence(db: AsyncSession, reported_user_id: str) -> str:
        """Builds the evidence block fed to the model: the reported
        user's recent chat messages and their recent warning count.
        Deliberately does not include anything from before this report
        window that isn't specifically warning history - the goal is
        recent, relevant context, not everything ever said."""
        messages_result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.discord_id == reported_user_id, ChatMessage.source == "discord")
            .order_by(ChatMessage.timestamp.desc())
            .limit(10)
        )
        recent_messages = list(reversed(messages_result.scalars().all()))

        since = datetime.now(timezone.utc) - timedelta(hours=get_settings().repeat_offender_lookback_hours)
        recent_warning_count = await ModerationIntelRepository.count_recent_warnings(
            db, reported_user_id, since=since
        )

        lines = [f"Recent warning count (last {get_settings().repeat_offender_lookback_hours}h): {recent_warning_count}"]
        if recent_messages:
            lines.append("Recent messages from this user:")
            for msg in recent_messages:
                lines.append(f"- {msg.message}")
        else:
            lines.append("No recent messages found for this user.")
        return "\n".join(lines)

    @staticmethod
    async def analyze_report(db: AsyncSession, report: ModerationReport) -> dict:
        """
        Runs a ModerationReport through the AI layer: gathers evidence,
        dual-reviews a risk assessment, persists the analysis, and
        escalates to staff when confidence is too low or the two models
        disagree. Returns a plain dict summary (not an ORM object) so
        callers - a future Discord cog, a REST endpoint - don't need to
        know about SQLAlchemy session lifecycle to read the result.
        """
        evidence = await ModerationIntelligenceService._gather_evidence(db, report.reported_user_id)
        system_prompt = await ConstitutionService.build_system_prompt(
            db, f"You are analyzing a moderation report. {_RESULT_SCHEMA_INSTRUCTIONS}"
        )
        task_prompt = f"Report reason: {report.reason}\n\nEvidence:\n{evidence}"

        result = await Orchestrator.run(
            db,
            _TASK_TYPE,
            task_prompt,
            requested_by=report.reporter_id,
            agreement_fn=_moderation_agreement,
        )

        parsed = _safe_parse(result.text)

        try:
            recommended_action = RecommendedAction(parsed.get("recommended_action", "escalate"))
        except ValueError:
            # Bug B, fixed: the model returned something outside the five
            # allowed values (or omitted the field). Fail safe to
            # ESCALATE rather than let a ValueError take down report
            # analysis entirely - the same direction _safe_parse already
            # takes for malformed JSON.
            recommended_action = RecommendedAction.ESCALATE

        risk_score = parsed.get("risk_score")
        risk_score = float(risk_score) if isinstance(risk_score, (int, float)) else 0.5
        evidence_summary = parsed.get("evidence_summary") or "No evidence summary provided by the model."

        low_confidence_action = (
            recommended_action != RecommendedAction.NONE
            and result.confidence < get_settings().confidence_escalation_threshold
        )
        should_escalate = (
            result.escalated
            or recommended_action == RecommendedAction.ESCALATE
            or low_confidence_action
        )

        analysis = await ModerationIntelRepository.save_analysis(
            db,
            report_id=report.id,
            risk_score=risk_score,
            confidence=result.confidence,
            recommended_action=recommended_action,
            evidence_summary=evidence_summary,
            primary_model=f"{result.primary_provider}/{result.primary_model}",
            secondary_model=(
                f"{result.secondary_provider}/{result.secondary_model}" if result.secondary_provider else None
            ),
            agreement=result.dual_review_agreement,
            action_taken=False,  # Phase 6 sets this once real execution exists
        )

        if should_escalate:
            await ModerationIntelRepository.set_report_status(db, report.id, ReportStatus.ESCALATED)
            await ModerationIntelRepository.create_escalation(
                db,
                source="moderation",
                summary=evidence_summary,
                confidence=result.confidence,
                related_report_id=report.id,
            )
        else:
            await ModerationIntelRepository.set_report_status(db, report.id, ReportStatus.AUTO_RESOLVED)

        return {
            "report_id": report.id,
            "analysis_id": analysis.id,
            "risk_score": risk_score,
            "confidence": result.confidence,
            "recommended_action": recommended_action.value,
            "escalated": should_escalate,
            "evidence_summary": evidence_summary,
        }

    @staticmethod
    async def check_repeat_offender(db: AsyncSession, user_id: str) -> ModerationReport | None:
        """
        If a user has crossed the repeat-offender warning threshold within
        the lookback window, auto-creates a system-generated
        ModerationReport for them (source="heuristic:repeat_offender") -
        the same pattern as the spam/raid heuristic detectors, just
        triggered by warning history instead of a message-rate window.
        Returns the created report, or None if the threshold isn't met.
        """
        settings = get_settings()
        since = datetime.now(timezone.utc) - timedelta(hours=settings.repeat_offender_lookback_hours)
        warning_count = await ModerationIntelRepository.count_recent_warnings(db, user_id, since=since)

        if warning_count < settings.repeat_offender_warning_count:
            return None

        return await ModerationIntelRepository.create_report(
            db,
            reported_user_id=user_id,
            reporter_id=None,
            channel_id=None,
            reported_message_id=None,
            reason=f"Automated: {warning_count} warnings in the last {settings.repeat_offender_lookback_hours}h",
            source="heuristic:repeat_offender",
        )
