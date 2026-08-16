"""
services/memory/service.py — Ported from Moo-assistant's
bot/services/memory_service.py.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.memory import MemoryEntry, MemoryScope
from services.memory.repository import MemoryRepository


class MemoryService:
    """Short-term / server / operational memory, per the three memory types:

    - short_term: conversational context (e.g. what a prior AI call was
      discussing with this user in this channel), expires after
      settings.short_term_memory_ttl_seconds.
    - server: durable facts about the server (server IP, store URL, voting
      link...), no expiry unless the caller explicitly sets one.
    - operational: recurring issues/questions and how they were resolved,
      tracked via hit_count so the most common resolutions can be
      surfaced first.
    """

    # --- short-term (conversational) ---
    @staticmethod
    async def remember_conversation_turn(
        db: AsyncSession, *, channel_id: str, user_id: str, summary: str
    ) -> None:
        key = f"conversation:{channel_id}:{user_id}"
        expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
            seconds=get_settings().short_term_memory_ttl_seconds
        )
        await MemoryRepository.upsert(
            db, scope=MemoryScope.SHORT_TERM, key=key, value=summary, expires_at=expires_at, increment_hit=False
        )

    @staticmethod
    async def recall_conversation_turn(db: AsyncSession, *, channel_id: str, user_id: str) -> str | None:
        key = f"conversation:{channel_id}:{user_id}"
        entry = await MemoryRepository.get(db, MemoryScope.SHORT_TERM, key)
        return entry.value if entry else None

    # --- server facts ---
    @staticmethod
    async def set_server_fact(db: AsyncSession, *, fact_key: str, value: str) -> None:
        await MemoryRepository.upsert(
            db, scope=MemoryScope.SERVER, key=f"fact:{fact_key}", value=value, expires_at=None, increment_hit=False
        )

    @staticmethod
    async def get_server_fact(db: AsyncSession, *, fact_key: str) -> str | None:
        entry = await MemoryRepository.get(db, MemoryScope.SERVER, f"fact:{fact_key}")
        return entry.value if entry else None

    @staticmethod
    async def list_server_facts(db: AsyncSession) -> list[MemoryEntry]:
        return await MemoryRepository.list_scope(db, MemoryScope.SERVER)

    # --- operational memory (recurring issues/questions + resolutions) ---
    @staticmethod
    async def record_recurring(db: AsyncSession, *, topic_key: str, resolution: str) -> None:
        """Call whenever a support/investigation flow resolves something,
        to build up a record of common issues and how they were solved.
        hit_count increments automatically on repeat calls for the same
        topic_key."""
        await MemoryRepository.upsert(
            db,
            scope=MemoryScope.OPERATIONAL,
            key=f"recurring:{topic_key}",
            value=resolution,
            expires_at=None,
            increment_hit=True,
        )

    @staticmethod
    async def get_recurring(db: AsyncSession, *, topic_key: str) -> str | None:
        entry = await MemoryRepository.get(db, MemoryScope.OPERATIONAL, f"recurring:{topic_key}")
        return entry.value if entry else None

    @staticmethod
    async def top_recurring(db: AsyncSession, limit: int = 10) -> list[MemoryEntry]:
        return await MemoryRepository.list_scope(db, MemoryScope.OPERATIONAL, limit=limit)

    # --- maintenance ---
    @staticmethod
    async def purge_expired(db: AsyncSession) -> int:
        return await MemoryRepository.purge_expired(db)
