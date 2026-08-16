"""
capabilities/player_risk.py — Unified player risk score (Phase 5's fourth
novel capability). See services/player_risk/risk_score.py's module
docstring for the full design.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from registry.context import CallContext
from registry.decorator import capability
from services.player_risk.risk_score import compute_risk_score


class RiskScoreParams(BaseModel):
    player_uuid: str = Field(description="Minecraft player UUID to compute a risk score for")

    def audit_target(self) -> str:
        return self.player_uuid


class RiskScoreBreakdownResult(BaseModel):
    anticheat_points: int
    confirmed_alt_group: bool
    moderation_action_count: int
    investigation_count: int
    anticheat_component: int
    alt_component: int
    moderation_component: int
    investigation_component: int


class RiskScoreResultModel(BaseModel):
    player_uuid: str
    discord_id: str | None
    total_score: int
    breakdown: RiskScoreBreakdownResult
    reasoning: str


@capability(
    name="player_risk.score",
    summary="Compute a unified risk score for a player, combining anticheat signals, alt detection, moderation history, and investigation findings.",
    params_model=RiskScoreParams,
    result_model=RiskScoreResultModel,
    required_permission="player_risk.view",
    destructive=False,
    reversible=True,
    audited=False,
)
async def score(ctx: CallContext, params: RiskScoreParams) -> RiskScoreResultModel:
    result = await compute_risk_score(ctx.db, params.player_uuid)
    return RiskScoreResultModel(
        player_uuid=result.player_uuid,
        discord_id=result.discord_id,
        total_score=result.total_score,
        breakdown=RiskScoreBreakdownResult(
            anticheat_points=result.breakdown.anticheat_points,
            confirmed_alt_group=result.breakdown.confirmed_alt_group,
            moderation_action_count=result.breakdown.moderation_action_count,
            investigation_count=result.breakdown.investigation_count,
            anticheat_component=result.breakdown.anticheat_component,
            alt_component=result.breakdown.alt_component,
            moderation_component=result.breakdown.moderation_component,
            investigation_component=result.breakdown.investigation_component,
        ),
        reasoning=result.reasoning,
    )
