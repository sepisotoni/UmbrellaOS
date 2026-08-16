"""
services/investigation/service.py — The aggregator that replaces Moo's
intent-classifier-driven tool selection (bot/investigation/registry.py's
tools_for_intent). See models/investigation.py and
services/investigation/tools.py's module docstrings for why: umbrella-core's
AI Tool Registry already exposes each tool as its own capability directly to
the model, so a bespoke pre-filter isn't solving a problem that exists here.

`run_investigation` runs every registered tool (not an intent-filtered
subset) and persists the aggregate as an Investigation + its
InvestigationFindings - this is the one piece of real, still-useful value
from Moo's registry.py (a consolidated report a staff member or the AI can
read in one place), kept without the intent-classification layer.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from services.investigation.repository import InvestigationRepository
from services.investigation.tools import ALL_TOOLS, InvestigationContext, ToolFinding


async def run_investigation(
    db: AsyncSession, *, requested_by: str, target_user_id: str | None, question: str
) -> dict:
    """
    Runs every investigation tool against target_user_id, persists an
    Investigation with one InvestigationFinding per tool, and returns a
    plain dict summary - findings are deliberately concatenated as-is
    rather than run through another AI call to "summarize" them, since
    each tool's finding_text is already a short, direct statement; adding
    an LLM summarization pass here would add latency and a second place
    for the answer to drift from what the tools actually found.
    """
    context = InvestigationContext(target_user_id=target_user_id, question=question)
    findings: list[ToolFinding] = []
    for tool in ALL_TOOLS:
        findings.append(await tool.run(db, context))

    summary = " | ".join(f"[{f.tool_key}] {f.finding_text}" for f in findings)
    confidence = sum(f.confidence for f in findings) / len(findings) if findings else 0.0

    investigation = await InvestigationRepository.create_investigation(
        db,
        requested_by=requested_by,
        target_user_id=target_user_id,
        question=question,
        summary=summary,
        confidence=confidence,
    )
    for finding in findings:
        await InvestigationRepository.add_finding(
            db,
            investigation_id=investigation.id,
            tool_key=finding.tool_key,
            finding_text=finding.finding_text,
            confidence=finding.confidence,
        )

    return {
        "investigation_id": investigation.id,
        "summary": summary,
        "confidence": confidence,
        "findings": [{"tool_key": f.tool_key, "finding_text": f.finding_text, "confidence": f.confidence} for f in findings],
    }
