"""
api/routers/audit.py — Audit log read endpoints.

GET /api/v1/audit             — paginated audit log (filter by actor_type)
GET /api/v1/audit/{action}    — filter by action type

The audit log is read-only via API. Writes happen internally via services.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from database import get_db
from models.audit_log import AuditLog
from api.middleware.auth import require_admin_key

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


def _entry_to_dict(e: AuditLog) -> dict:
    return {
        "id": e.id,
        "actor": e.actor,
        "actor_type": e.actor_type,
        "action": e.action,
        "target": e.target,
        "details": e.details_json,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("")
async def list_audit_log(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    actor_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> dict:
    """
    Return paginated audit log, newest first.
    Optionally filter by actor_type (staff | plugin | bot | system | ai).
    'total' reflects the full matching row count, not just the current page.
    """
    # Build base query (with optional filter)
    base_query = select(AuditLog)
    if actor_type:
        base_query = base_query.where(AuditLog.actor_type == actor_type)

    # TD-05 fix: count the full matching set, not len(page)
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    # Fetch the requested page
    page_query = base_query.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
    result = await db.execute(page_query)
    entries = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "entries": [_entry_to_dict(e) for e in entries],
    }


@router.get("/{action}")
async def list_audit_log_by_action(
    action: str,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> dict:
    """
    Return paginated audit log filtered by action type, newest first.
    Example actions: settings.update, role.create, player.ban, etc.
    'total' reflects the full matching row count for this action type.
    """
    base_query = select(AuditLog).where(AuditLog.action == action)

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    page_query = base_query.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
    result = await db.execute(page_query)
    entries = result.scalars().all()

    return {
        "total": total,
        "action": action,
        "limit": limit,
        "offset": offset,
        "entries": [_entry_to_dict(e) for e in entries],
    }
