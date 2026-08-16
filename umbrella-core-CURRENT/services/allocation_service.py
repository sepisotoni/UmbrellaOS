"""
services/allocation_service.py — Port allocations: one port on one node,
either free or bound to a Server.

The (node_id, port, protocol) uniqueness constraint lives in the database
(models/hosting.py's Allocation.__table_args__) — this service catches the
resulting IntegrityError and raises a clear, specific AllocationError
rather than letting a raw database exception surface to a capability caller.
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.middleware.errors import AppException
from models.hosting import Allocation


class AllocationError(AppException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, "ALLOCATION_ERROR", status_code)


class AllocationService:
    @staticmethod
    async def create_allocation(
        db: AsyncSession,
        node_id: str,
        port: int,
        protocol: str = "tcp",
    ) -> Allocation:
        allocation = Allocation(node_id=node_id, port=port, protocol=protocol)
        db.add(allocation)
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise AllocationError(
                f"port {port}/{protocol} is already allocated on this node", 409
            ) from exc
        return allocation

    @staticmethod
    async def list_free_allocations(db: AsyncSession, node_id: str) -> list[Allocation]:
        result = await db.execute(
            select(Allocation).where(Allocation.node_id == node_id, Allocation.server_id.is_(None))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_allocation(db: AsyncSession, allocation_id: str) -> Allocation:
        allocation = await db.get(Allocation, allocation_id)
        if allocation is None:
            raise AllocationError(f"no allocation with id {allocation_id!r}", 404)
        return allocation

    @staticmethod
    async def bind_allocation(
        db: AsyncSession,
        allocation_id: str,
        server_id: str,
        container_port: int,
    ) -> Allocation:
        allocation = await AllocationService.get_allocation(db, allocation_id)
        if allocation.server_id is not None and allocation.server_id != server_id:
            raise AllocationError(
                f"allocation {allocation_id!r} is already bound to a different server", 409
            )
        allocation.server_id = server_id
        allocation.container_port = container_port
        await db.flush()
        return allocation

    @staticmethod
    async def release_allocation(db: AsyncSession, allocation_id: str) -> Allocation:
        allocation = await AllocationService.get_allocation(db, allocation_id)
        allocation.server_id = None
        allocation.container_port = None
        await db.flush()
        return allocation
