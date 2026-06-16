"""
api/routers/health.py — Health check endpoint.

GET /health — public, no auth required.
Returns database connectivity status and app version.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Returns 200 if Core is running and the database is reachable.
    Used by the plugin heartbeat, load balancers, and monitoring.
    """
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if db_ok else "degraded",
        "version": "1.0.0",
        "database": "connected" if db_ok else "unreachable",
        "service": "umbrella-core",
    }
