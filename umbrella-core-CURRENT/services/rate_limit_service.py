"""
services/rate_limit_service.py — Redis-backed fixed-window rate limiting.

A fixed window (not sliding/token-bucket) is a deliberate simplicity choice
for Phase 3: one INCR + one conditional EXPIRE per check, O(1) and easy to
reason about, at the cost of allowing up to 2x `limit` requests across a
window boundary in the worst case (a burst right at the end of one window
and right at the start of the next). That trade-off is acceptable for
"stop obvious abuse," which is this phase's actual goal — a precise sliding
window is a reasonable future upgrade if abuse patterns actually exploit
the boundary case, not something to build preemptively against a
hypothetical.
"""
from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int


class RateLimiter:
    def __init__(self, redis_client: Redis, key_prefix: str = "umbrella:ratelimit"):
        self._redis = redis_client
        self._key_prefix = key_prefix

    async def check(self, identifier: str, limit: int, window_seconds: int) -> RateLimitResult:
        """
        Increment this identifier's counter for the current window and
        report whether it's still within `limit`. The counter's TTL is set
        only on the increment that creates the key (count == 1) — later
        increments within the same window don't reset the window's expiry,
        which would let a busy client keep its window open indefinitely.
        """
        key = f"{self._key_prefix}:{identifier}:{window_seconds}"
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, window_seconds)

        ttl = await self._redis.ttl(key)
        reset_seconds = ttl if ttl and ttl > 0 else window_seconds

        return RateLimitResult(
            allowed=count <= limit,
            limit=limit,
            remaining=max(0, limit - count),
            reset_seconds=reset_seconds,
        )
