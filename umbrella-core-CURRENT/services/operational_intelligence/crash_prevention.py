"""
services/operational_intelligence/crash_prevention.py — Predictive crash
prevention (Phase 5's first "novel capability").

Anomaly detection over the ServerMetricSnapshot time series (see that
model's module docstring, and models/server_metrics.py, for why this is
TPS + online player count only, not TPS/MSPT/memory as the roadmap's text
literally describes - MSPT isn't reported anywhere, and memory can't be
reliably joined to this identity space).

Deliberately a simple, explainable heuristic - a trend comparison plus
threshold checks - not a statistical/ML anomaly detector. This is a
judgment call worth stating plainly: a simple, auditable rule a staff
member can understand at a glance ("TPS dropped from 19 to 12 over the
last 15 minutes") is more useful for an operational alert than a more
sophisticated model whose reasoning is opaque, especially with the
relatively small, noisy sample sizes a single Minecraft server produces.
"""
from __future__ import annotations

import datetime as dt
import enum
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from services.operational_intelligence.metrics import recent_snapshots


class CrashRiskLevel(str, enum.Enum):
    INSUFFICIENT_DATA = "insufficient_data"
    NONE = "none"
    WATCH = "watch"
    CRITICAL = "critical"


@dataclass(frozen=True)
class CrashRiskAssessment:
    server_id: str
    risk_level: CrashRiskLevel
    current_tps: float | None
    trend_delta: float | None  # negative means declining (2nd-half avg minus 1st-half avg)
    samples_analyzed: int
    reasoning: str


async def assess_crash_risk(db: AsyncSession, server_id: str) -> CrashRiskAssessment:
    settings = get_settings()
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=settings.crash_prevention_lookback_minutes)
    snapshots = await recent_snapshots(db, server_id, since=since)

    if len(snapshots) < settings.crash_prevention_min_samples:
        return CrashRiskAssessment(
            server_id=server_id,
            risk_level=CrashRiskLevel.INSUFFICIENT_DATA,
            current_tps=snapshots[-1].tps if snapshots else None,
            trend_delta=None,
            samples_analyzed=len(snapshots),
            reasoning=(
                f"Only {len(snapshots)} sample(s) in the last "
                f"{settings.crash_prevention_lookback_minutes} minutes - need at least "
                f"{settings.crash_prevention_min_samples} to assess a trend."
            ),
        )

    current_tps = snapshots[-1].tps
    midpoint = len(snapshots) // 2
    first_half_avg = sum(s.tps for s in snapshots[:midpoint]) / midpoint
    second_half = snapshots[midpoint:]
    second_half_avg = sum(s.tps for s in second_half) / len(second_half)
    trend_delta = second_half_avg - first_half_avg
    trending_down = trend_delta <= -settings.crash_prevention_trend_drop_threshold

    if current_tps < settings.crash_prevention_critical_tps:
        return CrashRiskAssessment(
            server_id=server_id,
            risk_level=CrashRiskLevel.CRITICAL,
            current_tps=current_tps,
            trend_delta=trend_delta,
            samples_analyzed=len(snapshots),
            reasoning=(
                f"Current TPS ({current_tps:.1f}) is below the critical threshold "
                f"({settings.crash_prevention_critical_tps:.1f}) - the server is at serious risk "
                f"of becoming unresponsive."
            ),
        )

    if trending_down and current_tps < settings.crash_prevention_watch_tps:
        return CrashRiskAssessment(
            server_id=server_id,
            risk_level=CrashRiskLevel.WATCH,
            current_tps=current_tps,
            trend_delta=trend_delta,
            samples_analyzed=len(snapshots),
            reasoning=(
                f"TPS has dropped from an average of {first_half_avg:.1f} to {second_half_avg:.1f} "
                f"over the last {settings.crash_prevention_lookback_minutes} minutes, and current TPS "
                f"({current_tps:.1f}) is below the watch threshold ({settings.crash_prevention_watch_tps:.1f}) - "
                f"worth checking before it gets worse."
            ),
        )

    return CrashRiskAssessment(
        server_id=server_id,
        risk_level=CrashRiskLevel.NONE,
        current_tps=current_tps,
        trend_delta=trend_delta,
        samples_analyzed=len(snapshots),
        reasoning=f"Current TPS ({current_tps:.1f}) and recent trend show no sign of an impending crash.",
    )
