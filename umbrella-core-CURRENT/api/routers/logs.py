"""
api/routers/logs.py — GET /api/v1/logs, aggregated log search (Phase 9,
item 3). Thin delegate to `platform.observability.search_logs`, same
pattern as api/routers/audit.py.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.permissions import require_permission
from database import get_db
from registry.context import CallContext
from registry.registry import registry

router = APIRouter(prefix="/api/v1/logs", tags=["observability"])


@router.get("")
async def search_logs(
    query: str | None = Query(default=None),
    level: str | None = Query(default=None),
    source: str | None = Query(default=None),
    trace_id: str | None = Query(default=None),
    limit: int = Query(default=50, le=500),
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_permission("observability.logs.view")),
) -> dict:
    ctx = await CallContext.from_web_auth(auth, db, source="rest")
    result = await registry.call(
        "platform.observability.search_logs",
        ctx,
        {"query": query, "level": level, "source": source, "trace_id": trace_id, "limit": limit},
    )
    return result.model_dump(mode="json")
