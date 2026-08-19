"""
database/redis_client.py — Async Redis client + FastAPI dependency.

Mirrors database/engine.py's get_db pattern. Constructed from the same
settings.redis_url the rest of the app already uses (see main.py's
rate-limiter wiring and services/rate_limit_service.py).
"""
from redis.asyncio import Redis, from_url

from config.settings import get_settings

settings = get_settings()

# Module-level client — Redis connections are cheap/pooled internally,
# so (like the rate limiter's client) we don't open a new one per request.
redis_client: Redis = from_url(settings.redis_url)


async def get_redis() -> Redis:
    """
    FastAPI dependency. Yields the shared async Redis client.

    Usage:
        @router.get("/")
        async def endpoint(redis: Redis = Depends(get_redis)):
            ...
    """
    yield redis_client
