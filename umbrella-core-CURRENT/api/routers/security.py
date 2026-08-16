"""
api/routers/security.py — GET /api/v1/security/events, recorded security
events and threat-detection signal history (Phase 9, item 4). Thin
delegate to `platform.security.list_events`, same pattern as
api/routers/audit.py.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.permissions import require_permission
from database import get_db
from registry.context import CallContext
from registry.registry import registry

router = APIRouter(prefix="/api/v1/security", tags=["security"])


@router.get("/events")
async def list_security_events(
    event_type: str | None = Query(default=None),
    source_ip: str | None = Query(default=None),
    limit: int = Query(default=50, le=500),
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_permission("security.events.view")),
) -> dict:
    ctx = await CallContext.from_web_auth(auth, db, source="rest")
    result = await registry.call(
        "platform.security.list_events",
        ctx,
        {"event_type": event_type, "source_ip": source_ip, "limit": limit},
    )
    return result.model_dump(mode="json")
