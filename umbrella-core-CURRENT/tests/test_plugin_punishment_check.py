"""
tests/test_plugin_punishment_check.py — Plugin-key ban-check endpoint.

GET /api/v1/plugin/punishments/{player_uuid}/active

Phase 13 Step 2. New endpoint — see api/routers/plugin.py for why it
exists (the plugin has no RBAC identity to present against the real
punishments.view-gated endpoint).
"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from models import Player, Punishment
from tests.conftest import PLUGIN_HEADERS

TEST_PLAYER_UUID = "11111111-2222-3333-4444-555555555555"
OTHER_PLAYER_UUID = "99999999-8888-7777-6666-555555555555"


@pytest_asyncio.fixture
async def test_player(db_session):
    async with db_session() as db:
        db.add(Player(uuid=TEST_PLAYER_UUID, username="TestPlayer"))
        db.add(Player(uuid=OTHER_PLAYER_UUID, username="OtherPlayer"))
        await db.commit()


@pytest.mark.asyncio
async def test_active_ban_check_unauthenticated_returns_401(client):
    response = await client.get(f"/api/v1/plugin/punishments/{TEST_PLAYER_UUID}/active")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_active_ban_check_no_punishments_returns_not_banned(client, test_player):
    response = await client.get(
        f"/api/v1/plugin/punishments/{TEST_PLAYER_UUID}/active",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["banned"] is False
    assert data["punishment"] is None


@pytest.mark.asyncio
async def test_active_ban_check_permanent_ban_returns_banned(client, db_session, test_player):
    async with db_session() as db:
        db.add(
            Punishment(
                player_uuid=TEST_PLAYER_UUID,
                type="ban",
                reason="Griefing",
                active=True,
            )
        )
        await db.commit()

    response = await client.get(
        f"/api/v1/plugin/punishments/{TEST_PLAYER_UUID}/active",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["banned"] is True
    assert data["punishment"]["type"] == "ban"
    assert data["punishment"]["reason"] == "Griefing"
    assert data["punishment"]["expires_at"] is None


@pytest.mark.asyncio
async def test_active_ban_check_active_tempban_returns_banned(client, db_session, test_player):
    async with db_session() as db:
        db.add(
            Punishment(
                player_uuid=TEST_PLAYER_UUID,
                type="tempban",
                reason="Spamming",
                active=True,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        await db.commit()

    response = await client.get(
        f"/api/v1/plugin/punishments/{TEST_PLAYER_UUID}/active",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["banned"] is True
    assert data["punishment"]["type"] == "tempban"


@pytest.mark.asyncio
async def test_active_ban_check_expired_tempban_returns_not_banned(client, db_session, test_player):
    async with db_session() as db:
        db.add(
            Punishment(
                player_uuid=TEST_PLAYER_UUID,
                type="tempban",
                reason="Spamming",
                active=True,
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
        )
        await db.commit()

    response = await client.get(
        f"/api/v1/plugin/punishments/{TEST_PLAYER_UUID}/active",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["banned"] is False


@pytest.mark.asyncio
async def test_active_ban_check_revoked_ban_returns_not_banned(client, db_session, test_player):
    async with db_session() as db:
        db.add(
            Punishment(
                player_uuid=TEST_PLAYER_UUID,
                type="ban",
                reason="Griefing, later revoked",
                active=False,
            )
        )
        await db.commit()

    response = await client.get(
        f"/api/v1/plugin/punishments/{TEST_PLAYER_UUID}/active",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["banned"] is False


@pytest.mark.asyncio
async def test_active_ban_check_mute_does_not_count_as_ban(client, db_session, test_player):
    """A mute or warn should never block a join — only ban/tempban do."""
    async with db_session() as db:
        db.add(
            Punishment(
                player_uuid=TEST_PLAYER_UUID,
                type="mute",
                reason="Chat spam",
                active=True,
            )
        )
        await db.commit()

    response = await client.get(
        f"/api/v1/plugin/punishments/{TEST_PLAYER_UUID}/active",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["banned"] is False


@pytest.mark.asyncio
async def test_active_ban_check_only_matches_requested_player(client, db_session, test_player):
    async with db_session() as db:
        db.add(
            Punishment(
                player_uuid=OTHER_PLAYER_UUID,
                type="ban",
                reason="Not this player",
                active=True,
            )
        )
        await db.commit()

    response = await client.get(
        f"/api/v1/plugin/punishments/{TEST_PLAYER_UUID}/active",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["banned"] is False


@pytest.mark.asyncio
async def test_active_ban_check_permanent_ban_takes_priority_over_tempban(
    client, db_session, test_player
):
    """
    If a player somehow has both an active tempban and an active permanent
    ban, the permanent one is the one that actually matters (it's the one
    that determines whether they can ever rejoin) — assert it's the one
    returned, not whichever was created most recently.
    """
    async with db_session() as db:
        db.add(
            Punishment(
                player_uuid=TEST_PLAYER_UUID,
                type="tempban",
                reason="Older tempban",
                active=True,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        await db.commit()
        db.add(
            Punishment(
                player_uuid=TEST_PLAYER_UUID,
                type="ban",
                reason="Newer permanent ban",
                active=True,
            )
        )
        await db.commit()

    response = await client.get(
        f"/api/v1/plugin/punishments/{TEST_PLAYER_UUID}/active",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["banned"] is True
    assert data["punishment"]["expires_at"] is None

