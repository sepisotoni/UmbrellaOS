"""
api/routers/audit.py — Audit log read endpoints.

GET /api/v1/audit             — paginated audit log
GET /api/v1/audit/{action}    — filter by action type

The audit log is read-only via API. Writes happen internally via services.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database import get_db
from models.audit_log import AuditLog
from api.middleware.auth import require_admin_key

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


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
    """
    query = select(AuditLog).order_by(desc(AuditLog.created_at))
    if actor_type:
        query = query.where(AuditLog.actor_type == actor_type)

    result = await db.execute(query.limit(limit).offset(offset))
    entries = result.scalars().all()

    return {
        "total": len(entries),
        "limit": limit,
        "offset": offset,
        "entries": [
            {
                "id": e.id,
                "actor": e.actor,
                "actor_type": e.actor_type,
                "action": e.action,
                "target": e.target,
                "details": e.details_json,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
    }
