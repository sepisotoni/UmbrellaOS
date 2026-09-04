"""Tests for server control and staff management endpoints."""
import pytest
from sqlalchemy import select

from models import User
from models.permissions import Role
from models.plugin_heartbeat import PluginHeartbeat
from services.settings_service import SettingsService
from tests.conftest import ADMIN_HEADERS, PLUGIN_HEADERS


async def _owner_headers(db_session):
    from datetime import datetime, timedelta, timezone
    from models import Session

    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == "owner"))
        user = User(discord_id="owner-discord", username="owner_user", role_id=role.id)
        db.add(user)
        await db.flush()
        token = "owner-token"
        db.add(Session(user_id=user.id, token=token, expires_at=datetime.now(timezone.utc) + timedelta(days=1)))
        await db.commit()
    return {"Authorization": "Bearer owner-token"}


async def _helper_headers(db_session):
    from datetime import datetime, timedelta, timezone
    from models import Session

    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == "helper"))
        user = User(discord_id="helper-discord", username="helper_user", role_id=role.id)
        db.add(user)
        await db.flush()
        token = "helper-token"
        db.add(Session(user_id=user.id, token=token, expires_at=datetime.now(timezone.utc) + timedelta(days=1)))
        await db.commit()
    return {"Authorization": "Bearer helper-token"}


@pytest.mark.asyncio
async def test_server_control_maintenance(client, db_session, monkeypatch):
    async with db_session() as db:
        db.add(PluginHeartbeat(server_id="srv1", server_name="Test"))
        await db.commit()

    response = await client.post(
        "/api/v1/server/control",
        json={"server_id": "srv1", "action": "maintenance", "enabled": True},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["maintenance"] is True
    assert data["success"] is True


@pytest.mark.asyncio
async def test_server_control_restart_runs_command(client, db_session, monkeypatch):
    async with db_session() as db:
        db.add(PluginHeartbeat(server_id="srv1", server_name="Test"))
        await SettingsService.update(
            db, "server.control.restart_cmd", "echo restarted", actor="test", actor_type="system",
        )
        await db.commit()

    async def fake_exec(*args, **kwargs):
        class Proc:
            returncode = 0

            async def communicate(self):
                return b"ok", b""

        return Proc()

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)

    response = await client.post(
        "/api/v1/server/control",
        json={"server_id": "srv1", "action": "restart"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_server_control_requires_permission(client, db_session):
    headers = await _helper_headers(db_session)
    response = await client.post(
        "/api/v1/server/control",
        json={"server_id": "srv1", "action": "maintenance"},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_staff_promote(client, db_session):
    owner_headers = await _owner_headers(db_session)
    async with db_session() as db:
        helper_role = await db.scalar(select(Role).where(Role.name == "helper"))
        mod_role = await db.scalar(select(Role).where(Role.name == "moderator"))
        user = User(discord_id="staff-1", username="StaffOne", role_id=helper_role.id)
        db.add(user)
        await db.commit()
        user_id = user.id

    response = await client.post(
        "/api/v1/staff/manage",
        json={"user_id": user_id, "action": "promote"},
        headers=owner_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["previous_role"] == "helper"
    assert data["new_role"] == "moderator"


@pytest.mark.asyncio
async def test_staff_demote(client, db_session):
    owner_headers = await _owner_headers(db_session)
    async with db_session() as db:
        mod_role = await db.scalar(select(Role).where(Role.name == "moderator"))
        user = User(discord_id="staff-2", username="StaffTwo", role_id=mod_role.id)
        db.add(user)
        await db.commit()
        user_id = user.id

    response = await client.post(
        "/api/v1/staff/manage",
        json={"user_id": user_id, "action": "demote"},
        headers=owner_headers,
    )
    assert response.status_code == 200
    assert response.json()["new_role"] == "helper"


@pytest.mark.asyncio
async def test_staff_manage_requires_roles_permission(client, db_session):
    from datetime import datetime, timedelta, timezone
    from models import Session

    async with db_session() as db:
        admin_role = await db.scalar(select(Role).where(Role.name == "admin"))
        user = User(discord_id="admin-1", username="AdminOne", role_id=admin_role.id)
        db.add(user)
        await db.flush()
        token = "admin-token"
        db.add(Session(user_id=user.id, token=token, expires_at=datetime.now(timezone.utc) + timedelta(days=1)))
        helper_role = await db.scalar(select(Role).where(Role.name == "helper"))
        target = User(discord_id="target-1", username="Target", role_id=helper_role.id)
        db.add(target)
        await db.commit()
        target_id = target.id

    response = await client.post(
        "/api/v1/staff/manage",
        json={"user_id": target_id, "action": "promote"},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_staff_demote_blocks_last_owner(client, db_session):
    """
    Demoting the only remaining owner must be refused (409) — otherwise the
    org permanently loses the ability to promote anyone back to owner, since
    only owners can run the promote-to-owner branch of manage_staff_role.
    Bug found + fixed 2026-08-30 in services/staff_service.py.
    """
    from sqlalchemy import select as sa_select
    from models import User as UserModel

    owner_headers = await _owner_headers(db_session)

    # Find the sole owner just created by _owner_headers
    async with db_session() as db:
        owner_role = await db.scalar(select(Role).where(Role.name == "owner"))
        owner_user = await db.scalar(
            sa_select(UserModel).where(UserModel.role_id == owner_role.id)
        )
        owner_user_id = owner_user.id

    response = await client.post(
        "/api/v1/staff/manage",
        json={"user_id": owner_user_id, "action": "demote"},
        headers=owner_headers,
    )
    assert response.status_code == 409
    assert "last remaining owner" in response.json()["detail"].lower()

    # Confirm they're still owner in the DB
    async with db_session() as db:
        refreshed = await db.get(UserModel, owner_user_id)
        role = await db.scalar(select(Role).where(Role.id == refreshed.role_id))
        assert role.name == "owner"


@pytest.mark.asyncio
async def test_staff_demote_second_owner_succeeds(client, db_session):
    """With 2+ owners present, demoting one of them must still work normally."""
    from sqlalchemy import select as sa_select
    from models import User as UserModel

    owner_headers = await _owner_headers(db_session)

    async with db_session() as db:
        owner_role = await db.scalar(select(Role).where(Role.name == "owner"))
        second_owner = UserModel(discord_id="owner-discord-2", username="owner_user_2", role_id=owner_role.id)
        db.add(second_owner)
        await db.commit()
        second_owner_id = second_owner.id

    response = await client.post(
        "/api/v1/staff/manage",
        json={"user_id": second_owner_id, "action": "demote"},
        headers=owner_headers,
    )
    assert response.status_code == 200
    assert response.json()["new_role"] == "admin"


# ---------------------------------------------------------------------------
# GET /api/v1/staff/{identifier} — plugin-key staff lookup (HEAD's plugin-
# extensibility notice: plugin needs to check a player's staff status/role
# by Discord ID or Minecraft UUID to grant matching in-game permissions).
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_staff_lookup_by_discord_id_finds_staff(client, db_session):
    from datetime import datetime, timezone
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == "helper"))
        user = User(discord_id="lookup-discord-1", username="LookupHelper", role_id=role.id)
        db.add(user)
        await db.commit()

    response = await client.get(
        "/api/v1/staff/lookup-discord-1",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_staff"] is True
    assert data["discord_id"] == "lookup-discord-1"
    assert data["role"] == "helper"


@pytest.mark.asyncio
async def test_staff_lookup_by_discord_id_not_staff(client, db_session):
    response = await client.get(
        "/api/v1/staff/never-registered-discord-id",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_staff"] is False


@pytest.mark.asyncio
async def test_staff_lookup_by_minecraft_uuid_finds_staff(client, db_session):
    from models import Player
    from models.discord import DiscordAccount

    test_uuid = "aaaaaaaa-1111-2222-3333-444444444444"
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == "moderator"))
        user = User(discord_id="lookup-discord-2", username="LookupMod", role_id=role.id)
        db.add(user)
        db.add(Player(uuid=test_uuid, username="ModPlayer"))
        db.add(DiscordAccount(
            discord_id="lookup-discord-2",
            player_uuid=test_uuid,
            verified=True,
        ))
        await db.commit()

    response = await client.get(
        f"/api/v1/staff/{test_uuid}",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_staff"] is True
    assert data["discord_id"] == "lookup-discord-2"
    assert data["role"] == "moderator"


@pytest.mark.asyncio
async def test_staff_lookup_by_unverified_uuid_not_staff(client, db_session):
    """An unverified DiscordAccount link should not resolve to staff status,
    even if the underlying discord_id belongs to a real staff member —
    unverified means the plugin can't trust the UUID<->Discord link yet."""
    from models import Player
    from models.discord import DiscordAccount

    test_uuid = "bbbbbbbb-1111-2222-3333-444444444444"
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == "helper"))
        user = User(discord_id="lookup-discord-3", username="LookupUnverified", role_id=role.id)
        db.add(user)
        db.add(Player(uuid=test_uuid, username="UnverifiedPlayer"))
        db.add(DiscordAccount(
            discord_id="lookup-discord-3",
            player_uuid=test_uuid,
            verified=False,
        ))
        await db.commit()

    response = await client.get(
        f"/api/v1/staff/{test_uuid}",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["is_staff"] is False


@pytest.mark.asyncio
async def test_staff_lookup_player_role_excluded(client, db_session):
    """A User with the 'player' role (not a real staff role) should report
    is_staff=False, matching list_staff()'s existing exclusion."""
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == "player"))
        if role is not None:
            user = User(discord_id="lookup-discord-player", username="JustAPlayer", role_id=role.id)
            db.add(user)
            await db.commit()
        else:
            pytest.skip("no 'player' role seeded in this environment")

    response = await client.get(
        "/api/v1/staff/lookup-discord-player",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["is_staff"] is False


@pytest.mark.asyncio
async def test_staff_lookup_requires_plugin_key(client, db_session):
    response = await client.get("/api/v1/staff/some-discord-id")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_staff_includes_is_active(client, db_session):
    """
    AUDIT-2026-08-30 regression test: StaffMemberSchema previously had no
    is_active field at all — GET /api/v1/staff/list_staff's response
    never included it, so the dashboard's status badge (member.is_active)
    was always undefined -> always falsy -> every staff member showed
    DISABLED regardless of their real status. Zero test coverage existed
    for this endpoint's response shape before this test.
    """
    headers = await _owner_headers(db_session)

    response = await client.get("/api/v1/staff", headers=headers)
    assert response.status_code == 200
    members = response.json()
    assert len(members) >= 1

    owner_member = next(m for m in members if m["discord_id"] == "owner-discord")
    assert "is_active" in owner_member
    assert owner_member["is_active"] is True
