"""
tests/test_punishments.py — Tests for punishment endpoints.

GET  /api/v1/punishments           — list all punishments
POST /api/v1/punishments           — create a new punishment
POST /api/v1/punishments/{id}/revoke — revoke a punishment
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


@pytest_asyncio.fixture
async def test_punishment(client, db_session, test_player):
    """Create a test punishment via admin key for use in other tests."""
    response = await client.post(
        "/api/v1/punishments",
        json={
            "player_uuid": TEST_PLAYER_UUID,
            "type": "ban",
            "reason": "Test punishment",
        },
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_list_punishments_returns_200(client, db_session, test_punishment):
    headers = await _session_headers_for_role(db_session, "owner")
    response = await client.get("/api/v1/punishments", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_create_punishment_returns_201(client, db_session, test_player):
    headers = await _session_headers_for_role(db_session, "owner")
    response = await client.post(
        "/api/v1/punishments",
        json={
            "player_uuid": TEST_PLAYER_UUID,
            "type": "mute",
            "reason": "Test mute",
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "mute"
    assert data["reason"] == "Test mute"
    assert data["player_uuid"] == TEST_PLAYER_UUID


@pytest.mark.asyncio
async def test_revoke_punishment_returns_200(client, db_session, test_punishment):
    headers = await _session_headers_for_role(db_session, "owner")
    punishment_id = test_punishment["id"]
    response = await client.post(
        f"/api/v1/punishments/{punishment_id}/revoke",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is False


@pytest.mark.asyncio
async def test_helper_cannot_create_punishment(client, db_session, test_player):
    headers = await _session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/punishments",
        json={
            "player_uuid": TEST_PLAYER_UUID,
            "type": "ban",
            "reason": "Helper trying to ban",
        },
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_invalid_player_uuid_returns_404(client, db_session):
    headers = await _session_headers_for_role(db_session, "owner")
    fake_uuid = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
    response = await client.post(
        "/api/v1/punishments",
        json={
            "player_uuid": fake_uuid,
            "type": "ban",
            "reason": "Test",
        },
        headers=headers,
    )
    assert response.status_code == 404
