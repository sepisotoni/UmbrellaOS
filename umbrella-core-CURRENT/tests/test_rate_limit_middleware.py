"""
tests/test_rate_limit_middleware.py — Tests for api/middleware/rate_limit.py
against a minimal, isolated FastAPI app (not the full application) plus
fakeredis, so this middleware's behavior is verified independently of the
rest of umbrella-core's dependency graph.
"""
import fakeredis
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.middleware.rate_limit import RateLimitMiddleware
from services.rate_limit_service import RateLimiter


def _build_app(
    requests_per_window: int = 3,
    window_seconds: int = 60,
    api_key_requests_per_window: int = 300,
    api_key_window_seconds: int = 60,
) -> FastAPI:
    app = FastAPI()

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/protected")
    async def protected():
        return {"ok": True}

    limiter = RateLimiter(fakeredis.aioredis.FakeRedis())
    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=limiter,
        requests_per_window=requests_per_window,
        window_seconds=window_seconds,
        api_key_requests_per_window=api_key_requests_per_window,
        api_key_window_seconds=api_key_window_seconds,
    )
    return app


@pytest.mark.asyncio
async def test_requests_within_limit_succeed():
    app = _build_app(requests_per_window=3)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(3):
            response = await client.get("/protected")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_requests_over_limit_return_429_with_retry_after():
    app = _build_app(requests_per_window=2)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/protected")
        await client.get("/protected")
        blocked = await client.get("/protected")

        assert blocked.status_code == 429
        assert blocked.json()["code"] == "RATE_LIMITED"
        assert "Retry-After" in blocked.headers


@pytest.mark.asyncio
async def test_exempt_path_is_never_rate_limited():
    app = _build_app(requests_per_window=1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(5):
            response = await client.get("/healthz")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_headers_present_on_allowed_response():
    app = _build_app(requests_per_window=5)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/protected")
        assert response.headers["X-RateLimit-Limit"] == "5"
        assert response.headers["X-RateLimit-Remaining"] == "4"


@pytest.mark.asyncio
async def test_fails_open_when_redis_is_unreachable():
    """
    The exact regression this test guards against: wiring this middleware
    into main.py with a real (but in this environment unreachable) Redis
    client broke every existing test, because the initial version let
    redis.exceptions.ConnectionError propagate. Fixed to fail open; this
    test points a RateLimiter at a real redis.asyncio client for a host
    nothing is listening on, and asserts the request still succeeds.
    """
    import redis.asyncio as redis_asyncio

    app = FastAPI()

    @app.get("/protected")
    async def protected():
        return {"ok": True}

    unreachable_limiter = RateLimiter(redis_asyncio.from_url("redis://localhost:1"))
    app.add_middleware(RateLimitMiddleware, rate_limiter=unreachable_limiter, requests_per_window=1)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/protected")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_key_over_its_own_limit_returns_429_even_with_ip_budget_left():
    """Two different callers sharing one IP (a NAT/proxy scenario) but
    using two different API keys must not share one bucket — the per-IP
    limit here is generous specifically so this test isolates the new
    per-key check."""
    app = _build_app(requests_per_window=100, api_key_requests_per_window=2)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"X-Api-Key": "umbr_sometestkey"}
        await client.get("/protected", headers=headers)
        await client.get("/protected", headers=headers)
        blocked = await client.get("/protected", headers=headers)

        assert blocked.status_code == 429
        assert blocked.json()["code"] == "RATE_LIMITED"
        assert "Retry-After" in blocked.headers


@pytest.mark.asyncio
async def test_different_api_keys_get_independent_buckets():
    app = _build_app(requests_per_window=100, api_key_requests_per_window=1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first_key_response = await client.get("/protected", headers={"X-Api-Key": "umbr_keyone"})
        second_key_response = await client.get("/protected", headers={"X-Api-Key": "umbr_keytwo"})

        assert first_key_response.status_code == 200
        assert second_key_response.status_code == 200


@pytest.mark.asyncio
async def test_requests_without_api_key_are_unaffected_by_api_key_limit():
    app = _build_app(requests_per_window=100, api_key_requests_per_window=1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(3):
            response = await client.get("/protected")
            assert response.status_code == 200
