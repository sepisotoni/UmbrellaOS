"""
tests/test_permissions.py — Role-based permission enforcement tests.
"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from models import Player, Session, User
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
async def test_owner_role_can_ban(client, db_session, test_player):
    headers = await _session_headers_for_role(db_session, "owner")
    response = await client.post(
        "/api/v1/moderation/ban",
        json={"player_uuid": TEST_PLAYER_UUID, "reason": "test ban"},
        headers=headers,
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_moderator_role_can_kick(client, db_session, test_player):
    headers = await _session_headers_for_role(db_session, "moderator")
    response = await client.post(
        "/api/v1/moderation/kick",
        json={"player_uuid": TEST_PLAYER_UUID, "reason": "test kick"},
        headers=headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_moderator_role_cannot_change_settings(client, db_session):
    headers = await _session_headers_for_role(db_session, "moderator")
    response = await client.patch(
        "/api/v1/settings/server.name",
        json={"value": "hacked"},
        headers=headers,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_helper_role_cannot_ban(client, db_session, test_player):
    headers = await _session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/moderation/ban",
        json={"player_uuid": TEST_PLAYER_UUID, "reason": "test ban"},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_key_bypasses_permission_checks(client, db_session, test_player):
    response = await client.post(
        "/api/v1/moderation/ban",
        json={"player_uuid": TEST_PLAYER_UUID, "reason": "admin key ban"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(client, test_player):
    response = await client.post(
        "/api/v1/moderation/ban",
        json={"player_uuid": TEST_PLAYER_UUID, "reason": "no auth"},
    )
    assert response.status_code == 401
