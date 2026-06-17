"""
tests/test_moderation.py — Tests for moderation endpoints.

POST /api/v1/moderation/kick       — Kick a player
POST /api/v1/moderation/warn       — Warn a player
POST /api/v1/moderation/ban        — Ban a player
POST /api/v1/moderation/ipban      — IP ban
GET  /api/v1/moderation/active     — Get active punishments
"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from models import Player, Punishment, Session, User
from models.permissions import Role
from tests.conftest import ADMIN_HEADERS

TEST_PLAYER_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


async def _session_headers_for_role(db_session, role_name: str) -> dict:
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == role_name))
        user = User(
            discord_id=f"discord-{role_name}",
            username=f"user_{role_name}",
            role_id=role.id,
        )
        db.add(user)
        await db.flush()
        token = f"token-{role_name}"
        session = Session(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(session)
        await db.commit()
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_player(db_session):
    async with db_session() as db:
        db.add(Player(uuid=TEST_PLAYER_UUID, username="TestPlayer"))
        await db.commit()


@pytest.mark.asyncio
async def test_kick_requires_moderation_kick_permission(client, db_session, test_player):
    headers = await _session_headers_for_role(db_session, "moderator")
    response = await client.post(
        "/api/v1/moderation/kick",
        json={"player_uuid": TEST_PLAYER_UUID, "reason": "Test kick"},
        headers=headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_warn_requires_moderation_warn_permission(client, db_session, test_player):
    headers = await _session_headers_for_role(db_session, "moderator")
    response = await client.post(
        "/api/v1/moderation/warn",
        json={"player_uuid": TEST_PLAYER_UUID, "reason": "Test warn"},
        headers=headers,
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_ban_requires_moderation_ban_permission(client, db_session, test_player):
    headers = await _session_headers_for_role(db_session, "owner")
    response = await client.post(
        "/api/v1/moderation/ban",
        json={"player_uuid": TEST_PLAYER_UUID, "reason": "Test ban"},
        headers=headers,
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_ipban_requires_moderation_ipban_permission(client, db_session):
    headers = await _session_headers_for_role(db_session, "owner")
    response = await client.post(
        "/api/v1/moderation/ipban",
        json={"ip_address": "192.168.1.1", "reason": "Test IP ban"},
        headers=headers,
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_helper_cannot_kick(client, db_session, test_player):
    headers = await _session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/moderation/kick",
        json={"player_uuid": TEST_PLAYER_UUID, "reason": "Helper trying to kick"},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_x_admin_key_bypasses_all_permission_checks(client, db_session, test_player):
    """X-Admin-Key should bypass all permission checks."""
    response = await client.post(
        "/api/v1/moderation/kick",
        json={"player_uuid": TEST_PLAYER_UUID, "reason": "Admin key kick"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_active_punishments_requires_punishments_view(client, db_session, test_player):
    """Create a punishment first, then test getting active punishments."""
    # Create a punishment via admin key
    await client.post(
        "/api/v1/punishments",
        json={
            "player_uuid": TEST_PLAYER_UUID,
            "type": "ban",
            "reason": "Test ban",
        },
        headers=ADMIN_HEADERS,
    )
    
    headers = await _session_headers_for_role(db_session, "helper")
    response = await client.get(f"/api/v1/moderation/active/{TEST_PLAYER_UUID}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
