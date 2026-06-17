"""
tests/test_auth.py — Tests for authentication enforcement.

Every guarded route must return 401 on missing or wrong key,
and 2xx on the correct key.
"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from tests.conftest import ADMIN_HEADERS, WRONG_HEADERS
from models import User, Session
from models.permissions import Role

# Routes that require X-Admin-Key only (not session)
ADMIN_ROUTES = [
    ("GET",   "/api/v1/settings"),
    ("GET",   "/api/v1/settings/server.name"),
    ("GET",   "/api/v1/roles"),
    ("GET",   "/api/v1/roles/permissions"),
    ("GET",   "/api/v1/audit"),
    ("GET",   "/api/v1/audit/settings.update"),
]

# Route migrated to admin-key-or-session auth
SESSION_ROUTE = ("GET", "/api/v1/players")


@pytest_asyncio.fixture
async def bearer_headers(db_session):
    """Create a valid user session and return Bearer auth headers."""
    async with db_session() as db:
        owner_role = await db.scalar(select(Role).where(Role.name == "owner"))
        user = User(discord_id="999", username="sessionuser", role_id=owner_role.id)
        db.add(user)
        await db.flush()
        token = "valid-test-session-token"
        session = Session(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(session)
        await db.commit()
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def expired_bearer_headers(db_session):
    """Create an expired session and return Bearer auth headers."""
    async with db_session() as db:
        user = User(discord_id="998", username="expireduser")
        db.add(user)
        await db.flush()
        token = "expired-test-session-token"
        session = Session(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.add(session)
        await db.commit()
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def revoked_bearer_headers(db_session):
    """Create a revoked session and return Bearer auth headers."""
    async with db_session() as db:
        user = User(discord_id="997", username="revokeduser")
        db.add(user)
        await db.flush()
        token = "revoked-test-session-token"
        session = Session(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            revoked=True,
        )
        db.add(session)
        await db.commit()
    return {"Authorization": f"Bearer {token}"}


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


@pytest.mark.asyncio
async def test_valid_bearer_token_grants_access(client, bearer_headers):
    method, path = SESSION_ROUTE
    response = await client.request(method, path, headers=bearer_headers)
    assert response.status_code != 401, f"{method} {path} should accept valid Bearer token"


@pytest.mark.asyncio
async def test_expired_session_returns_401(client, expired_bearer_headers):
    method, path = SESSION_ROUTE
    response = await client.request(method, path, headers=expired_bearer_headers)
    assert response.status_code == 401, f"{method} {path} should return 401 for expired session"


@pytest.mark.asyncio
async def test_revoked_session_returns_401(client, revoked_bearer_headers):
    method, path = SESSION_ROUTE
    response = await client.request(method, path, headers=revoked_bearer_headers)
    assert response.status_code == 401, f"{method} {path} should return 401 for revoked session"


@pytest.mark.asyncio
async def test_missing_auth_returns_401_on_session_route(client):
    method, path = SESSION_ROUTE
    response = await client.request(method, path)
    assert response.status_code == 401, f"{method} {path} should return 401 without auth"


@pytest.mark.asyncio
async def test_admin_key_still_works_on_session_route(client):
    method, path = SESSION_ROUTE
    response = await client.request(method, path, headers=ADMIN_HEADERS)
    assert response.status_code != 401, f"{method} {path} should still accept X-Admin-Key"

