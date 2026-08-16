"""
services/knowledge/service.py — Ported and merged from Moo-assistant's
bot/knowledge/indexer.py, retriever.py, and learning_service.py.

Merged into one module rather than kept as three separate classes: Moo
split these across different bot lifecycle event handlers (on_message,
on_message_edit, a staff command), which made sense for where each was
*called from* in a live bot process. umbrella-core has no such lifecycle -
everything here is invoked by a capability call - so the split no longer
tracks anything meaningful; it's all "knowledge domain business logic"
now.

Real fix from the source, not a straight port: `index_entry` (Moo's
`index_message`) checks for an existing row by `discord_message_id` first
and updates it instead of blindly inserting. The source never did this -
since discord_message_id is unique, reprocessing the same message (a
backfill, a duplicate event) would raise an IntegrityError instead of
gracefully upserting.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.knowledge import KnowledgeEntry
from services.knowledge.repository import KnowledgeRepository


def channel_names_configured() -> set[str]:
    """Parses config.settings.knowledge_channel_names (comma-separated)
    into a set. Empty setting -> empty set -> is_knowledge_channel() is
    False for everything, matching "index nothing until configured"."""
    raw = get_settings().knowledge_channel_names
    return {name.strip().lower() for name in raw.split(",") if name.strip()}


def is_knowledge_channel(channel_name: str) -> bool:
    return channel_name.lower() in channel_names_configured()


class KnowledgeService:
    @staticmethod
    async def index_entry(
        db: AsyncSession,
        *,
        channel_id: str,
        channel_name: str,
        discord_message_id: str,
        author_id: str,
        author_name: str,
        content: str,
    ) -> KnowledgeEntry | None:
        """
        Indexes a message into the knowledge base if its channel is
        configured for indexing. Idempotent: a second call for the same
        discord_message_id updates the existing entry's content (and
        snapshots the prior content as a version first) rather than
        raising on the unique constraint - the bug fix described in this
        module's docstring.

        Returns None if the channel isn't a configured knowledge channel
        (nothing was indexed) or the content is empty.
        """
        if not is_knowledge_channel(channel_name) or not content:
            return None

        existing = await KnowledgeRepository.get_by_discord_message_id(db, discord_message_id)
        if existing is not None:
            if existing.content != content:
                await KnowledgeRepository.snapshot_version(db, existing, edited_by=author_id)
                existing.content = content
                await db.flush()
            return existing

        entry = KnowledgeEntry(
            channel_id=channel_id,
            channel_name=channel_name,
            discord_message_id=discord_message_id,
            author_id=author_id,
            author_name=author_name,
            content=content,
        )
        db.add(entry)
        await db.flush()
        return entry

    @staticmethod
    async def search(db: AsyncSession, query: str, limit: int = 5) -> list[KnowledgeEntry]:
        return await KnowledgeRepository.search(db, query, limit=limit)

    @staticmethod
    async def propose_correction(
        db: AsyncSession,
        *,
        original_entry_id: str,
        channel_id: str,
        channel_name: str,
        discord_message_id: str,
        author_id: str,
        author_name: str,
        content: str,
    ) -> KnowledgeEntry:
        return await KnowledgeRepository.create_correction(
            db,
            channel_id=channel_id,
            channel_name=channel_name,
            original_entry_id=original_entry_id,
            discord_message_id=discord_message_id,
            author_id=author_id,
            author_name=author_name,
            content=content,
        )

    @staticmethod
    async def list_pending(db: AsyncSession) -> list[KnowledgeEntry]:
        return await KnowledgeRepository.list_pending(db)

    @staticmethod
    async def approve(db: AsyncSession, entry_id: str, *, reviewed_by: str) -> KnowledgeEntry | None:
        return await KnowledgeRepository.approve(db, entry_id, reviewed_by=reviewed_by)

    @staticmethod
    async def reject(db: AsyncSession, entry_id: str, *, reviewed_by: str) -> KnowledgeEntry | None:
        return await KnowledgeRepository.reject(db, entry_id, reviewed_by=reviewed_by)

    @staticmethod
    async def history(db: AsyncSession, knowledge_entry_id: str):
        return await KnowledgeRepository.history(db, knowledge_entry_id)
