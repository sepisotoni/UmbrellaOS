"""
capabilities/moderation_intelligence.py — Discord-side AI moderation
capabilities (Phase 5), over registry/registry.py.

Permissions are namespaced "moderation_intelligence.*", distinct from the
pre-existing "moderation.*" keys (see services/roles_service.py) which
govern the Minecraft-side, player.uuid-keyed Punishment system - a
different domain entirely from Discord user moderation.

None of these capabilities execute an action against live Discord (warn a
member, delete a message, apply a timeout) - that needs the live bot
connection Phase 6 adds. What's here is the full analysis pipeline: create
a report, analyze it (dual-reviewed AI risk assessment, persisted, escalated
when warranted), and manage the resulting staff escalation queue.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from models.moderation_intelligence import ModerationReport, StaffEscalation
from registry.context import CallContext
from registry.decorator import capability
from services.moderation_intelligence.repository import ModerationIntelRepository
from services.moderation_intelligence.service import ModerationIntelligenceService

# --------------------------------------------------------------------------
# moderation_intelligence.report.create
# --------------------------------------------------------------------------


class CreateReportParams(BaseModel):
    reported_user_id: str = Field(description="Discord user ID being reported")
    reason: str = Field(description="What's being reported and why")
    channel_id: str | None = Field(default=None, description="Channel the reported behavior occurred in, if any")
    reported_message_id: str | None = Field(default=None, description="Specific message being reported, if any")

    def audit_target(self) -> str:
        return self.reported_user_id


class ReportResult(BaseModel):
    id: str
    reported_user_id: str
    reporter_id: str | None
    channel_id: str | None
    reason: str
    source: str
    status: str


def _report_to_result(report: ModerationReport) -> ReportResult:
    return ReportResult(
        id=report.id,
        reported_user_id=report.reported_user_id,
        reporter_id=report.reporter_id,
        channel_id=report.channel_id,
        reason=report.reason,
        source=report.source,
        status=report.status.value,
    )


@capability(
    name="moderation_intelligence.report.create",
    summary="Create a moderation report for a Discord user.",
    params_model=CreateReportParams,
    result_model=ReportResult,
    required_permission="moderation_intelligence.report.manage",
    destructive=False,
    reversible=True,
)
async def create_report(ctx: CallContext, params: CreateReportParams) -> ReportResult:
    """
    reporter_id is deliberately taken from the calling context, not the
    params - a report is always attributed to whoever actually called
    this (a staff member via REST/CLI, or "None" if the AI-facing caller
    represents a system-generated report), never a freely-supplied field
    that could misattribute a report to someone else.
    """
    report = await ModerationIntelRepository.create_report(
        ctx.db,
        reported_user_id=params.reported_user_id,
        reporter_id=None if ctx.source == "ai" and ctx.is_superuser else ctx.actor_id,
        channel_id=params.channel_id,
        reported_message_id=params.reported_message_id,
        reason=params.reason,
        source="user",
    )
    return _report_to_result(report)


# --------------------------------------------------------------------------
# moderation_intelligence.report.analyze
# --------------------------------------------------------------------------


class AnalyzeReportParams(BaseModel):
    report_id: str

    def audit_target(self) -> str:
        return self.report_id


class AnalysisResult(BaseModel):
    report_id: str
    analysis_id: str
    risk_score: float
    confidence: float
    recommended_action: str
    escalated: bool
    evidence_summary: str


@capability(
    name="moderation_intelligence.report.analyze",
    summary="Run AI dual-review analysis on a moderation report.",
    params_model=AnalyzeReportParams,
    result_model=AnalysisResult,
    required_permission="moderation_intelligence.report.manage",
    destructive=False,
    reversible=True,
)
async def analyze_report(ctx: CallContext, params: AnalyzeReportParams) -> AnalysisResult:
    from api.middleware.errors import ResourceNotFoundException

    report = await ctx.db.get(ModerationReport, params.report_id)
    if report is None:
        raise ResourceNotFoundException("Moderation report", params.report_id)

    result = await ModerationIntelligenceService.analyze_report(ctx.db, report)
    return AnalysisResult(**result)


# --------------------------------------------------------------------------
# moderation_intelligence.report.get
# --------------------------------------------------------------------------


class GetReportParams(BaseModel):
    report_id: str


@capability(
    name="moderation_intelligence.report.get",
    summary="Get a single moderation report by ID.",
    params_model=GetReportParams,
    result_model=ReportResult,
    required_permission="moderation_intelligence.report.view",
    destructive=False,
    reversible=True,
    audited=False,  # reading a single report is not itself an action worth auditing
)
async def get_report(ctx: CallContext, params: GetReportParams) -> ReportResult:
    from api.middleware.errors import ResourceNotFoundException

    report = await ctx.db.get(ModerationReport, params.report_id)
    if report is None:
        raise ResourceNotFoundException("Moderation report", params.report_id)
    return _report_to_result(report)


# --------------------------------------------------------------------------
# moderation_intelligence.escalation.list
# --------------------------------------------------------------------------


class ListEscalationsParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)


class EscalationResult(BaseModel):
    id: str
    source: str
    summary: str
    confidence: float | None
    resolved: bool
    related_report_id: str | None
    notified_at: str | None = None


class ListEscalationsResult(BaseModel):
    escalations: list[EscalationResult]


@capability(
    name="moderation_intelligence.escalation.list",
    summary="List open (unresolved) staff escalations.",
    params_model=ListEscalationsParams,
    result_model=ListEscalationsResult,
    required_permission="moderation_intelligence.escalation.view",
    destructive=False,
    reversible=True,
    audited=False,
)
async def list_escalations(ctx: CallContext, params: ListEscalationsParams) -> ListEscalationsResult:
    escalations = await ModerationIntelRepository.list_open_escalations(ctx.db, limit=params.limit)
    return ListEscalationsResult(
        escalations=[
            EscalationResult(
                id=e.id,
                source=e.source,
                summary=e.summary,
                confidence=e.confidence,
                resolved=e.resolved,
                related_report_id=e.related_report_id,
                notified_at=e.notified_at.isoformat() if e.notified_at else None,
            )
            for e in escalations
        ]
    )


# --------------------------------------------------------------------------
# moderation_intelligence.escalation.resolve
# --------------------------------------------------------------------------


class ResolveEscalationParams(BaseModel):
    escalation_id: str

    def audit_target(self) -> str:
        return self.escalation_id


@capability(
    name="moderation_intelligence.escalation.resolve",
    summary="Mark a staff escalation as resolved.",
    params_model=ResolveEscalationParams,
    result_model=EscalationResult,
    required_permission="moderation_intelligence.escalation.manage",
    destructive=False,
    reversible=True,
)
async def resolve_escalation(ctx: CallContext, params: ResolveEscalationParams) -> EscalationResult:
    from datetime import datetime, timezone

    from api.middleware.errors import ResourceNotFoundException

    escalation = await ctx.db.get(StaffEscalation, params.escalation_id)
    if escalation is None:
        raise ResourceNotFoundException("Escalation", params.escalation_id)

    escalation.resolved = True
    escalation.resolved_by = ctx.actor_id
    escalation.resolved_at = datetime.now(timezone.utc)
    await ctx.db.flush()

    return EscalationResult(
        id=escalation.id,
        source=escalation.source,
        summary=escalation.summary,
        confidence=escalation.confidence,
        resolved=escalation.resolved,
        related_report_id=escalation.related_report_id,
        notified_at=escalation.notified_at.isoformat() if escalation.notified_at else None,
    )


# --------------------------------------------------------------------------
# moderation_intelligence.escalation.mark_notified
#
# Closes the "notification/event-bus" gap flagged since early Phase 6:
# escalations existed and were listable, but nothing ever pushed them
# anywhere - umbrella-discord's notifications_cog.py polls
# escalation.list and calls this after successfully posting, so a bot
# restart mid-poll can't cause a duplicate announcement (the DB, not the
# bot process, is the source of truth for "already announced" - see
# models/moderation_intelligence.py's notified_at docstring). Not a true
# push/event-bus (core doesn't call out to Discord on its own) - a
# deliberately simpler polling design, see notifications_cog.py's own
# docstring for the full reasoning.
# --------------------------------------------------------------------------


class MarkNotifiedParams(BaseModel):
    escalation_id: str

    def audit_target(self) -> str:
        return self.escalation_id


@capability(
    name="moderation_intelligence.escalation.mark_notified",
    summary="Record that a staff escalation has been announced (e.g. posted to a Discord channel).",
    params_model=MarkNotifiedParams,
    result_model=EscalationResult,
    required_permission="moderation_intelligence.escalation.manage",
    destructive=False,
    reversible=True,
    audited=False,
)
async def mark_notified(ctx: CallContext, params: MarkNotifiedParams) -> EscalationResult:
    from api.middleware.errors import ResourceNotFoundException

    escalation = await ModerationIntelRepository.mark_notified(ctx.db, params.escalation_id)
    if escalation is None:
        raise ResourceNotFoundException("Escalation", params.escalation_id)

    return EscalationResult(
        id=escalation.id,
        source=escalation.source,
        summary=escalation.summary,
        confidence=escalation.confidence,
        resolved=escalation.resolved,
        related_report_id=escalation.related_report_id,
        notified_at=escalation.notified_at.isoformat() if escalation.notified_at else None,
    )
