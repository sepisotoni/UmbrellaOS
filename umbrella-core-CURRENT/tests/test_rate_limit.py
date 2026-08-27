"""
tests/test_rate_limit.py — Unit tests for RateLimiter using a mock Redis client.

These tests exercise the fixed-window algorithm and the Bug #7 TTL fix
(expire with nx=True) without requiring a live Redis instance.
The HTTP-layer rate limit integration is covered indirectly by all other
test_*.py files — those use _NoOpRateLimiter from conftest and confirm
the middleware doesn't interfere with normal flows.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, call

from services.rate_limit_service import RateLimiter, RateLimitResult


@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=30)
    return redis


@pytest.fixture
def limiter(mock_redis):
    return RateLimiter(mock_redis)


# ------------------------------------------------------------------
# Basic allow/deny
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_request_allowed(limiter, mock_redis):
    mock_redis.incr.return_value = 1
    result = await limiter.check("127.0.0.1", limit=10, window_seconds=60)
    assert result.allowed is True
    assert result.remaining == 9
    assert result.limit == 10


@pytest.mark.asyncio
async def test_request_at_limit_allowed(limiter, mock_redis):
    mock_redis.incr.return_value = 10
    result = await limiter.check("127.0.0.1", limit=10, window_seconds=60)
    assert result.allowed is True
    assert result.remaining == 0


@pytest.mark.asyncio
async def test_request_over_limit_denied(limiter, mock_redis):
    mock_redis.incr.return_value = 11
    result = await limiter.check("127.0.0.1", limit=10, window_seconds=60)
    assert result.allowed is False
    assert result.remaining == 0


# ------------------------------------------------------------------
# Bug #7 fix — expire called with nx=True every request
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expire_called_on_first_request(limiter, mock_redis):
    """expire must be called even on the first request (count=1)."""
    mock_redis.incr.return_value = 1
    await limiter.check("127.0.0.1", limit=10, window_seconds=60)
    mock_redis.expire.assert_called_once_with(
        "umbrella:ratelimit:127.0.0.1:60", 60, nx=True
    )


@pytest.mark.asyncio
async def test_expire_called_on_subsequent_requests(limiter, mock_redis):
    """expire must be called on every request, not just count==1.

    This is the Bug #7 fix: the old code only called expire on count==1,
    leaving a permanent key if that single EXPIRE call was lost.
    """
    mock_redis.incr.return_value = 5
    await limiter.check("127.0.0.1", limit=10, window_seconds=60)
    mock_redis.expire.assert_called_once_with(
        "umbrella:ratelimit:127.0.0.1:60", 60, nx=True
    )


@pytest.mark.asyncio
async def test_expire_uses_nx_flag(limiter, mock_redis):
    """nx=True means 'only set TTL if the key has no current expiry'.

    Running windows are unaffected (expire is a no-op when TTL exists).
    Wedged keys (TTL=-1 from a prior crash) get healed.
    """
    mock_redis.incr.return_value = 3
    await limiter.check("10.0.0.1", limit=100, window_seconds=30)

    _, kwargs = mock_redis.expire.call_args
    assert kwargs.get("nx") is True, (
        "expire must use nx=True so running windows aren't reset and wedged "
        "keys self-heal (Bug #7 fix)"
    )


@pytest.mark.asyncio
async def test_key_includes_window_seconds(limiter, mock_redis):
    """Different window sizes get different Redis keys — no cross-contamination."""
    mock_redis.incr.return_value = 1
    await limiter.check("1.2.3.4", limit=10, window_seconds=60)
    await limiter.check("1.2.3.4", limit=10, window_seconds=3600)

    keys_used = [c.args[0] for c in mock_redis.incr.call_args_list]
    assert "umbrella:ratelimit:1.2.3.4:60" in keys_used
    assert "umbrella:ratelimit:1.2.3.4:3600" in keys_used
    assert keys_used[0] != keys_used[1]


# ------------------------------------------------------------------
# TTL / reset_seconds handling
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reset_seconds_from_ttl(limiter, mock_redis):
    mock_redis.incr.return_value = 1
    mock_redis.ttl.return_value = 45
    result = await limiter.check("x", limit=10, window_seconds=60)
    assert result.reset_seconds == 45


@pytest.mark.asyncio
async def test_reset_seconds_fallback_when_ttl_missing(limiter, mock_redis):
    """TTL of -1 (no expiry set) or -2 (key missing) → fall back to window_seconds."""
    mock_redis.incr.return_value = 1
    mock_redis.ttl.return_value = -1
    result = await limiter.check("x", limit=10, window_seconds=60)
    assert result.reset_seconds == 60


@pytest.mark.asyncio
async def test_result_is_frozen_dataclass(limiter, mock_redis):
    """RateLimitResult is frozen — callers can't mutate it."""
    mock_redis.incr.return_value = 1
    result = await limiter.check("x", limit=5, window_seconds=10)
    with pytest.raises((AttributeError, TypeError)):
        result.allowed = False  # type: ignore[misc]


# ------------------------------------------------------------------
# Key prefix customisation
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_custom_key_prefix(mock_redis):
    limiter = RateLimiter(mock_redis, key_prefix="myapp:rl")
    mock_redis.incr.return_value = 1
    await limiter.check("user:42", limit=10, window_seconds=60)
    mock_redis.incr.assert_called_once_with("myapp:rl:user:42:60")
