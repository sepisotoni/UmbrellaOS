"""
tests/test_rate_limit_service.py — Tests for services/rate_limit_service.py
using fakeredis's async client, a real Redis-protocol-compatible
implementation (not a hand-rolled fake), the same class of infrastructure
test double used throughout this project (aiosqlite standing in for
Postgres, httpx.MockTransport for HTTP).
"""
import fakeredis
import pytest

from services.rate_limit_service import RateLimiter


@pytest.fixture
def redis_client():
    return fakeredis.aioredis.FakeRedis()


@pytest.mark.asyncio
async def test_allows_requests_within_limit(redis_client):
    limiter = RateLimiter(redis_client)
    for _ in range(5):
        result = await limiter.check("client-a", limit=5, window_seconds=60)
        assert result.allowed is True
    assert result.remaining == 0


@pytest.mark.asyncio
async def test_denies_requests_over_limit(redis_client):
    limiter = RateLimiter(redis_client)
    for _ in range(5):
        await limiter.check("client-b", limit=5, window_seconds=60)
    result = await limiter.check("client-b", limit=5, window_seconds=60)
    assert result.allowed is False
    assert result.remaining == 0


@pytest.mark.asyncio
async def test_different_identifiers_have_independent_counters(redis_client):
    limiter = RateLimiter(redis_client)
    for _ in range(5):
        await limiter.check("client-c", limit=5, window_seconds=60)
    # A different identifier must not be affected by client-c's usage.
    result = await limiter.check("client-d", limit=5, window_seconds=60)
    assert result.allowed is True
    assert result.remaining == 4


@pytest.mark.asyncio
async def test_reset_seconds_reflects_window_ttl(redis_client):
    limiter = RateLimiter(redis_client)
    result = await limiter.check("client-e", limit=5, window_seconds=30)
    assert 0 < result.reset_seconds <= 30


@pytest.mark.asyncio
async def test_window_expiry_resets_the_counter(redis_client):
    limiter = RateLimiter(redis_client)
    await limiter.check("client-f", limit=2, window_seconds=1)
    await limiter.check("client-f", limit=2, window_seconds=1)
    blocked = await limiter.check("client-f", limit=2, window_seconds=1)
    assert blocked.allowed is False

    # Manually expire the key to simulate window passing, rather than
    # sleeping in a test — fakeredis supports TTL semantics but a real
    # sleep would make this test slow and flaky under load.
    await redis_client.delete("umbrella:ratelimit:client-f:1")
    result = await limiter.check("client-f", limit=2, window_seconds=1)
    assert result.allowed is True
