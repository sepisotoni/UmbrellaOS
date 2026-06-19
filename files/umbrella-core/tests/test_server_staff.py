"""Tests for server control and staff management endpoints."""
import pytest
from sqlalchemy import select

from models import User
from models.permissions import Role
from models.plugin_heartbeat import PluginHeartbeat
from services.settings_service import SettingsService
from tests.conftest import ADMIN_HEADERS


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
