"""
capabilities/observability.py — Phase 9 read capabilities: aggregated log
search and security event/threat-alert visibility. Follows the same
migration pattern capabilities/system.py established for
`platform.audit.search` — the query logic lives here once, reachable via
REST, CLI, and the AI Tool Registry with no duplication between them.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select, or_

from models.log_entry import LogEntry
from models.security_event import SecurityEvent
from registry.context import CallContext
from registry.decorator import capability


# --------------------------------------------------------------------------
# platform.observability.search_logs
# --------------------------------------------------------------------------


class LogSearchParams(BaseModel):
    query: str | None = Field(default=None, description="Substring match against message/logger name.")
    level: str | None = Field(default=None, description="Exact level, e.g. ERROR.")
    source: str | None = Field(default=None, description="Originating process, e.g. umbrella-core.")
    trace_id: str | None = Field(default=None, description="Filter to one request's trace.")
    limit: int = Field(default=50, ge=1, le=500)


class LogEntryResult(BaseModel):
    id: str
    created_at: str | None
    level: str
    logger_name: str
    message: str
    source: str
    trace_id: str | None


class LogSearchResult(BaseModel):
    entries: list[LogEntryResult]


@capability(
    name="platform.observability.search_logs",
    summary="Full-text-ish search over aggregated umbrella-core log records.",
    params_model=LogSearchParams,
    result_model=LogSearchResult,
    required_permission="observability.logs.view",
    destructive=False,
    reversible=True,
    audited=False,  # reading logs is not itself an action worth auditing, same reasoning as audit.search
)
async def search_logs(ctx: CallContext, params: LogSearchParams) -> LogSearchResult:
    stmt = select(LogEntry).order_by(desc(LogEntry.created_at)).limit(params.limit)
    if params.query:
        stmt = stmt.where(
            or_(LogEntry.message.ilike(f"%{params.query}%"), LogEntry.logger_name.ilike(f"%{params.query}%"))
        )
    if params.level:
        stmt = stmt.where(LogEntry.level == params.level.upper())
    if params.source:
        stmt = stmt.where(LogEntry.source == params.source)
    if params.trace_id:
        stmt = stmt.where(LogEntry.trace_id == params.trace_id)

    result = await ctx.db.execute(stmt)
    rows = result.scalars().all()
    return LogSearchResult(
        entries=[
            LogEntryResult(
                id=row.id,
                created_at=row.created_at.isoformat() if row.created_at else None,
                level=row.level,
                logger_name=row.logger_name,
                message=row.message,
                source=row.source,
                trace_id=row.trace_id,
            )
            for row in rows
        ]
    )


# --------------------------------------------------------------------------
# platform.security.list_events
# --------------------------------------------------------------------------


class SecurityEventListParams(BaseModel):
    event_type: str | None = Field(default=None, description="auth_failure | rate_limit_violation | sandbox_violation")
    source_ip: str | None = Field(default=None)
    limit: int = Field(default=50, ge=1, le=500)


class SecurityEventResult(BaseModel):
    id: str
    created_at: str | None
    event_type: str
    source_ip: str | None
    identifier: str | None
    detail: str


class SecurityEventListResult(BaseModel):
    entries: list[SecurityEventResult]
    total: int


@capability(
    name="platform.security.list_events",
    summary="List recorded security events (auth failures, rate-limit violations, sandbox violations).",
    params_model=SecurityEventListParams,
    result_model=SecurityEventListResult,
    required_permission="security.events.view",
    destructive=False,
    reversible=True,
    audited=False,
)
async def list_security_events(ctx: CallContext, params: SecurityEventListParams) -> SecurityEventListResult:
    base_query = select(SecurityEvent)
    if params.event_type:
        base_query = base_query.where(SecurityEvent.event_type == params.event_type)
    if params.source_ip:
        base_query = base_query.where(SecurityEvent.source_ip == params.source_ip)

    count_result = await ctx.db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_result.scalar_one()

    page_query = base_query.order_by(desc(SecurityEvent.created_at)).limit(params.limit)
    result = await ctx.db.execute(page_query)
    rows = result.scalars().all()

    return SecurityEventListResult(
        entries=[
            SecurityEventResult(
                id=row.id,
                created_at=row.created_at.isoformat() if row.created_at else None,
                event_type=row.event_type,
                source_ip=row.source_ip,
                identifier=row.identifier,
                detail=row.detail,
            )
            for row in rows
        ],
        total=total,
    )
