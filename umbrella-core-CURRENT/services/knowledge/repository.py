"""
services/knowledge/repository.py — Data access for the knowledge domain,
ported from Moo-assistant's KnowledgeReviewRepository plus the raw queries
KnowledgeIndexer/KnowledgeRetriever did inline. Adapted to umbrella-core's
dependency-injected AsyncSession convention.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.knowledge import KnowledgeEntry, KnowledgeReviewStatus, KnowledgeVersion


class KnowledgeRepository:
    @staticmethod
    async def get_by_discord_message_id(db: AsyncSession, discord_message_id: str) -> KnowledgeEntry | None:
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.discord_message_id == discord_message_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def search(db: AsyncSession, query: str, limit: int = 5) -> list[KnowledgeEntry]:
        """
        Simple ILIKE keyword search over approved, non-superseded entries -
        intentionally lightweight (no external embedding/vector-store
        dependency), same tradeoff the source made. Swap for a
        pgvector-backed similarity search if richer retrieval is needed
        later.

        An empty query matches every entry (ILIKE '%%' is a no-op filter),
        which callers rely on deliberately to get "most recent entries"
        via ordering + limit alone, not a bug to guard against.
        """
        like = f"%{query}%"
        stmt = (
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.content.ilike(like),
                KnowledgeEntry.review_status == KnowledgeReviewStatus.APPROVED,
                KnowledgeEntry.superseded_by_id.is_(None),
            )
            .order_by(KnowledgeEntry.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def snapshot_version(db: AsyncSession, entry: KnowledgeEntry, *, edited_by: str | None) -> KnowledgeVersion:
        """Archives the entry's *current* content as a new version row
        before it changes. Uses a SQL MAX() rather than fetching every
        existing version just to compute it in Python (the source's
        approach) - a knowledge entry with a long edit history shouldn't
        mean an ever-growing fetch just to number the next version."""
        stmt = select(func.max(KnowledgeVersion.version_number)).where(
            KnowledgeVersion.knowledge_entry_id == entry.id
        )
        current_max = (await db.execute(stmt)).scalar_one_or_none()
        next_version = (current_max or 0) + 1

        version = KnowledgeVersion(
            knowledge_entry_id=entry.id, version_number=next_version, content=entry.content, edited_by=edited_by
        )
        db.add(version)
        await db.flush()
        return version

    @staticmethod
    async def history(db: AsyncSession, knowledge_entry_id: str) -> list[KnowledgeVersion]:
        stmt = (
            select(KnowledgeVersion)
            .where(KnowledgeVersion.knowledge_entry_id == knowledge_entry_id)
            .order_by(KnowledgeVersion.version_number.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_correction(
        db: AsyncSession,
        *,
        channel_id: str,
        channel_name: str,
        original_entry_id: str,
        discord_message_id: str,
        author_id: str,
        author_name: str,
        content: str,
    ) -> KnowledgeEntry:
        """Submits a proposed correction as a new PENDING entry linked to
        the entry it would replace. Does not affect retrieval until
        approved (search() only ever returns APPROVED, non-superseded
        entries)."""
        correction = KnowledgeEntry(
            channel_id=channel_id,
            channel_name=channel_name,
            discord_message_id=discord_message_id,
            author_id=author_id,
            author_name=author_name,
            content=content,
            confidence_score=0.5,
            review_status=KnowledgeReviewStatus.PENDING,
            corrects_entry_id=original_entry_id,
        )
        db.add(correction)
        await db.flush()
        return correction

    @staticmethod
    async def list_pending(db: AsyncSession) -> list[KnowledgeEntry]:
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.review_status == KnowledgeReviewStatus.PENDING)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def approve(db: AsyncSession, entry_id: str, *, reviewed_by: str) -> KnowledgeEntry | None:
        entry = await db.get(KnowledgeEntry, entry_id)
        if entry is None:
            return None
        entry.review_status = KnowledgeReviewStatus.APPROVED
        entry.confidence_score = 1.0
        entry.reviewed_by = reviewed_by
        entry.reviewed_at = datetime.now(timezone.utc)

        if entry.corrects_entry_id is not None:
            superseded = await db.get(KnowledgeEntry, entry.corrects_entry_id)
            if superseded is not None:
                superseded.superseded_by_id = entry.id

        await db.flush()
        return entry

    @staticmethod
    async def reject(db: AsyncSession, entry_id: str, *, reviewed_by: str) -> KnowledgeEntry | None:
        entry = await db.get(KnowledgeEntry, entry_id)
        if entry is None:
            return None
        entry.review_status = KnowledgeReviewStatus.REJECTED
        entry.reviewed_by = reviewed_by
        entry.reviewed_at = datetime.now(timezone.utc)
        await db.flush()
        return entry
