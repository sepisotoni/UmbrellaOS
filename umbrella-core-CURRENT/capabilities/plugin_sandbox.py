"""
capabilities/plugin_sandbox.py — Phase 8 completion: the plugin
debugger/profiler/sandbox-visualizer read surface, entirely a view over
`PluginExecutionRecord` rows written by
`services/plugins/sandbox.py::ProcessSandbox.run` (Task A) plus the
process-wide sandbox's own configured resource limits (Task D). No
capability in this module ever writes a `PluginExecutionRecord` — that
happens exactly once, inside `ProcessSandbox.run` itself, independent of
any capability call (see that module's docstring for the security
reasoning: a plugin must never see or spoof its own resource-usage
report). This module is read-only by construction, not just convention.

Four capabilities, one per dispatch task:
    plugin.sandbox.execution_history — Task A.3, list view, paginated/
        filterable, mirrors capabilities/system.py's platform.audit.search
        shape exactly (same two-filter/limit/offset/total convention).
    plugin.sandbox.execution_detail  — Task B.1, single-execution detail
        (includes error_detail, which the list view deliberately omits).
    plugin.sandbox.profile           — Task C.1, per-plugin aggregate
        stats over a trailing time window.
    plugin.sandbox.limits            — Task D, the sandbox's actual
        configured resource limits (no new capture — services/plugins/
        sandbox.py::ProcessSandbox already holds these as
        ResourceLimits; this just surfaces them).

All four share one permission, `plugin.sandbox.view` (services/roles_service.py)
— see that file's own comment for why this is a separate namespace from
`marketplace.install.view` rather than reusing it. All four are
`audited=False`, matching every other read-only discovery capability in
this codebase (platform.audit.search, marketplace.install.list, etc.) —
reading telemetry is not itself an action worth an audit row.

Task C's aggregation is computed in Python, not SQL (no window functions
/ percentile_cont), deliberately: this codebase's test suite runs against
sqlite (tests/conftest.py), and the migration-bug history in
dispatches/PHASE10-COMPLETION/handback/STEP9-...md already found real
Postgres-vs-sqlite friction in this project once — a Postgres-only
aggregate function here would work in production and silently never be
exercised by the real test suite, or fail outright the moment anyone
tried to actually run it against sqlite. Per-plugin row counts within any
sane window are small enough that Python-side aggregation is not a
real performance concern.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select

from api.middleware.errors import ResourceNotFoundException
from models.plugin_execution import PluginExecutionRecord
from registry.context import CallContext
from registry.decorator import capability
from services.plugins.runtime import plugin_sandbox

# --------------------------------------------------------------------------
# plugin.sandbox.execution_history
# --------------------------------------------------------------------------


class ExecutionHistoryParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    plugin_id: str | None = Field(default=None, description="Filter to one plugin's executions.")
    outcome: str | None = Field(
        default=None, description="Filter by exact outcome: success | error | timeout | resource_limit_kill."
    )


class ExecutionHistoryEntryResult(BaseModel):
    id: str
    plugin_id: str
    entrypoint: str
    actor_id: str
    outcome: str
    wall_time_ms: float
    cpu_time_ms: float | None
    peak_memory_bytes: int | None
    created_at: str | None

    @classmethod
    def from_row(cls, row: PluginExecutionRecord) -> "ExecutionHistoryEntryResult":
        return cls(
            id=row.id,
            plugin_id=row.plugin_id,
            entrypoint=row.entrypoint,
            actor_id=row.actor_id,
            outcome=row.outcome,
            wall_time_ms=row.wall_time_ms,
            cpu_time_ms=row.cpu_time_ms,
            peak_memory_bytes=row.peak_memory_bytes,
            created_at=row.created_at.isoformat() if row.created_at else None,
        )


class ExecutionHistoryResult(BaseModel):
    entries: list[ExecutionHistoryEntryResult]
    total: int
    limit: int
    offset: int


@capability(
    name="plugin.sandbox.execution_history",
    summary="List sandboxed plugin executions with pagination and filtering, most recent first.",
    params_model=ExecutionHistoryParams,
    result_model=ExecutionHistoryResult,
    required_permission="plugin.sandbox.view",
    destructive=False,
    audited=False,
)
async def execution_history(ctx: CallContext, params: ExecutionHistoryParams) -> ExecutionHistoryResult:
    """Query logic deliberately mirrors capabilities/system.py's
    search_audit_log almost line for line — same base_query/count/page
    structure, same "count first against the filtered subquery, then page"
    approach — per the dispatch's explicit instruction to follow that
    shape rather than invent a different one."""
    base_query = select(PluginExecutionRecord)
    if params.plugin_id:
        base_query = base_query.where(PluginExecutionRecord.plugin_id == params.plugin_id)
    if params.outcome:
        base_query = base_query.where(PluginExecutionRecord.outcome == params.outcome)

    count_result = await ctx.db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_result.scalar_one()

    page_query = (
        base_query.order_by(desc(PluginExecutionRecord.created_at))
        .limit(params.limit)
        .offset(params.offset)
    )
    result = await ctx.db.execute(page_query)
    rows = result.scalars().all()

    return ExecutionHistoryResult(
        entries=[ExecutionHistoryEntryResult.from_row(row) for row in rows],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


# --------------------------------------------------------------------------
# plugin.sandbox.execution_detail — Task B.1, the plugin debugger's data
# source: one execution's full detail, including error_detail (the
# uncaught exception's str(), or the timeout/resource-limit message),
# which execution_history's list view above deliberately omits.
# --------------------------------------------------------------------------


class ExecutionDetailParams(BaseModel):
    execution_id: str


class ExecutionDetailResult(ExecutionHistoryEntryResult):
    error_detail: str | None

    @classmethod
    def from_row(cls, row: PluginExecutionRecord) -> "ExecutionDetailResult":  # type: ignore[override]
        return cls(
            id=row.id,
            plugin_id=row.plugin_id,
            entrypoint=row.entrypoint,
            actor_id=row.actor_id,
            outcome=row.outcome,
            wall_time_ms=row.wall_time_ms,
            cpu_time_ms=row.cpu_time_ms,
            peak_memory_bytes=row.peak_memory_bytes,
            created_at=row.created_at.isoformat() if row.created_at else None,
            error_detail=row.error_detail,
        )


@capability(
    name="plugin.sandbox.execution_detail",
    summary="Get full detail for one sandboxed plugin execution, including its error detail if it failed.",
    params_model=ExecutionDetailParams,
    result_model=ExecutionDetailResult,
    required_permission="plugin.sandbox.view",
    destructive=False,
    audited=False,
)
async def execution_detail(ctx: CallContext, params: ExecutionDetailParams) -> ExecutionDetailResult:
    row = await ctx.db.get(PluginExecutionRecord, params.execution_id)
    if row is None:
        raise ResourceNotFoundException("Plugin execution record", params.execution_id)
    return ExecutionDetailResult.from_row(row)


# --------------------------------------------------------------------------
# plugin.sandbox.profile — Task C.1, per-plugin aggregate stats over a
# trailing time window (default 24h — dispatch left this as "your call,
# state it": 24h is the tighter, more operationally useful default for a
# profiler an admin is actively looking at; a longer window is one param
# away, not a second capability).
# --------------------------------------------------------------------------


class ProfileParams(BaseModel):
    window_hours: int = Field(default=24, ge=1, le=720, description="Trailing window, in hours. Default 24h.")
    plugin_id: str | None = Field(default=None, description="Limit to one plugin; omit for every plugin with activity in the window.")


class ProfileEntryResult(BaseModel):
    plugin_id: str
    execution_count: int
    avg_wall_time_ms: float
    p95_wall_time_ms: float
    avg_peak_memory_bytes: float | None
    error_rate: float
    window_hours: int


@capability(
    name="plugin.sandbox.profile",
    summary="Aggregate per-plugin execution stats (avg/p95 duration, memory, error rate) over a trailing time window.",
    params_model=ProfileParams,
    result_model=list[ProfileEntryResult],
    required_permission="plugin.sandbox.view",
    destructive=False,
    audited=False,
)
async def profile(ctx: CallContext, params: ProfileParams) -> list[ProfileEntryResult]:
    """Fetches every matching row within the window and aggregates in
    Python — see this module's docstring for why (sqlite/Postgres
    portability, and the row counts involved are small). Grouped by
    plugin_id after the fact rather than a SQL GROUP BY, for the same
    reason: p95 has no simple, portable SQL aggregate across both
    backends this codebase runs against."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=params.window_hours)
    query = select(PluginExecutionRecord).where(PluginExecutionRecord.created_at >= cutoff)
    if params.plugin_id:
        query = query.where(PluginExecutionRecord.plugin_id == params.plugin_id)

    result = await ctx.db.execute(query)
    rows = result.scalars().all()

    by_plugin: dict[str, list[PluginExecutionRecord]] = {}
    for row in rows:
        by_plugin.setdefault(row.plugin_id, []).append(row)

    entries: list[ProfileEntryResult] = []
    for plugin_id, plugin_rows in sorted(by_plugin.items()):
        wall_times = sorted(r.wall_time_ms for r in plugin_rows)
        memory_samples = [r.peak_memory_bytes for r in plugin_rows if r.peak_memory_bytes is not None]
        error_count = sum(1 for r in plugin_rows if r.outcome != "success")

        entries.append(
            ProfileEntryResult(
                plugin_id=plugin_id,
                execution_count=len(plugin_rows),
                avg_wall_time_ms=statistics.fmean(wall_times),
                p95_wall_time_ms=_percentile(wall_times, 0.95),
                avg_peak_memory_bytes=statistics.fmean(memory_samples) if memory_samples else None,
                error_rate=error_count / len(plugin_rows),
                window_hours=params.window_hours,
            )
        )
    return entries


def _percentile(sorted_values: list[float], fraction: float) -> float:
    """Nearest-rank percentile over an already-sorted list. Deliberately
    simple (no interpolation) — this is an operational profiler surfacing
    "roughly how bad does the tail get," not a statistics package; a
    single-element list returns that element (its own p95, by
    definition)."""
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, round(fraction * (len(sorted_values) - 1))))
    return sorted_values[index]


# --------------------------------------------------------------------------
# plugin.sandbox.limits — Task D (sandbox visualizer): the real,
# currently-configured resource limits the process-wide sandbox enforces.
# No new capture — services/plugins/sandbox.py::ProcessSandbox already
# holds these as a ResourceLimits dataclass; this just surfaces them via
# the new `ProcessSandbox.limits` read-only property.
# --------------------------------------------------------------------------


class LimitsParams(BaseModel):
    pass


class LimitsResult(BaseModel):
    cpu_seconds: int
    memory_bytes: int
    wall_timeout_seconds: float


@capability(
    name="plugin.sandbox.limits",
    summary="Get the sandbox's currently-configured resource limits (CPU seconds, memory bytes, wall timeout).",
    params_model=LimitsParams,
    result_model=LimitsResult,
    required_permission="plugin.sandbox.view",
    destructive=False,
    audited=False,
)
async def limits(ctx: CallContext, params: LimitsParams) -> LimitsResult:
    current = plugin_sandbox.limits
    return LimitsResult(
        cpu_seconds=current.cpu_seconds,
        memory_bytes=current.memory_bytes,
        wall_timeout_seconds=current.wall_timeout_seconds,
    )
