"""
api/routers/health.py — Health check endpoint.

GET /health — public, no auth required.
Returns database + Redis connectivity status and app version.
"""
import time
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db, get_redis

router = APIRouter(tags=["health"])

# AUDIT-2026-08-30: uptime tracking added for the dashboard's sidebar
# core-status chip. Recorded at module-import time rather than in the
# app's lifespan/startup handler — the test suite's `client` fixture
# never triggers lifespan events (see main.py's comment on this), so
# anything set only in `lifespan()` would be unset in tests. Import time
# happens in both real server boot and test collection, so this stays
# accurate either way. time.monotonic() rather than a wall-clock
# timestamp — immune to system clock adjustments, which is what uptime
# measurement actually needs.
_start_time = time.monotonic()


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
        "uptime_seconds": round(time.monotonic() - _start_time),
    }
