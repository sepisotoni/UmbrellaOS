"""
capabilities/system.py — Platform-level introspection capabilities.

These are the first capabilities registered through Phase 0's Capability
Registry, and deliberately simple ones: `whoami` proves the identity/
permission path end-to-end, and `audit.search` proves the pattern for
*migrating* an existing hand-written router onto the registry (see
api/routers/audit.py, which now delegates to `search_audit_log` below
instead of duplicating its query logic).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select

from models.audit_log import AuditLog
from registry.context import CallContext
from registry.decorator import capability


# --------------------------------------------------------------------------
# platform.system.whoami
# --------------------------------------------------------------------------


class WhoAmIParams(BaseModel):
    """No input required — this capability only reads the calling context."""


class WhoAmIResult(BaseModel):
    actor_id: str
    actor_type: str
    source: str
    is_superuser: bool
    permissions: list[str]


@capability(
    name="platform.system.whoami",
    summary="Return the identity and effective permissions of the calling actor.",
    params_model=WhoAmIParams,
    result_model=WhoAmIResult,
    required_permission=None,  # any authenticated actor may introspect itself
    destructive=False,
    reversible=True,
    audited=False,  # pure introspection — an audit row here is noise, not signal
)
async def whoami(ctx: CallContext, params: WhoAmIParams) -> WhoAmIResult:
    """
    Exists primarily to prove the CallContext/permission path end-to-end
    across every adapter: the same handler answers "who am I" whether it's
    invoked over REST, the CLI, or (Phase 5) an AI session — and the answer
    it gives is always derived from the actor the *caller* authenticated as,
    never a capability-specific notion of identity.
    """
    return WhoAmIResult(
        actor_id=ctx.actor_id,
        actor_type=ctx.actor_type,
        source=ctx.source,
        is_superuser=ctx.is_superuser,
        permissions=["*"] if ctx.is_superuser else sorted(ctx.permissions),
    )


# --------------------------------------------------------------------------
# platform.audit.search
# --------------------------------------------------------------------------


class AuditSearchParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    actor_type: str | None = Field(
        default=None, description="Filter by staff | plugin | bot | system | ai."
    )
    action: str | None = Field(
        default=None, description="Filter by exact action name, e.g. 'player.ban'."
    )


class AuditEntryResult(BaseModel):
    id: str
    actor: str
    actor_type: str
    action: str
    target: str | None
    details: str
    created_at: str | None


class AuditSearchResult(BaseModel):
    entries: list[AuditEntryResult]
    total: int
    limit: int
    offset: int


@capability(
    name="platform.audit.search",
    summary="Search the platform audit log with pagination and filtering.",
    params_model=AuditSearchParams,
    result_model=AuditSearchResult,
    required_permission="audit.view",
    destructive=False,
    reversible=True,
    audited=False,  # reading the audit log is not itself an action worth auditing
)
async def search_audit_log(ctx: CallContext, params: AuditSearchParams) -> AuditSearchResult:
    """
    Query logic ported unchanged from the pre-Phase-0 `api/routers/audit.py`
    (both its list-all and filter-by-action endpoints, now unified into one
    capability with optional filters) — this is a migration of existing,
    already-correct business logic onto the registry, not a reimplementation.
    """
    base_query = select(AuditLog)
    if params.actor_type:
        base_query = base_query.where(AuditLog.actor_type == params.actor_type)
    if params.action:
        base_query = base_query.where(AuditLog.action == params.action)

    count_result = await ctx.db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    page_query = (
        base_query.order_by(desc(AuditLog.created_at))
        .limit(params.limit)
        .offset(params.offset)
    )
    result = await ctx.db.execute(page_query)
    rows = result.scalars().all()

    return AuditSearchResult(
        entries=[
            AuditEntryResult(
                id=row.id,
                actor=row.actor,
                actor_type=row.actor_type,
                action=row.action,
                target=row.target,
                details=row.details_json,
                created_at=row.created_at.isoformat() if row.created_at else None,
            )
            for row in rows
        ],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )
