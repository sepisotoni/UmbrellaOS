"""
tests/test_health.py — Tests for GET /health

Health is public (no auth required).
"""
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest
from redis.exceptions import RedisError

from database import get_redis
from main import app


@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_shape(client):
    response = await client.get("/health")
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "database" in data
    assert "service" in data


@pytest.mark.asyncio
async def test_health_service_name(client):
    response = await client.get("/health")
    assert response.json()["service"] == "umbrella-core"


@pytest.mark.asyncio
async def test_health_no_auth_required(client):
    """Health endpoint must not require any API key."""
    response = await client.get("/health")
    assert response.status_code != 401


@pytest.mark.asyncio
async def test_health_redis_reachable(client):
    """When Redis responds to PING, health reports it connected and overall ok."""
    fake_redis = fakeredis.aioredis.FakeRedis()

    async def override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = override_get_redis
    try:
        response = await client.get("/health")
        data = response.json()
        assert data["redis"] == "connected"
        assert data["status"] == "ok"
    finally:
        del app.dependency_overrides[get_redis]
        await fake_redis.aclose()


@pytest.mark.asyncio
async def test_health_redis_unreachable(client):
    """When Redis PING raises RedisError, health reports it unreachable and degraded."""
    mock_redis = AsyncMock()
    mock_redis.ping.side_effect = RedisError("connection refused")

    async def override_get_redis():
        yield mock_redis

    app.dependency_overrides[get_redis] = override_get_redis
    try:
        response = await client.get("/health")
        data = response.json()
        assert data["redis"] == "unreachable"
        assert data["status"] == "degraded"
    finally:
        del app.dependency_overrides[get_redis]
