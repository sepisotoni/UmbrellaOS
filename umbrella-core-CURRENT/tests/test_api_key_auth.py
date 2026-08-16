"""
tests/test_api_key_auth.py — Tests for api/middleware/api_key_auth.py.

The key regression this guards against: a request authenticating via a
valid X-Api-Key header must succeed even though it carries no
Authorization/X-Admin-Key header at all — an earlier version of this
dependency declared `require_admin_key_or_session` via FastAPI's Depends(),
which evaluates eagerly and would have rejected exactly this request before
the API-key check ever ran. Caught before shipping by reasoning through
FastAPI's dependency resolution order, then confirmed here.
"""
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from api.middleware.api_key_auth import require_capability_auth
from database import get_db
from models.api_key import ApiKey
from models.user import User
from services.api_key_service import ApiKeyService


def _build_app(db_session) -> FastAPI:
    from api.middleware.errors import register_error_handlers

    app = FastAPI()
    register_error_handlers(app)

    async def override_get_db():
        async with db_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    @app.get("/whoami")
    async def whoami(auth=Depends(require_capability_auth)):
        if isinstance(auth, ApiKey):
            return {"kind": "api_key", "id": auth.id, "permissions": auth.permissions}
        if isinstance(auth, str):
            return {"kind": "admin_key"}
        if isinstance(auth, User):
            return {"kind": "user", "id": auth.id}
        return {"kind": "unknown"}

    return app


@pytest.mark.asyncio
async def test_valid_api_key_authenticates_without_any_other_header(db_session, monkeypatch):
    async with db_session() as db:
        _, plaintext = await ApiKeyService.create_api_key(db, "bot-key", ["hosting.server.view"])
        await db.commit()

    app = _build_app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Deliberately no Authorization header and no X-Admin-Key — this is
        # exactly the request shape the eager-Depends() bug would have
        # rejected.
        response = await client.get("/whoami", headers={"X-Api-Key": plaintext})

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "api_key"
    assert body["permissions"] == ["hosting.server.view"]


@pytest.mark.asyncio
async def test_invalid_api_key_is_rejected_even_with_no_fallback_header(db_session):
    app = _build_app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/whoami", headers={"X-Api-Key": "umbr_totally-not-real"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_missing_api_key_falls_back_to_admin_key(db_session):
    from config import get_settings

    settings = get_settings()

    app = _build_app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/whoami", headers={"X-Admin-Key": settings.admin_key})

    assert response.status_code == 200
    assert response.json()["kind"] == "admin_key"


@pytest.mark.asyncio
async def test_no_auth_at_all_is_rejected(db_session):
    app = _build_app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/whoami")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_key_header_takes_precedence_over_admin_key(db_session):
    """An X-Api-Key header, even an invalid one, must not silently fall
    through to a valid X-Admin-Key also present on the same request — the
    two auth methods are mutually exclusive per-request, not a priority
    chain that tries both."""
    from config import get_settings

    settings = get_settings()
    app = _build_app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/whoami",
            headers={"X-Api-Key": "umbr_invalid", "X-Admin-Key": settings.admin_key},
        )
    assert response.status_code == 401
