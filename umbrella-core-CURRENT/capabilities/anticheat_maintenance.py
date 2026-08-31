"""
capabilities/anticheat_maintenance.py — Scheduled data-hygiene tasks for
the anticheat subsystem.

AUDIT-2026-08-30: anticheat_violations had no retention policy at all —
unbounded growth over time, flagged in
AUDIT-VERIFICATION-2026-08-29-MASTER-BUG-REPORT.md. Rather than a bespoke
background loop (like services/operational_intelligence/sampler_loop.py's
tightly-coupled sample+purge combo), this is a plain capability that
staff wire up via a normal Schedule
(capabilities/automation.py's schedule CRUD) — reuses the existing
scheduler infrastructure instead of inventing a new one, and gives staff
visibility/control over the cadence through whatever already manages
schedules, rather than a cadence hardcoded in Python.
"""
from __future__ import annotations

from pydantic import BaseModel

from capabilities.shared import NoParams
from registry.context import CallContext
from registry.decorator import capability
from services.anticheat_service import purge_old_violations


class PurgeOldViolationsResult(BaseModel):
    purged_count: int


@capability(
    name="anticheat.violations.purge_old",
    summary="Delete anticheat_violations older than the configured retention window (settings.anticheat_violation_retention_days).",
    params_model=NoParams,
    result_model=PurgeOldViolationsResult,
    required_permission="punishments.manage",
    destructive=True,
    reversible=False,
    audited=True,
    audit_category="anticheat",
)
async def purge_old(ctx: CallContext, params: NoParams) -> PurgeOldViolationsResult:
    purged_count = await purge_old_violations(ctx.db)
    return PurgeOldViolationsResult(purged_count=purged_count)
