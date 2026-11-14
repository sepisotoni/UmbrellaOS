"""
tests/test_health.py — Tests for GET /health

Health is public (no auth required).
"""

from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest
import pytest_asyncio
from redis.exceptions import RedisError

from database import get_redis
from main import app


@pytest_asyncio.fixture(autouse=True)
async def use_loop_local_redis():
    """Keep health tests from reusing the production Redis pool across test loops."""
    fake_redis = fakeredis.aioredis.FakeRedis()

    async def override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = override_get_redis
    yield
    app.dependency_overrides.pop(get_redis, None)
    await fake_redis.aclose()


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
async def test_health_uptime_seconds_present_and_non_negative(client):
    """
    AUDIT-2026-08-30: uptime_seconds added for the dashboard's sidebar
    core-status chip (previously absent entirely).
    """
    response = await client.get("/health")
    data = response.json()
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0


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


@pytest.mark.asyncio
async def test_required_migration_failure_prevents_startup_and_readiness(
    monkeypatch,
):
    """A failed required migration must abort lifespan before startup completes."""
    import main as main_module
    from alembic import command as alembic_command

    def fail_migration(config, revision):
        raise RuntimeError("migration failed")

    monkeypatch.setattr(main_module, "validate_secrets", lambda settings: None)
    monkeypatch.setattr(alembic_command, "upgrade", fail_migration)
    create_tables = AsyncMock()
    monkeypatch.setattr(main_module, "create_tables", create_tables)

    startup_completed = False
    with pytest.raises(RuntimeError, match="migration failed"):
        async with main_module.lifespan(app):
            startup_completed = True

    assert startup_completed is False
    create_tables.assert_not_awaited()
