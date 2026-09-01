"""
capabilities/alt_detection_maintenance.py — Scheduled data-hygiene tasks
for the alt detection subsystem.

AUDIT-2026-08-30: player.suspicion_score had no decay mechanism at all —
see config/settings.py's suspicion_score_decay_points/
suspicion_score_decay_after_days comments for the full reasoning (the
alt_detection.py watchlist, suspicion_score >= 80, degrades over time
without decay). Same pattern as capabilities/anticheat_maintenance.py:
a plain capability staff wire up via a normal Schedule
(capabilities/automation.py's schedule CRUD), reusing the existing
scheduler infrastructure instead of a bespoke background loop.
"""
from __future__ import annotations

from pydantic import BaseModel

from capabilities.shared import NoParams
from registry.context import CallContext
from registry.decorator import capability
from services.alt_detection_service import decay_stale_suspicion_scores


class DecayStaleSuspicionScoresResult(BaseModel):
    decayed_count: int


@capability(
    name="alt_detection.suspicion.decay_stale",
    summary="Decay suspicion_score for players with no SuspicionEvent in the configured window (settings.suspicion_score_decay_after_days).",
    params_model=NoParams,
    result_model=DecayStaleSuspicionScoresResult,
    required_permission="punishments.manage",
    destructive=True,
    reversible=False,
    audited=True,
    audit_category="alt_detection",
)
async def decay_stale(ctx: CallContext, params: NoParams) -> DecayStaleSuspicionScoresResult:
    decayed_count = await decay_stale_suspicion_scores(ctx.db)
    return DecayStaleSuspicionScoresResult(decayed_count=decayed_count)
