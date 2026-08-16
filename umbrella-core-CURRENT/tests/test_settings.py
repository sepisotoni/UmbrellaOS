"""
tests/test_settings.py — Tests for settings endpoints.

GET  /api/v1/settings
GET  /api/v1/settings/{key}
PATCH /api/v1/settings/{key}
"""
import pytest
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from models import Session, User
from models.permissions import Role
from tests.conftest import ADMIN_HEADERS


async def session_headers_for_role(db_session, role_name: str, suffix: str = "") -> dict:
    """Create a User with the given seeded role plus a valid Session
    token, returning the Bearer header a REST test can use. Local copy,
    matching the existing per-test-file convention (see
    tests/registry/conftest.py's identical helper for the same rationale)."""
    discord_id = f"discord-{role_name}{suffix}"
    token = f"token-{role_name}{suffix}"
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == role_name))
        user = User(discord_id=discord_id, username=f"user_{role_name}{suffix}", role_id=role.id)
        db.add(user)
        await db.flush()
        db.add(
            Session(
                user_id=user.id,
                token=token,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
        )
        await db.commit()
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_settings_returns_list(client):
    response = await client.get("/api/v1/settings", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_list_settings_has_expected_keys(client):
    response = await client.get("/api/v1/settings", headers=ADMIN_HEADERS)
    first = response.json()[0]
    for field in ("id", "key", "value", "category", "description", "sensitive", "requires_restart"):
        assert field in first


@pytest.mark.asyncio
async def test_get_setting_by_key(client):
    response = await client.get("/api/v1/settings/server.name", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "server.name"


@pytest.mark.asyncio
async def test_get_setting_not_found(client):
    response = await client.get("/api/v1/settings/does.not.exist", headers=ADMIN_HEADERS)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_sensitive_settings_are_masked(client, db_session):
    """discord.bot_token is sensitive — value must come back as '***' for
    a session-authenticated (dashboard) user. Admin-key callers (bot,
    plugin) deliberately get the real value instead - see
    api/routers/settings.py's get_setting() and its comment. Using
    ADMIN_HEADERS here would test the wrong auth path entirely."""
    headers = await session_headers_for_role(db_session, "owner")
    response = await client.get("/api/v1/settings/discord.bot_token", headers=headers)
    assert response.status_code == 200
    assert response.json()["value"] == "***"


@pytest.mark.asyncio
async def test_non_sensitive_settings_not_masked(client):
    response = await client.get("/api/v1/settings/server.name", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    # Value should be the seeded default, not masked
    assert response.json()["value"] != "***"


@pytest.mark.asyncio
async def test_patch_setting_updates_value(client):
    payload = {"value": "MyTestServer"}
    response = await client.patch(
        "/api/v1/settings/server.name", json=payload, headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    assert response.json()["value"] == "MyTestServer"


@pytest.mark.asyncio
async def test_patch_setting_persists(client):
    """After PATCH, GET should return the new value."""
    await client.patch(
        "/api/v1/settings/server.name",
        json={"value": "PersistTest"},
        headers=ADMIN_HEADERS,
    )
    response = await client.get("/api/v1/settings/server.name", headers=ADMIN_HEADERS)
    assert response.json()["value"] == "PersistTest"


@pytest.mark.asyncio
async def test_patch_setting_not_found(client):
    response = await client.patch(
        "/api/v1/settings/fake.key",
        json={"value": "x"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_sensitive_setting_returns_masked(client, tmp_path, monkeypatch):
    """Patching a sensitive key must still return masked value in response.

    discord.bot_token is in services.settings_service.ENV_KEY_MAP, so a
    real PATCH here flows through write_env_value() -> dotenv.set_key(),
    which writes into ENV_PATH for real. Left unmocked, this test wrote a
    genuine .env file into umbrella-core-CURRENT/ on every single pytest
    run (discovered 2026-08-15, after it kept resurfacing across
    otherwise-clean leak-checks) — isolated here the same way
    tests/test_settings_seed_from_env.py already isolates the same risk,
    rather than testing against the project's real .env by accident.
    """
    import services.settings_service as settings_service_module

    env_file = tmp_path / ".env"
    env_file.write_text("")
    monkeypatch.setattr(settings_service_module, "ENV_PATH", env_file)

    response = await client.patch(
        "/api/v1/settings/discord.bot_token",
        json={"value": "real-token-123"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["value"] == "***"
    # Confirm the write really happened (this test's actual point), just
    # into the isolated temp file instead of the project's real .env.
    assert "DISCORD_BOT_TOKEN=real-token-123" in env_file.read_text()
