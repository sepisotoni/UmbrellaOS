"""
services/memory/repository.py — Ported from Moo-assistant's MemoryRepository
(bot/repositories/ai_state_repository.py). Adapted to umbrella-core's
dependency-injected AsyncSession convention.

Real fix from the source: `upsert`'s select-then-insert-or-update is a
classic check-then-act race - two concurrent calls for the same
(scope, key) can both see "no existing entry" and both attempt an insert,
the second hitting the unique constraint as an uncaught IntegrityError
instead of gracefully updating. Fixed here with a catch-and-retry: attempt
the insert, and on a unique-constraint violation, fall back to the update
path. A dialect-native upsert (Postgres/SQLite both support
INSERT ... ON CONFLICT) would avoid the extra round-trip on the race path,
but would need dialect-specific SQL construction to work identically on
both the SQLite this test suite runs against and the Postgres production
targets. Catch-and-retry is portable across both with one code path, and
memory-key contention is low-stakes/low-frequency enough that the extra
round trip only on an actual race (not on every call) is the right
trade-off here - unlike services/ai/model_router.py's health-tracking
race, which is hit on every single AI call under load and got a proper
atomic SQL UPDATE instead.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.memory import MemoryEntry, MemoryScope


class MemoryRepository:
    @staticmethod
    async def get(db: AsyncSession, scope: MemoryScope, key: str) -> MemoryEntry | None:
        stmt = select(MemoryEntry).where(MemoryEntry.scope == scope, MemoryEntry.key == key)
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry is not None and entry.expires_at is not None:
            expires_at = entry.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
            if expires_at < dt.datetime.now(dt.timezone.utc):
                return None  # expired; caller treats this as a miss (lazy expiry)
        return entry

    @staticmethod
    async def upsert(
        db: AsyncSession,
        *,
        scope: MemoryScope,
        key: str,
        value: str,
        expires_at: dt.datetime | None,
        increment_hit: bool = True,
    ) -> MemoryEntry:
        stmt = select(MemoryEntry).where(MemoryEntry.scope == scope, MemoryEntry.key == key)
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()

        if entry is not None:
            entry.value = value
            entry.expires_at = expires_at
            if increment_hit:
                entry.hit_count += 1
            await db.flush()
            return entry

        entry = MemoryEntry(scope=scope, key=key, value=value, expires_at=expires_at)
        try:
            async with db.begin_nested():
                db.add(entry)
                await db.flush()
        except IntegrityError:
            # Lost the race: another call inserted the same (scope, key)
            # between our SELECT above and this flush. begin_nested() uses
            # a SAVEPOINT, so only this insert attempt rolls back - not
            # any other pending work the caller's session might hold, the
            # way a full db.rollback() would. The rollback itself already
            # detaches the failed `entry` object from the session (no
            # manual expunge needed - attempting one here raises
            # InvalidRequestError, since it's already gone). Fall back to
            # the update path against whatever the winner just created.
            result = await db.execute(stmt)
            entry = result.scalar_one()
            entry.value = value
            entry.expires_at = expires_at
            if increment_hit:
                entry.hit_count += 1
            await db.flush()

        return entry

    @staticmethod
    async def list_scope(db: AsyncSession, scope: MemoryScope, limit: int = 50) -> list[MemoryEntry]:
        stmt = (
            select(MemoryEntry)
            .where(MemoryEntry.scope == scope)
            .order_by(MemoryEntry.hit_count.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def purge_expired(db: AsyncSession) -> int:
        """Sweep expired entries. Returns the number removed. Safe to call periodically."""
        now = dt.datetime.now(dt.timezone.utc)
        stmt = delete(MemoryEntry).where(MemoryEntry.expires_at.is_not(None), MemoryEntry.expires_at < now)
        result = await db.execute(stmt)
        return result.rowcount
