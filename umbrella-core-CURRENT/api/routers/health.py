"""
api/routers/health.py — Health check endpoint.

GET /health — public, no auth required.
Returns database + Redis connectivity status and app version.
"""
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db, get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    """
    Returns 200 if Core is running; body reflects whether the database
    and Redis are both reachable. Used by the plugin heartbeat, load
    balancers, and monitoring.
    """
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    redis_ok = False
    try:
        await redis.ping()
        redis_ok = True
    except RedisError:
        pass

    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "version": "1.0.0",
        "database": "connected" if db_ok else "unreachable",
        "redis": "connected" if redis_ok else "unreachable",
        "service": "umbrella-core",
    }
