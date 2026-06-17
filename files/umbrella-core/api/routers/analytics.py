"""
api/routers/analytics.py — Analytics endpoints.

POST /api/v1/analytics/events
GET  /api/v1/analytics/events
GET  /api/v1/analytics/players/{minecraft_uuid}
GET  /api/v1/analytics/summary
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from database import get_db
from api.middleware.auth import require_admin_key
from services import analytics_service

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class AnalyticsEventRequest(BaseModel):
    event_type: str
    minecraft_uuid: str | None = None
    data: dict | None = None


class AnalyticsEventResponse(BaseModel):
    id: str
    event_type: str
    minecraft_uuid: str | None
    created_at: str


@router.post("/events", response_model=AnalyticsEventResponse, status_code=201)
async def post_analytics_event(
    body: AnalyticsEventRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> AnalyticsEventResponse:
    """
    Record an analytics event.
    Automatically increments relevant player stats.
    """
    try:
        event = await analytics_service.record_event(
            db,
            body.event_type,
            body.minecraft_uuid,
            body.data,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    return AnalyticsEventResponse(
        id=event.id,
        event_type=event.event_type,
        minecraft_uuid=event.minecraft_uuid,
        created_at=event.created_at.isoformat(),
    )


@router.get("/events")
async def get_analytics_events(
    limit: int = Query(50, ge=1, le=200),
    event_type: str | None = None,
    minecraft_uuid: str | None = None,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Get recent analytics events.
    Supports optional filtering by event_type and minecraft_uuid.
    """
    events = await analytics_service.get_recent_events(
        db,
        limit=limit,
        event_type=event_type,
        minecraft_uuid=minecraft_uuid,
    )
    
    return events


@router.get("/players/{minecraft_uuid}")
async def get_player_analytics(
    minecraft_uuid: str,
    period: str = Query("alltime"),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Get player statistics for a specific period.
    
    Valid periods: daily, weekly, alltime
    """
    if period not in ["daily", "weekly", "alltime"]:
        raise HTTPException(status_code=400, detail="Invalid period. Must be one of: daily, weekly, alltime")
    
    stats = await analytics_service.get_player_stats(
        db,
        minecraft_uuid,
        period=period,
    )
    
    return stats


@router.get("/summary")
async def get_server_analytics_summary(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """
    Get server-wide alltime totals for all metrics.
    """
    summary = await analytics_service.get_server_summary(db)
    
    return summary
