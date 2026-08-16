"""
services/archive_search/service.py — Adapted from Moo-assistant's
SearchService (bot/services/search_service.py).

Real scope reduction from the source, not a straight port: Moo's version
is genuinely "permission-aware" in a per-Discord-member sense - staff see
everything, everyone else is restricted to channels they can currently
view in Discord (computed from live discord.Guild/discord.Member role and
per-channel permission-overwrite state). That computation fundamentally
requires a live Discord gateway connection - it's not something that can
be derived from anything stored in this database, the same dependency gap
as moderation's warn/timeout execution and investigation's original
maybe_auto_apply.

What's built here instead: a single staff-tier search over
models.discord.ChatMessage (which already exists and is already populated
by api/routers/bridge.py - no new archiving pipeline needed), gated by
umbrella-core's own RBAC ("archive.search", granted moderator+, not the
lower-trust helper tier investigation/knowledge search capabilities use -
unlike those, this reveals unfiltered chat content across every channel,
with no per-channel restriction possible yet).

Per-member channel-visibility filtering is real, deferred Phase 6 work,
not something to fake here - a stubbed "always visible" check would be a
false sense of security, and a stubbed "never visible" check would make
the capability pointless. Wire it in once a live guild/channel-permission
mirror exists.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.discord import ChatMessage


@dataclass(frozen=True)
class ArchiveSearchResult:
    message_id: int
    source: str
    channel_id: str | None
    author_name: str | None
    content: str
    timestamp: str


async def search(
    db: AsyncSession, query: str, *, source: str | None = None, limit: int = 10
) -> list[ArchiveSearchResult]:
    """
    ILIKE keyword search over archived chat, most recent first. `source`
    optionally restricts to "minecraft" or "discord"; omitted searches
    both. An empty query matches everything (same "no-op filter" behavior
    as services/knowledge/repository.py's search - deliberate, not a bug).
    """
    like = f"%{query}%"
    stmt = select(ChatMessage).where(ChatMessage.message.ilike(like))
    if source is not None:
        stmt = stmt.where(ChatMessage.source == source)
    stmt = stmt.order_by(ChatMessage.timestamp.desc()).limit(limit)

    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    return [
        ArchiveSearchResult(
            message_id=row.id,
            source=row.source,
            channel_id=row.discord_channel_id,
            author_name=row.player_name,
            content=row.message,
            timestamp=row.timestamp.isoformat(),
        )
        for row in rows
    ]
