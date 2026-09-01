"""
tests/test_mc_commands.py — MC command execution API tests.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from models import MCCommand, AuditLog
from datetime import datetime, timezone
from tests.conftest import PLUGIN_HEADERS


@pytest.mark.asyncio
async def test_post_mc_command_creates_pending_command(client: AsyncClient, db_session):
    """POST /mc/command creates pending command."""
    response = await client.post(
        "/api/v1/mc/command",
        json={
            "command": "say hello world",
            "requested_by_discord_id": "123456789",
            "requested_by_username": "TestStaff",
        },
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["command"] == "say hello world"
    assert data["status"] == "pending"
    assert data["requested_by_username"] == "TestStaff"
    assert data["requested_by_discord_id"] == "123456789"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_post_mc_command_empty_command_returns_400(client: AsyncClient):
    """POST /mc/command with empty command returns 400."""
    response = await client.post(
        "/api/v1/mc/command",
        json={
            "command": "   ",
            "requested_by_discord_id": "123456789",
            "requested_by_username": "TestStaff",
        },
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_post_mc_command_unauthenticated_returns_401(client: AsyncClient):
    """POST /mc/command without auth returns 401."""
    response = await client.post(
        "/api/v1/mc/command",
        json={
            "command": "say hello",
            "requested_by_discord_id": "123456789",
            "requested_by_username": "TestStaff",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_mc_commands_pending_returns_list(client: AsyncClient, db_session):
    """GET /mc/commands/pending returns list of pending commands."""
    # Create some pending commands
    async with db_session() as db:
        cmd1 = MCCommand(
            command="say hello",
            requested_by_discord_id="123456789",
            requested_by_username="TestStaff1",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        cmd2 = MCCommand(
            command="gamemode creative",
            requested_by_discord_id="987654321",
            requested_by_username="TestStaff2",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        cmd3 = MCCommand(
            command="op player",
            requested_by_discord_id="111222333",
            requested_by_username="TestStaff3",
            status="completed",
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(cmd1)
        db.add(cmd2)
        db.add(cmd3)
        await db.commit()
    
    response = await client.get(
        "/api/v1/mc/commands/pending",
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    # All returned commands should be pending
    assert all(cmd["status"] == "pending" for cmd in data)


@pytest.mark.asyncio
async def test_get_mc_commands_pending_unauthenticated_returns_401(client: AsyncClient):
    """GET /mc/commands/pending without auth returns 401."""
    response = await client.get("/api/v1/mc/commands/pending")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_mc_commands_id_complete_marks_completed(client: AsyncClient, db_session):
    """POST /mc/commands/{id}/complete marks command as completed."""
    # Create a pending command
    async with db_session() as db:
        cmd = MCCommand(
            command="say hello",
            requested_by_discord_id="123456789",
            requested_by_username="TestStaff",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(cmd)
        await db.commit()
        await db.refresh(cmd)
    
    response = await client.post(
        f"/api/v1/mc/commands/{cmd.id}/complete",
        json={
            "output": "Command executed successfully",
            "success": True,
        },
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    
    # Verify command was updated
    async with db_session() as db:
        updated_cmd = await db.scalar(select(MCCommand).where(MCCommand.id == cmd.id))
        assert updated_cmd.status == "completed"
        assert updated_cmd.success == True
        assert updated_cmd.output == "Command executed successfully"
        assert updated_cmd.completed_at is not None


@pytest.mark.asyncio
async def test_post_mc_commands_id_complete_marks_failed(client: AsyncClient, db_session):
    """POST /mc/commands/{id}/complete can mark command as failed."""
    # Create a pending command
    async with db_session() as db:
        cmd = MCCommand(
            command="invalid command",
            requested_by_discord_id="123456789",
            requested_by_username="TestStaff",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(cmd)
        await db.commit()
        await db.refresh(cmd)
    
    response = await client.post(
        f"/api/v1/mc/commands/{cmd.id}/complete",
        json={
            "output": "Unknown command",
            "success": False,
        },
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    
    # Verify command was marked as failed
    async with db_session() as db:
        updated_cmd = await db.scalar(select(MCCommand).where(MCCommand.id == cmd.id))
        assert updated_cmd.status == "failed"
        assert updated_cmd.success == False


@pytest.mark.asyncio
async def test_post_mc_commands_id_complete_not_found_returns_404(client: AsyncClient):
    """POST /mc/commands/{id}/complete with non-existent ID returns 404."""
    response = await client.post(
        "/api/v1/mc/commands/99999/complete",
        json={
            "output": "test",
            "success": True,
        },
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_post_mc_commands_id_complete_already_completed_returns_400(client: AsyncClient, db_session):
    """POST /mc/commands/{id}/complete on already completed command returns 400."""
    # Create a completed command
    async with db_session() as db:
        cmd = MCCommand(
            command="say hello",
            requested_by_discord_id="123456789",
            requested_by_username="TestStaff",
            status="completed",
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(cmd)
        await db.commit()
        await db.refresh(cmd)
    
    response = await client.post(
        f"/api/v1/mc/commands/{cmd.id}/complete",
        json={
            "output": "test",
            "success": True,
        },
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 400
    assert "already" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_post_mc_commands_id_complete_unauthenticated_returns_401(client: AsyncClient):
    """POST /mc/commands/{id}/complete without auth returns 401."""
    response = await client.post(
        "/api/v1/mc/commands/1/complete",
        json={
            "output": "test",
            "success": True,
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_mc_command_creates_audit_log(client: AsyncClient, db_session):
    """POST /mc/command creates audit log entry."""
    response = await client.post(
        "/api/v1/mc/command",
        json={
            "command": "ban griefer123",
            "requested_by_discord_id": "123456789",
            "requested_by_username": "AdminUser",
        },
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 201
    
    # Verify audit log was created
    async with db_session() as db:
        audit_log = await db.execute(
            select(AuditLog).where(AuditLog.action == "mc_command.requested")
        )
        logs = audit_log.scalars().all()
        assert len(logs) > 0
        latest_log = logs[-1]
        assert "discord:123456789" == latest_log.actor
        assert latest_log.details_json


@pytest.mark.asyncio
async def test_post_mc_commands_id_complete_creates_audit_log(client: AsyncClient, db_session):
    """POST /mc/commands/{id}/complete creates audit log entry."""
    # Create a pending command
    async with db_session() as db:
        cmd = MCCommand(
            command="say hello",
            requested_by_discord_id="123456789",
            requested_by_username="TestStaff",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(cmd)
        await db.commit()
        await db.refresh(cmd)
    
    response = await client.post(
        f"/api/v1/mc/commands/{cmd.id}/complete",
        json={
            "output": "Executed",
            "success": True,
        },
        headers=PLUGIN_HEADERS,
    )
    assert response.status_code == 200
    
    # Verify audit log was created
    async with db_session() as db:
        audit_log = await db.execute(
            select(AuditLog).where(AuditLog.action == "mc_command.executed")
        )
        logs = audit_log.scalars().all()
        assert len(logs) > 0
        latest_log = logs[-1]
        assert latest_log.actor == "plugin"
        assert latest_log.details_json


# ---------------------------------------------------------------------------
# server_id routing ([PLUGIN] subsystem audit) — a fleet's plugin instances
# must only see/execute commands meant for their own server, not every
# pending command globally.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_mc_command_respects_server_id(client: AsyncClient, db_session):
    """POST /mc/command with an explicit server_id stores it on the row."""
    response = await client.post(
        "/api/v1/mc/command",
        json={
            "command": "say hello",
            "requested_by_discord_id": "123456789",
            "requested_by_username": "TestStaff",
            "server_id": "survival-1",
        },
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 201
    assert response.json()["server_id"] == "survival-1"


@pytest.mark.asyncio
async def test_post_mc_command_defaults_server_id(client: AsyncClient):
    """POST /mc/command without server_id defaults to 'default' (backward
    compatible with any caller not yet updated to send one)."""
    response = await client.post(
        "/api/v1/mc/command",
        json={
            "command": "say hello",
            "requested_by_discord_id": "123456789",
            "requested_by_username": "TestStaff",
        },
        headers={"X-Admin-Key": "test-secret-key"},
    )
    assert response.status_code == 201
    assert response.json()["server_id"] == "default"


@pytest.mark.asyncio
async def test_get_mc_commands_pending_scoped_to_server_id(client: AsyncClient, db_session):
    """GET /mc/commands/pending?server_id=X only returns commands for that
    server — the core bug this fix addresses. Without this, a fleet's
    plugin instances would each execute every server's pending commands."""
    async with db_session() as db:
        db.add(MCCommand(
            command="ban griefer",
            server_id="survival-1",
            requested_by_discord_id="1", requested_by_username="A",
            status="pending", created_at=datetime.now(timezone.utc),
        ))
        db.add(MCCommand(
            command="whitelist add dev",
            server_id="creative-dev",
            requested_by_discord_id="2", requested_by_username="B",
            status="pending", created_at=datetime.now(timezone.utc),
        ))
        await db.commit()

    survival_response = await client.get(
        "/api/v1/mc/commands/pending?server_id=survival-1",
        headers=PLUGIN_HEADERS,
    )
    assert survival_response.status_code == 200
    survival_commands = [c["command"] for c in survival_response.json()]
    assert "ban griefer" in survival_commands
    assert "whitelist add dev" not in survival_commands

    dev_response = await client.get(
        "/api/v1/mc/commands/pending?server_id=creative-dev",
        headers=PLUGIN_HEADERS,
    )
    assert dev_response.status_code == 200
    dev_commands = [c["command"] for c in dev_response.json()]
    assert "whitelist add dev" in dev_commands
    assert "ban griefer" not in dev_commands


@pytest.mark.asyncio
async def test_get_mc_commands_pending_defaults_to_default_server(client: AsyncClient, db_session):
    """A plugin instance not yet passing ?server_id= keeps working exactly
    as before — scoped to the implicit 'default' queue every existing row
    already uses via the column default."""
    async with db_session() as db:
        db.add(MCCommand(
            command="say legacy behavior",
            requested_by_discord_id="1", requested_by_username="A",
            status="pending", created_at=datetime.now(timezone.utc),
            # server_id intentionally omitted — exercises the column default
        ))
        db.add(MCCommand(
            command="say other server",
            server_id="other-server",
            requested_by_discord_id="2", requested_by_username="B",
            status="pending", created_at=datetime.now(timezone.utc),
        ))
        await db.commit()

    response = await client.get("/api/v1/mc/commands/pending", headers=PLUGIN_HEADERS)
    assert response.status_code == 200
    commands = [c["command"] for c in response.json()]
    assert "say legacy behavior" in commands
    assert "say other server" not in commands
