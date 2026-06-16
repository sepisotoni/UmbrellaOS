"""
tests/test_health.py — Tests for GET /health

Health is public (no auth required).
"""
import pytest


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
