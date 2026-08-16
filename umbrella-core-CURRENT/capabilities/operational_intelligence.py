"""
capabilities/operational_intelligence.py — Predictive crash prevention and
natural-language operational queries (Phase 5's novel capabilities #1 and
#3). See services/operational_intelligence/*.py module docstrings for the
real scope notes (no MSPT, TPS+online-count only, window resolution is the
caller's job).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from registry.context import CallContext
from registry.decorator import capability
from services.operational_intelligence.crash_prevention import assess_crash_risk
from services.operational_intelligence.nl_query import answer_operational_query
from services.operational_intelligence.postmortem import draft_postmortem


class AssessCrashRiskParams(BaseModel):
    server_id: str = Field(description="The PluginHeartbeat-reported server identity to assess")

    def audit_target(self) -> str:
        return self.server_id


class CrashRiskResult(BaseModel):
    server_id: str
    risk_level: str
    current_tps: float | None
    trend_delta: float | None
    samples_analyzed: int
    reasoning: str


@capability(
    name="operational_intelligence.crash_risk.assess",
    summary="Assess a server's predictive crash risk from its recent TPS/online-count trend.",
    params_model=AssessCrashRiskParams,
    result_model=CrashRiskResult,
    required_permission="operational_intelligence.view",
    destructive=False,
    reversible=True,
    audited=False,
)
async def crash_risk_assess(ctx: CallContext, params: AssessCrashRiskParams) -> CrashRiskResult:
    result = await assess_crash_risk(ctx.db, params.server_id)
    return CrashRiskResult(
        server_id=result.server_id,
        risk_level=result.risk_level.value,
        current_tps=result.current_tps,
        trend_delta=result.trend_delta,
        samples_analyzed=result.samples_analyzed,
        reasoning=result.reasoning,
    )


class OperationalQueryParams(BaseModel):
    server_id: str
    question: str = Field(description='e.g. "Why did the server lag at 3pm?"')
    window_start: datetime = Field(description="Start of the time window to analyze")
    window_end: datetime = Field(description="End of the time window to analyze")


class OperationalQueryResult(BaseModel):
    answer: str
    confidence: float
    escalated: bool
    evidence: str


@capability(
    name="operational_intelligence.query",
    summary="Answer a natural-language question about server operations, grounded in recorded metrics and activity.",
    params_model=OperationalQueryParams,
    result_model=OperationalQueryResult,
    required_permission="operational_intelligence.view",
    destructive=False,
    reversible=True,
)
async def query(ctx: CallContext, params: OperationalQueryParams) -> OperationalQueryResult:
    result = await answer_operational_query(
        ctx.db,
        server_id=params.server_id,
        question=params.question,
        window_start=params.window_start,
        window_end=params.window_end,
        requested_by=ctx.actor_id,
    )
    return OperationalQueryResult(**result)


class DraftPostmortemParams(BaseModel):
    server_id: str

    def audit_target(self) -> str:
        return self.server_id


class DraftPostmortemResult(BaseModel):
    server_id: str
    draft: str
    confidence: float
    escalated: bool
    evidence: str
    status: str


@capability(
    name="operational_intelligence.postmortem.draft",
    summary="Draft an AI-authored incident postmortem for staff review (never auto-published).",
    params_model=DraftPostmortemParams,
    result_model=DraftPostmortemResult,
    required_permission="operational_intelligence.view",
    destructive=False,
    reversible=True,
)
async def postmortem_draft(ctx: CallContext, params: DraftPostmortemParams) -> DraftPostmortemResult:
    result = await draft_postmortem(ctx.db, params.server_id, requested_by=ctx.actor_id)
    return DraftPostmortemResult(**result)
