"""
tests/registry/test_capabilities_discord_delegation.py — Tests for Phase 6's
slash-command -> REST-permission mapping: CallContext.from_discord_user and
the X-Discord-User-Id header handling in registry/adapters/rest.py.

Exercised entirely through the real FastAPI app, the real Capability
Registry, and platform.system.whoami (which just echoes back whatever
CallContext the request resolved to) — same approach
test_capabilities_identity.py already uses for the plain API-key path.
"""
import pytest

from models.permissions import Role
from models.user import User
from tests.conftest import ADMIN_HEADERS


async def _create_delegate_key(client, *, extra_permissions=None) -> str:
    """A key with identity.discord_delegate, i.e. one an operator has
    explicitly opted in to delegation - see rest.py's own reasoning for
    why this must be an explicit grant, never assumed."""
    permissions = ["identity.discord_delegate"] + (extra_permissions or [])
    response = await client.post(
        "/api/v1/capabilities/identity.apikey.create/invoke",
        json={"name": "delegating-bot-key", "permissions": permissions},
        headers=ADMIN_HEADERS,
    )
    return response.json()["plaintext_key"]


async def _create_non_delegate_key(client, *, permissions=None) -> str:
    response = await client.post(
        "/api/v1/capabilities/identity.apikey.create/invoke",
        json={"name": "plain-bot-key", "permissions": permissions or []},
        headers=ADMIN_HEADERS,
    )
    return response.json()["plaintext_key"]


@pytest.mark.asyncio
async def test_delegated_call_for_unlinked_discord_user_gets_only_base_permissions(client):
    plaintext = await _create_delegate_key(client, extra_permissions=["hosting.server.view"])

    response = await client.post(
        "/api/v1/capabilities/platform.system.whoami/invoke",
        json={},
        headers={"X-Api-Key": plaintext, "X-Discord-User-Id": "999999"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["actor_id"] == "999999"
    assert body["actor_type"] == "discord_user"
    assert body["is_superuser"] is False
    assert set(body["permissions"]) == {"identity.discord_delegate", "hosting.server.view"}


async def _get_seeded_permission(db, permission_key: str):
    from sqlalchemy import select
    from models.permissions import Permission

    result = await db.execute(select(Permission).where(Permission.permission_key == permission_key))
    return result.scalar_one()


async def _grant_role_permission(db, role, permission) -> None:
    """Inserts into the role_permissions join table directly rather than
    appending to role.permissions - that ORM relationship is lazy-loaded,
    and touching it here triggers SQLAlchemy's async greenlet error (no
    existing test in this codebase creates a role + attaches permissions
    within a single test, so there was no precedent to follow - this is
    the fix, not a workaround)."""
    from models.permissions import role_permissions

    await db.execute(role_permissions.insert().values(role_id=role.id, permission_id=permission.id))


@pytest.mark.asyncio
async def test_delegated_call_for_linked_staff_user_gets_unioned_permissions(client, db_session):
    async with db_session() as db:
        role = Role(name="delegation-test-moderator")
        db.add(role)
        await db.flush()
        perm = await _get_seeded_permission(db, "moderation_intelligence.escalation.manage")
        await _grant_role_permission(db, role, perm)
        db.add(User(discord_id="12345", username="LinkedStaffer", role_id=role.id))
        await db.commit()

    plaintext = await _create_delegate_key(client, extra_permissions=["hosting.server.view"])

    response = await client.post(
        "/api/v1/capabilities/platform.system.whoami/invoke",
        json={},
        headers={"X-Api-Key": plaintext, "X-Discord-User-Id": "12345"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["actor_id"] == "12345"
    assert body["actor_type"] == "staff"
    # union of the key's own base scope AND the linked user's role - not a
    # replacement of one by the other.
    assert "hosting.server.view" in body["permissions"]
    assert "moderation_intelligence.escalation.manage" in body["permissions"]


@pytest.mark.asyncio
async def test_delegated_call_for_deactivated_linked_user_falls_back_to_base_only(client, db_session):
    async with db_session() as db:
        role = Role(name="delegation-test-deactivated-role")
        db.add(role)
        await db.flush()
        perm = await _get_seeded_permission(db, "hosting.server.manage")
        await _grant_role_permission(db, role, perm)
        db.add(User(discord_id="55555", username="DeactivatedStaffer", role_id=role.id, is_active=False))
        await db.commit()

    plaintext = await _create_delegate_key(client, extra_permissions=["hosting.server.view"])

    response = await client.post(
        "/api/v1/capabilities/platform.system.whoami/invoke",
        json={},
        headers={"X-Api-Key": plaintext, "X-Discord-User-Id": "55555"},
    )
    body = response.json()
    assert body["actor_type"] == "discord_user"
    assert "hosting.server.manage" not in body["permissions"]
    assert set(body["permissions"]) == {"identity.discord_delegate", "hosting.server.view"}


@pytest.mark.asyncio
async def test_header_ignored_without_delegate_permission_falls_back_to_key_scope(client):
    """A key without identity.discord_delegate sending the header anyway
    must behave exactly as it did pre-Phase-6 - its own blanket scope,
    not a downgrade to discord_user-only permissions and not an error."""
    plaintext = await _create_non_delegate_key(client, permissions=["hosting.server.view"])

    response = await client.post(
        "/api/v1/capabilities/platform.system.whoami/invoke",
        json={},
        headers={"X-Api-Key": plaintext, "X-Discord-User-Id": "12345"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["actor_type"] == "plugin"
    assert set(body["permissions"]) == {"hosting.server.view"}


@pytest.mark.asyncio
async def test_source_is_discord_when_header_present_even_without_delegate_permission(client):
    plaintext = await _create_non_delegate_key(client)

    response = await client.post(
        "/api/v1/capabilities/platform.system.whoami/invoke",
        json={},
        headers={"X-Api-Key": plaintext, "X-Discord-User-Id": "anything"},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "discord"


@pytest.mark.asyncio
async def test_source_is_rest_when_header_absent(client):
    plaintext = await _create_non_delegate_key(client)

    response = await client.post(
        "/api/v1/capabilities/platform.system.whoami/invoke", json={}, headers={"X-Api-Key": plaintext}
    )
    assert response.status_code == 200
    assert response.json()["source"] == "rest"


@pytest.mark.asyncio
async def test_delegated_call_is_denied_for_capability_neither_scope_grants(client, db_session):
    async with db_session() as db:
        role = Role(name="delegation-test-no-relevant-perms")
        db.add(role)
        await db.flush()
        db.add(User(discord_id="77777", username="LowPrivStaffer", role_id=role.id))
        await db.commit()

    plaintext = await _create_delegate_key(client)  # no extra base permissions

    response = await client.post(
        "/api/v1/capabilities/hosting.server.restart/invoke",
        json={"server_id": "srv-1"},
        headers={"X-Api-Key": plaintext, "X-Discord-User-Id": "77777"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_plain_session_auth_is_unaffected_by_discord_header(client, db_session):
    """The header is only ever consulted for ApiKey auth - a staff
    session presenting it (which shouldn't happen in practice, but the
    isinstance(auth, ApiKey) gate should make it a no-op regardless) must
    not change session-auth behavior at all."""
    from tests.registry.conftest import session_headers_for_role

    headers = await session_headers_for_role(db_session, "moderator")
    headers = {**headers, "X-Discord-User-Id": "should-be-ignored"}
    response = await client.post(
        "/api/v1/capabilities/platform.system.whoami/invoke", json={}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["actor_type"] == "staff"
