"""
tests/test_players.py — Tests for player endpoints.

GET  /api/v1/players           — list all players
GET  /api/v1/players/{uuid}    — get a single player by UUID
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
async def test_list_players_returns_200_with_bearer_token(client, db_session, test_player):
    headers = await _session_headers_for_role(db_session, "owner")
    response = await client.get("/api/v1/players", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_player_by_uuid_returns_200(client, db_session, test_player):
    headers = await _session_headers_for_role(db_session, "owner")
    response = await client.get(f"/api/v1/players/{TEST_PLAYER_UUID}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["uuid"] == TEST_PLAYER_UUID
    assert data["username"] == "TestPlayer"


@pytest.mark.asyncio
async def test_get_nonexistent_player_returns_404(client, db_session):
    headers = await _session_headers_for_role(db_session, "owner")
    fake_uuid = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
    response = await client.get(f"/api/v1/players/{fake_uuid}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_players_without_auth_returns_401(client, test_player):
    response = await client.get("/api/v1/players")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_helper_role_can_view_players(client, db_session, test_player):
    headers = await _session_headers_for_role(db_session, "helper")
    response = await client.get("/api/v1/players", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_member_role_cannot_view_players(client, db_session, test_player):
    headers = await _session_headers_for_role(db_session, "member")
    response = await client.get("/api/v1/players", headers=headers)
    assert response.status_code == 403
