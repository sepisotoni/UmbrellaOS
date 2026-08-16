"""
tests/registry/test_capabilities_verification.py — REST integration tests
for verification.confirm / verification.status.

Deliberately does NOT re-test the pre-existing router endpoints
(/api/v1/verification/confirm etc) — those are covered by
tests/test_verification.py and are untouched by this change. This file
covers only the new capability path, including that it reuses the exact
same business rules (unexpired/unused code, conflicting-link rejection,
idempotent re-confirm) against the same tables, and that the new
verification.link.* permissions are gated as intended (helper: view only,
moderator: both, admin/owner: both via ALL_PERMISSION_KEYS).
"""
import itertools
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from models import VerificationCode
from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role

_code_counter = itertools.count(100000)


async def _create_code(db_session, *, player_uuid="aaaa-bbbb-cccc-dddd", player_username="TestPlayer", used=False, expired=False) -> str:
    async with db_session() as db:
        code = VerificationCode(
            player_uuid=player_uuid,
            player_username=player_username,
            code=f"{next(_code_counter)}",
            expires_at=datetime.now(timezone.utc) + (timedelta(minutes=-1) if expired else timedelta(minutes=10)),
            used=used,
        )
        db.add(code)
        await db.commit()
        return code.code


@pytest.mark.asyncio
async def test_verification_capabilities_are_listed(client):
    response = await client.get("/api/v1/capabilities")
    names = {c["name"] for c in response.json()}
    assert "verification.confirm" in names
    assert "verification.status" in names
    assert "verification.link.by_discord" in names


@pytest.mark.asyncio
async def test_confirm_with_valid_code_succeeds(client, db_session):
    code = await _create_code(db_session, player_uuid="uuid-1", player_username="Alice")
    response = await client.post(
        "/api/v1/capabilities/verification.confirm/invoke",
        json={"discord_id": "111", "discord_username": "alice#0001", "code": code},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["player_uuid"] == "uuid-1"
    assert data["player_username"] == "Alice"
    assert data["already_linked"] is False


@pytest.mark.asyncio
async def test_confirm_reconfirming_same_pair_is_idempotent(client, db_session):
    code1 = await _create_code(db_session, player_uuid="uuid-2", player_username="Bob")
    await client.post(
        "/api/v1/capabilities/verification.confirm/invoke",
        json={"discord_id": "222", "discord_username": "bob", "code": code1},
        headers=ADMIN_HEADERS,
    )
    code2 = await _create_code(db_session, player_uuid="uuid-2", player_username="Bob")
    response = await client.post(
        "/api/v1/capabilities/verification.confirm/invoke",
        json={"discord_id": "222", "discord_username": "bob", "code": code2},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["already_linked"] is True


@pytest.mark.asyncio
async def test_confirm_with_expired_code_returns_422(client, db_session):
    code = await _create_code(db_session, player_uuid="uuid-3", expired=True)
    response = await client.post(
        "/api/v1/capabilities/verification.confirm/invoke",
        json={"discord_id": "333", "discord_username": "c", "code": code},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_confirm_with_used_code_returns_422(client, db_session):
    code = await _create_code(db_session, player_uuid="uuid-4", used=True)
    response = await client.post(
        "/api/v1/capabilities/verification.confirm/invoke",
        json={"discord_id": "444", "discord_username": "d", "code": code},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_confirm_with_unknown_code_returns_404(client):
    response = await client.post(
        "/api/v1/capabilities/verification.confirm/invoke",
        json={"discord_id": "555", "discord_username": "e", "code": "000000"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_confirm_conflicting_discord_account_returns_409(client, db_session):
    first_code = await _create_code(db_session, player_uuid="uuid-5", player_username="Ed")
    await client.post(
        "/api/v1/capabilities/verification.confirm/invoke",
        json={"discord_id": "666", "discord_username": "ed", "code": first_code},
        headers=ADMIN_HEADERS,
    )
    second_code = await _create_code(db_session, player_uuid="uuid-6", player_username="Other")
    response = await client.post(
        "/api/v1/capabilities/verification.confirm/invoke",
        json={"discord_id": "666", "discord_username": "ed", "code": second_code},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_status_reflects_confirmed_link(client, db_session):
    code = await _create_code(db_session, player_uuid="uuid-7", player_username="Fae")
    await client.post(
        "/api/v1/capabilities/verification.confirm/invoke",
        json={"discord_id": "777", "discord_username": "fae", "code": code},
        headers=ADMIN_HEADERS,
    )
    response = await client.post(
        "/api/v1/capabilities/verification.status/invoke",
        json={"player_uuid": "uuid-7"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is True
    assert data["discord_id"] == "777"


@pytest.mark.asyncio
async def test_status_for_unverified_player(client):
    response = await client.post(
        "/api/v1/capabilities/verification.status/invoke",
        json={"player_uuid": "never-verified"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["verified"] is False


@pytest.mark.asyncio
async def test_confirm_denied_for_helper(client, db_session):
    """helper has verification.link.view but not .manage."""
    code = await _create_code(db_session, player_uuid="uuid-8")
    headers = await session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/capabilities/verification.confirm/invoke",
        json={"discord_id": "888", "discord_username": "h", "code": code},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_status_allowed_for_helper(client, db_session):
    headers = await session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/capabilities/verification.status/invoke",
        json={"player_uuid": "whatever"},
        headers=headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_confirm_allowed_for_moderator(client, db_session):
    code = await _create_code(db_session, player_uuid="uuid-9", player_username="Gia")
    headers = await session_headers_for_role(db_session, "moderator")
    response = await client.post(
        "/api/v1/capabilities/verification.confirm/invoke",
        json={"discord_id": "999", "discord_username": "g", "code": code},
        headers=headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_link_by_discord_returns_uuid_and_username_with_player_row(client, db_session):
    from models import Player

    code = await _create_code(db_session, player_uuid="uuid-10", player_username="Hana")
    await client.post(
        "/api/v1/capabilities/verification.confirm/invoke",
        json={"discord_id": "1010", "discord_username": "hana", "code": code},
        headers=ADMIN_HEADERS,
    )
    async with db_session() as db:
        db.add(Player(uuid="uuid-10", username="Hana"))
        await db.commit()

    response = await client.post(
        "/api/v1/capabilities/verification.link.by_discord/invoke",
        json={"discord_id": "1010"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["linked"] is True
    assert data["player_uuid"] == "uuid-10"
    assert data["player_username"] == "Hana"


@pytest.mark.asyncio
async def test_link_by_discord_returns_linked_without_player_row(client, db_session):
    """Confirms the outer join doesn't drop the link just because no
    Player row exists yet (e.g. a manually-linked account before the
    player's first join)."""
    code = await _create_code(db_session, player_uuid="uuid-11", player_username="Ira")
    await client.post(
        "/api/v1/capabilities/verification.confirm/invoke",
        json={"discord_id": "1111", "discord_username": "ira", "code": code},
        headers=ADMIN_HEADERS,
    )

    response = await client.post(
        "/api/v1/capabilities/verification.link.by_discord/invoke",
        json={"discord_id": "1111"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["linked"] is True
    assert data["player_uuid"] == "uuid-11"
    assert data["player_username"] is None


@pytest.mark.asyncio
async def test_link_by_discord_returns_not_linked_for_unknown_user(client):
    response = await client.post(
        "/api/v1/capabilities/verification.link.by_discord/invoke",
        json={"discord_id": "never-linked"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["linked"] is False
    assert data["player_uuid"] is None
    assert data["player_username"] is None


@pytest.mark.asyncio
async def test_link_by_discord_allowed_for_helper(client, db_session):
    headers = await session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/capabilities/verification.link.by_discord/invoke",
        json={"discord_id": "whoever"},
        headers=headers,
    )
    assert response.status_code == 200
