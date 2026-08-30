"""
capabilities/investigation.py — Pluggable diagnostic tools (Phase 5), each
registered as its own capability, plus an aggregator that runs all of them.

See services/investigation/tools.py and models/investigation.py's module
docstrings for why Moo's intent-classifier-driven tool selection isn't
ported: the AI Tool Registry already exposes each of these directly to
the model via list_tools(), which is what a native tool-calling model
needs instead of a bespoke pre-filter.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from capabilities.shared import NoParams

from registry.context import CallContext
from registry.decorator import capability
from services.investigation.service import run_investigation
from services.investigation.tools import (
    InvestigationContext,
    KnownIssuesTool,
    LinkedAccountTool,
    MaintenanceStatusTool,
    PunishmentHistoryTool,
    RecentAnnouncementsTool,
    WhitelistStatusTool)


class TargetUserParams(BaseModel):
    target_user_id: str = Field(description="Discord user ID to run this diagnostic for")

    def audit_target(self) -> str:
        return self.target_user_id




class FindingResult(BaseModel):
    tool_key: str
    finding_text: str
    confidence: float


def _make_tool_capability(tool_cls, name: str, summary: str, needs_target: bool):
    """Registers a single InvestigationTool as a capability. All five
    ported tools follow the exact same shape (run one tool, return its
    one finding), so this generates the boilerplate once rather than
    duplicating a near-identical @capability function five times."""
    tool = tool_cls()
    params_model = TargetUserParams if needs_target else NoParams

    @capability(
        name=name,
        summary=summary,
        params_model=params_model,
        result_model=FindingResult,
        required_permission="investigation.run",
        destructive=False,
        reversible=True,
        audited=False,  # read-only diagnostics; the aggregate investigation.run call is audited instead
    )
    async def handler(ctx: CallContext, params) -> FindingResult:
        target_user_id = params.target_user_id if needs_target else None
        finding = await tool.run(ctx.db, InvestigationContext(target_user_id=target_user_id))
        return FindingResult(tool_key=finding.tool_key, finding_text=finding.finding_text, confidence=finding.confidence)

    return handler


_whitelist_status = _make_tool_capability(
    WhitelistStatusTool, "investigation.whitelist_status", "Check a user's whitelist application status.", True
)
_known_issues = _make_tool_capability(
    KnownIssuesTool, "investigation.known_issues", "List currently open known issues.", False
)
_punishment_history = _make_tool_capability(
    PunishmentHistoryTool, "investigation.punishment_history", "Look up a user's recent moderation history.", True
)
_linked_account = _make_tool_capability(
    LinkedAccountTool, "investigation.linked_account", "Check whether a Discord account is linked to an in-game account.", True
)
_maintenance_status = _make_tool_capability(
    MaintenanceStatusTool, "investigation.maintenance_status", "Check for any currently logged maintenance or outage.", False
)


class RecentAnnouncementsParams(BaseModel):
    question: str = Field(description="Keyword to search recent knowledge base entries for")


_recent_announcements_tool = RecentAnnouncementsTool()


@capability(
    name="investigation.recent_announcements",
    summary="Search the knowledge base for content relevant to a question.",
    params_model=RecentAnnouncementsParams,
    result_model=FindingResult,
    required_permission="investigation.run",
    destructive=False,
    reversible=True,
    audited=False)
async def recent_announcements(ctx: CallContext, params: RecentAnnouncementsParams) -> FindingResult:
    finding = await _recent_announcements_tool.run(ctx.db, InvestigationContext(target_user_id=None, question=params.question))
    return FindingResult(tool_key=finding.tool_key, finding_text=finding.finding_text, confidence=finding.confidence)


# --------------------------------------------------------------------------
# investigation.run — the aggregator
# --------------------------------------------------------------------------


class RunInvestigationParams(BaseModel):
    question: str = Field(description="The question being investigated")
    target_user_id: str | None = Field(default=None, description="Discord user this investigation concerns, if any")

    def audit_target(self) -> str | None:
        return self.target_user_id


class InvestigationResult(BaseModel):
    investigation_id: str
    summary: str
    confidence: float
    findings: list[FindingResult]


@capability(
    name="investigation.run",
    summary="Run every investigation tool and aggregate the findings into one report.",
    params_model=RunInvestigationParams,
    result_model=InvestigationResult,
    required_permission="investigation.run",
    destructive=False,
    reversible=True)
async def run(ctx: CallContext, params: RunInvestigationParams) -> InvestigationResult:
    result = await run_investigation(
        ctx.db, requested_by=ctx.actor_id, target_user_id=params.target_user_id, question=params.question
    )
    return InvestigationResult(**result)
