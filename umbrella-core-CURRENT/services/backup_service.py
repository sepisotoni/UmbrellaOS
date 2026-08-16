"""
services/backup_service.py — Backup metadata and orchestration.

Metadata (which backup exists, its status, size, timestamps) lives here in
umbrella-core; the archive bytes themselves are created/restored by
umbrella-daemon's internal/backup package on the server's actual node —
this service's job is sequencing those calls and keeping the Backup row's
status honest, never touching archive bytes directly.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import AppException
from models.hosting import Backup
from services.daemon_client import DaemonClient, DaemonError
from services.server_service import ServerService


class BackupError(AppException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, "BACKUP_ERROR", status_code)


class BackupService:
    @staticmethod
    async def create_backup(
        db: AsyncSession, server_id: str, daemon_client: DaemonClient | None = None
    ) -> Backup:
        server = await ServerService.get_server(db, server_id)

        backup = Backup(server_id=server_id, status="pending")
        db.add(backup)
        await db.flush()

        client = await ServerService.client_for(db, server, daemon_client)
        try:
            size_bytes = await client.create_backup(server_id, backup.id)
        except DaemonError as exc:
            # The Backup row itself is kept (status="failed"), not rolled
            # back — a failed backup attempt is exactly the kind of thing
            # an operator needs visible in history, not silently erased
            # because the underlying daemon call failed.
            backup.status = "failed"
            backup.error_message = str(exc)
            await db.flush()
            raise BackupError(f"backup failed: {exc}", 502) from exc

        backup.status = "completed"
        backup.size_bytes = size_bytes
        backup.completed_at = datetime.now(timezone.utc)
        await db.flush()
        return backup

    @staticmethod
    async def list_backups(db: AsyncSession, server_id: str) -> list[Backup]:
        result = await db.execute(
            select(Backup).where(Backup.server_id == server_id).order_by(Backup.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_backup(db: AsyncSession, backup_id: str) -> Backup:
        backup = await db.get(Backup, backup_id)
        if backup is None:
            raise BackupError(f"no backup with id {backup_id!r}", 404)
        return backup

    @staticmethod
    async def restore_backup(
        db: AsyncSession, backup_id: str, daemon_client: DaemonClient | None = None
    ) -> None:
        backup = await BackupService.get_backup(db, backup_id)
        if backup.status != "completed":
            raise BackupError(
                f"cannot restore backup {backup_id!r}: its status is {backup.status!r}, not 'completed'"
            )

        server = await ServerService.get_server(db, backup.server_id)
        client = await ServerService.client_for(db, server, daemon_client)
        try:
            await client.restore_backup(backup.server_id, backup.id)
        except DaemonError as exc:
            raise BackupError(f"restore failed: {exc}", 502) from exc

    @staticmethod
    async def delete_backup(
        db: AsyncSession, backup_id: str, daemon_client: DaemonClient | None = None
    ) -> None:
        backup = await BackupService.get_backup(db, backup_id)
        server = await ServerService.get_server(db, backup.server_id)
        client = await ServerService.client_for(db, server, daemon_client)
        try:
            await client.delete_backup(backup.server_id, backup.id)
        except DaemonError as exc:
            raise BackupError(f"failed to delete backup archive: {exc}", 502) from exc

        await db.delete(backup)
        await db.flush()
