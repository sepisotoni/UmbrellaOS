"""
tests/test_backup_service.py — Tests for services/backup_service.py, using
an injected fake DaemonClient (same DI pattern as test_hosting_services.py).
"""
import pytest

from services.allocation_service import AllocationService
from services.backup_service import BackupError, BackupService
from services.daemon_client import DaemonError
from services.node_service import NodeService
from services.server_service import ServerService
from services.server_template_service import ServerTemplateService


class FakeBackupDaemonClient:
    def __init__(self, fail_on: set[str] | None = None):
        self.calls: list[tuple] = []
        self._fail_on = fail_on or set()

    async def create(self, server_id, **kwargs):
        from services.daemon_client import ContainerState
        self.calls.append(("create", server_id))
        return ContainerState(server_id=server_id, runtime_id="d", status="created",
                               started_at=None, finished_at=None, exit_code=None, oom_killed=False)

    async def create_backup(self, server_id, backup_id):
        self.calls.append(("create_backup", server_id, backup_id))
        if "create_backup" in self._fail_on:
            raise DaemonError("simulated backup failure")
        return 12345

    async def restore_backup(self, server_id, backup_id):
        self.calls.append(("restore_backup", server_id, backup_id))
        if "restore_backup" in self._fail_on:
            raise DaemonError("simulated restore failure")

    async def delete_backup(self, server_id, backup_id):
        self.calls.append(("delete_backup", server_id, backup_id))
        if "delete_backup" in self._fail_on:
            raise DaemonError("simulated delete failure")


async def _setup_server(db_session, fake_client):
    async with db_session() as db:
        node, _ = await NodeService.register_node(db, "node-backup-test", "https://node:8443")
        template = await ServerTemplateService.create_template(db, "Paper", image="itzg/minecraft-server")
        await db.commit()
        node_id, template_id = node.id, template.id

    async with db_session() as db:
        allocation = await AllocationService.create_allocation(db, node_id, 25565)
        await db.commit()
        allocation_id = allocation.id

    async with db_session() as db:
        server = await ServerService.create_server(
            db, "Survival", node_id, template_id, [allocation_id], daemon_client=fake_client
        )
        await db.commit()
        return server.id


@pytest.mark.asyncio
async def test_create_backup_happy_path(db_session):
    fake_client = FakeBackupDaemonClient()
    server_id = await _setup_server(db_session, fake_client)

    async with db_session() as db:
        backup = await BackupService.create_backup(db, server_id, daemon_client=fake_client)
        await db.commit()
        assert backup.status == "completed"
        assert backup.size_bytes == 12345
        assert backup.completed_at is not None

    assert ("create_backup", server_id, backup.id) in fake_client.calls


@pytest.mark.asyncio
async def test_create_backup_failure_marks_status_failed_but_keeps_row(db_session):
    fake_client = FakeBackupDaemonClient(fail_on={"create_backup"})
    server_id = await _setup_server(db_session, fake_client)

    async with db_session() as db:
        with pytest.raises(BackupError):
            await BackupService.create_backup(db, server_id, daemon_client=fake_client)
        await db.commit()

    async with db_session() as db:
        backups = await BackupService.list_backups(db, server_id)
        assert len(backups) == 1
        assert backups[0].status == "failed"
        assert backups[0].error_message is not None


@pytest.mark.asyncio
async def test_list_backups_orders_newest_first(db_session):
    fake_client = FakeBackupDaemonClient()
    server_id = await _setup_server(db_session, fake_client)

    async with db_session() as db:
        first = await BackupService.create_backup(db, server_id, daemon_client=fake_client)
        await db.commit()
    async with db_session() as db:
        second = await BackupService.create_backup(db, server_id, daemon_client=fake_client)
        await db.commit()

    async with db_session() as db:
        backups = await BackupService.list_backups(db, server_id)
        assert [b.id for b in backups] == [second.id, first.id]


@pytest.mark.asyncio
async def test_restore_backup_happy_path(db_session):
    fake_client = FakeBackupDaemonClient()
    server_id = await _setup_server(db_session, fake_client)

    async with db_session() as db:
        backup = await BackupService.create_backup(db, server_id, daemon_client=fake_client)
        await db.commit()
        backup_id = backup.id

    async with db_session() as db:
        await BackupService.restore_backup(db, backup_id, daemon_client=fake_client)

    assert ("restore_backup", server_id, backup_id) in fake_client.calls


@pytest.mark.asyncio
async def test_restore_refuses_a_failed_backup(db_session):
    fake_client = FakeBackupDaemonClient(fail_on={"create_backup"})
    server_id = await _setup_server(db_session, fake_client)

    async with db_session() as db:
        with pytest.raises(BackupError):
            await BackupService.create_backup(db, server_id, daemon_client=fake_client)
        await db.commit()

    async with db_session() as db:
        backups = await BackupService.list_backups(db, server_id)
        failed_backup_id = backups[0].id

    fake_client2 = FakeBackupDaemonClient()
    async with db_session() as db:
        with pytest.raises(BackupError, match="not 'completed'"):
            await BackupService.restore_backup(db, failed_backup_id, daemon_client=fake_client2)


@pytest.mark.asyncio
async def test_delete_backup_removes_row_and_calls_daemon(db_session):
    fake_client = FakeBackupDaemonClient()
    server_id = await _setup_server(db_session, fake_client)

    async with db_session() as db:
        backup = await BackupService.create_backup(db, server_id, daemon_client=fake_client)
        await db.commit()
        backup_id = backup.id

    async with db_session() as db:
        await BackupService.delete_backup(db, backup_id, daemon_client=fake_client)
        await db.commit()

    async with db_session() as db:
        with pytest.raises(BackupError):
            await BackupService.get_backup(db, backup_id)

    assert ("delete_backup", server_id, backup_id) in fake_client.calls


@pytest.mark.asyncio
async def test_get_backup_raises_404_for_unknown_id(db_session):
    async with db_session() as db:
        with pytest.raises(BackupError):
            await BackupService.get_backup(db, "00000000-0000-0000-0000-000000000000")
