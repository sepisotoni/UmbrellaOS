"""
tests/test_auth.py — Tests for authentication enforcement.

Every guarded route must return 401 on missing or wrong key,
and 2xx on the correct key.
"""
import pytest
from tests.conftest import ADMIN_HEADERS, WRONG_HEADERS

# Routes that require X-Admin-Key
ADMIN_ROUTES = [
    ("GET",   "/api/v1/settings"),
    ("GET",   "/api/v1/settings/server.name"),
    ("GET",   "/api/v1/roles"),
    ("GET",   "/api/v1/roles/permissions"),
    ("GET",   "/api/v1/audit"),
    ("GET",   "/api/v1/audit/settings.update"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
async def test_missing_key_returns_401(client, method, path):
    response = await client.request(method, path)
    assert response.status_code == 401, f"{method} {path} should return 401 without key"


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
async def test_wrong_key_returns_401(client, method, path):
    response = await client.request(method, path, headers=WRONG_HEADERS)
    assert response.status_code == 401, f"{method} {path} should return 401 with wrong key"


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
async def test_correct_key_not_401(client, method, path):
    response = await client.request(method, path, headers=ADMIN_HEADERS)
    assert response.status_code != 401, f"{method} {path} should not return 401 with correct key"
