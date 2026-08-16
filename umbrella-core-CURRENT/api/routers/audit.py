"""
api/routers/audit.py — Audit log read endpoints.

GET /api/v1/audit             — paginated audit log (filter by actor_type/action)
GET /api/v1/audit/{action}    — filter by action type (back-compat path shape)

Phase 0 note: this router no longer implements the query itself. Both routes
now delegate to the `platform.audit.search` capability (capabilities/system.py)
through the Capability Registry — the exact same query logic is now also
reachable via `POST /api/v1/capabilities/platform.audit.search/invoke`, the
CLI (`umbrella platform audit search`), and, in a later phase, the AI Tool
Registry, with no duplicated implementation between them.

The audit log remains read-only via API — writes only ever happen via
`registry.audit.record_audit_event`, called from `CapabilityRegistry.call()`.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.permissions import require_permission
from database import get_db
from registry.context import CallContext
from registry.registry import registry

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("")
async def list_audit_log(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    actor_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_permission("audit.view")),
) -> dict:
    """
    Return paginated audit log, newest first.
    Optionally filter by actor_type (staff | plugin | bot | system | ai).
    'total' reflects the full matching row count, not just the current page.
    """
    ctx = await CallContext.from_web_auth(auth, db, source="rest")
    result = await registry.call(
        "platform.audit.search",
        ctx,
        {"limit": limit, "offset": offset, "actor_type": actor_type},
    )
    return result.model_dump(mode="json")


@router.get("/{action}")
async def list_audit_log_by_action(
    action: str,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_permission("audit.view")),
) -> dict:
    """
    Return paginated audit log filtered by action type, newest first.
    Example actions: settings.update, role.create, player.ban, etc.
    'total' reflects the full matching row count for this action type.
    """
    ctx = await CallContext.from_web_auth(auth, db, source="rest")
    result = await registry.call(
        "platform.audit.search",
        ctx,
        {"limit": limit, "offset": offset, "action": action},
    )
    payload = result.model_dump(mode="json")
    # Preserve the pre-Phase-0 response shape, which included `action` as a
    # top-level field on this specific route (unlike the list-all route above).
    payload["action"] = action
    return payload
