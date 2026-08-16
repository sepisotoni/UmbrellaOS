"""
services/moderation_intelligence/repository.py — Ported from Moo-assistant's
bot/repositories/moderation_intel_repository.py (ModerationIntelRepository
only - InvestigationRepository lives with the investigation domain port).

Adapted to umbrella-core's dependency-injection convention: every method
takes `db: AsyncSession` from the caller rather than opening its own
`get_session()` block internally, matching ConstitutionService/ModelRouter/
every other service in this codebase. This also means a single capability
call's report-creation + analysis-persistence + escalation-creation all
share one transaction rather than three independent ones - if something
fails partway, nothing is left half-committed.

`count_recent_reports` was fetching every matching row just to len() it;
ported here as a real COUNT(*) query instead.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.moderation_intelligence import (
    ModerationAction,
    ModerationActionType,
    ModerationAnalysis,
    ModerationReport,
    ReportStatus,
    StaffEscalation,
)


class ModerationIntelRepository:
    """Data access for AI-assisted moderation: reports, analyses, escalations."""

    @staticmethod
    async def create_report(
        db: AsyncSession,
        *,
        reported_user_id: str,
        reporter_id: str | None,
        channel_id: str | None,
        reported_message_id: str | None,
        reason: str,
        source: str = "user",
    ) -> ModerationReport:
        report = ModerationReport(
            reported_user_id=reported_user_id,
            reporter_id=reporter_id,
            channel_id=channel_id,
            reported_message_id=reported_message_id,
            reason=reason,
            source=source,
        )
        db.add(report)
        await db.flush()
        return report

    @staticmethod
    async def set_report_status(db: AsyncSession, report_id: str, status: ReportStatus) -> None:
        report = await db.get(ModerationReport, report_id)
        if report is not None:
            report.status = status

    @staticmethod
    async def count_recent_reports(db: AsyncSession, reported_user_id: str, *, since: datetime) -> int:
        stmt = select(func.count()).select_from(ModerationReport).where(
            ModerationReport.reported_user_id == reported_user_id,
            ModerationReport.created_at >= since,
        )
        return (await db.execute(stmt)).scalar_one()

    @staticmethod
    async def save_analysis(
        db: AsyncSession,
        *,
        report_id: str,
        risk_score: float,
        confidence: float,
        recommended_action,
        evidence_summary: str,
        primary_model: str,
        secondary_model: str | None,
        agreement: bool | None,
        action_taken: bool,
    ) -> ModerationAnalysis:
        analysis = ModerationAnalysis(
            report_id=report_id,
            risk_score=risk_score,
            confidence=confidence,
            recommended_action=recommended_action,
            evidence_summary=evidence_summary,
            primary_model=primary_model,
            secondary_model=secondary_model,
            agreement=agreement,
            action_taken=action_taken,
        )
        db.add(analysis)
        await db.flush()
        return analysis

    @staticmethod
    async def count_recent_warnings(db: AsyncSession, user_id: str, *, since: datetime) -> int:
        stmt = select(func.count()).select_from(ModerationAction).where(
            ModerationAction.user_id == user_id,
            ModerationAction.action_type == ModerationActionType.WARN,
            ModerationAction.created_at >= since,
        )
        return (await db.execute(stmt)).scalar_one()

    @staticmethod
    async def create_escalation(
        db: AsyncSession,
        *,
        source: str,
        summary: str,
        confidence: float | None,
        related_report_id: str | None = None,
        related_investigation_id: str | None = None,
    ) -> StaffEscalation:
        escalation = StaffEscalation(
            source=source,
            summary=summary,
            confidence=confidence,
            related_report_id=related_report_id,
            related_investigation_id=related_investigation_id,
        )
        db.add(escalation)
        await db.flush()
        return escalation

    @staticmethod
    async def list_open_escalations(db: AsyncSession, limit: int = 20) -> list[StaffEscalation]:
        stmt = (
            select(StaffEscalation)
            .where(StaffEscalation.resolved.is_(False))
            .order_by(StaffEscalation.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def mark_notified(db: AsyncSession, escalation_id: str) -> StaffEscalation | None:
        """See models/moderation_intelligence.py's notified_at docstring
        for why this is tracked here rather than in umbrella-discord."""
        escalation = await db.get(StaffEscalation, escalation_id)
        if escalation is None:
            return None
        escalation.notified_at = datetime.now(timezone.utc)
        await db.flush()
        return escalation
