"""
tests/test_mc_commands.py — MC command execution API tests.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from models import MCCommand, AuditLog
from datetime import datetime


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
            created_at=datetime.utcnow(),
        )
        cmd2 = MCCommand(
            command="gamemode creative",
            requested_by_discord_id="987654321",
            requested_by_username="TestStaff2",
            status="pending",
            created_at=datetime.utcnow(),
        )
        cmd3 = MCCommand(
            command="op player",
            requested_by_discord_id="111222333",
            requested_by_username="TestStaff3",
            status="completed",
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db.add(cmd1)
        db.add(cmd2)
        db.add(cmd3)
        await db.commit()
    
    response = await client.get(
        "/api/v1/mc/commands/pending",
        headers={"X-Admin-Key": "test-secret-key"},
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
            created_at=datetime.utcnow(),
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
        headers={"X-Admin-Key": "test-secret-key"},
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
            created_at=datetime.utcnow(),
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
        headers={"X-Admin-Key": "test-secret-key"},
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
        headers={"X-Admin-Key": "test-secret-key"},
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
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
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
        headers={"X-Admin-Key": "test-secret-key"},
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
            created_at=datetime.utcnow(),
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
        headers={"X-Admin-Key": "test-secret-key"},
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
