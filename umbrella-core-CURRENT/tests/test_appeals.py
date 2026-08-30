"""
tests/test_appeals.py — Tests for appeal endpoints.

GET  /api/v1/appeals           — list all appeals
POST /api/v1/appeals           — create a new appeal (public endpoint)
PATCH /api/v1/appeals/{id}     — update an appeal status
"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from models import Appeal, Player, Punishment, Session, User
from models.permissions import Role
from tests.conftest import ADMIN_HEADERS, PLUGIN_HEADERS

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
    """Create a test punishment via admin key for use in appeal tests."""
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


@pytest_asyncio.fixture
async def test_appeal(client, db_session, test_player, test_punishment):
    """Create a test appeal via admin key for use in other tests."""
    response = await client.post(
        "/api/v1/appeals",
        json={
            "punishment_id": test_punishment["id"],
            "player_uuid": TEST_PLAYER_UUID,
            "message": "This is a test appeal",
        },
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_list_appeals_requires_auth(client, db_session, test_appeal):
    response = await client.get("/api/v1/appeals")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_appeals_with_valid_auth(client, db_session, test_appeal):
    headers = await _session_headers_for_role(db_session, "owner")
    response = await client.get("/api/v1/appeals", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_post_appeals_requires_plugin_key(client, db_session, test_player, test_punishment):
    """POST /api/v1/appeals requires X-Plugin-Key (AUDIT-2026-08-29 fix — see
    api/routers/appeals.py create_appeal docstring). The endpoint accepts
    player_uuid directly from the request body with no ownership check, so a
    truly unauthenticated version would let anyone forge an appeal for any
    player against any punishment. This test previously asserted the OLD,
    insecure 'no auth required' contract that predates that fix; updated to
    match the corrected behaviour."""
    # No auth at all -> rejected
    unauth_response = await client.post(
        "/api/v1/appeals",
        json={
            "punishment_id": test_punishment["id"],
            "player_uuid": TEST_PLAYER_UUID,
            "message": "Public appeal test",
        },
    )
    assert unauth_response.status_code == 401

    # With X-Plugin-Key -> succeeds. Appeal status is "open" on creation
    # (Bug #9 fix in create_appeal: ck_appeals_status only allows
    # open/accepted/denied/... — "pending" always violated the constraint).
    response = await client.post(
        "/api/v1/appeals",
        json={
            "punishment_id": test_punishment["id"],
            "player_uuid": TEST_PLAYER_UUID,
            "message": "Public appeal test",
        },
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Public appeal test"
    assert data["status"] == "open"


@pytest.mark.asyncio
async def test_manage_appeal_patch_requires_appeals_manage(client, db_session, test_appeal):
    """"approved" is not a valid appeal status — ck_appeals_status (migrations
    039, 042) and VALID_APPEAL_STATUSES both only permit "accepted". Test was
    asserting a value the DB constraint has never allowed; fixed to use the
    actual valid value so this exercises the appeals.manage permission gate
    it is named for, rather than always failing on the 400 validation check
    before permission behaviour is even reached."""
    headers = await _session_headers_for_role(db_session, "owner")
    appeal_id = test_appeal["id"]
    response = await client.patch(
        f"/api/v1/appeals/{appeal_id}",
        json={"status": "accepted"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"


@pytest.mark.asyncio
async def test_helper_can_view_appeals(client, db_session, test_appeal):
    headers = await _session_headers_for_role(db_session, "helper")
    response = await client.get("/api/v1/appeals", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_helper_cannot_manage_appeals(client, db_session, test_appeal):
    headers = await _session_headers_for_role(db_session, "helper")
    appeal_id = test_appeal["id"]
    response = await client.patch(
        f"/api/v1/appeals/{appeal_id}",
        json={"status": "approved"},
        headers=headers,
    )
    assert response.status_code == 403
