"""
capabilities/archive_search.py — Staff-tier archive search (Phase 5).
See services/archive_search/service.py's module docstring for the scope
reduction from Moo's per-member permission-aware version.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from registry.context import CallContext
from registry.decorator import capability
from services.archive_search.service import search as search_archive


class SearchArchiveParams(BaseModel):
    query: str = Field(default="", description="Keyword to search archived chat for; empty returns most recent")
    source: str | None = Field(default=None, description='Restrict to "minecraft" or "discord"; omit for both')
    limit: int = Field(default=10, ge=1, le=50)


class ArchiveMessageResult(BaseModel):
    message_id: int
    source: str
    channel_id: str | None
    author_name: str | None
    content: str
    timestamp: str


class SearchArchiveResult(BaseModel):
    messages: list[ArchiveMessageResult]


@capability(
    name="archive.search",
    summary="Search archived chat history (Minecraft and Discord).",
    params_model=SearchArchiveParams,
    result_model=SearchArchiveResult,
    required_permission="archive.search",
    destructive=False,
    reversible=True,
    audited=True,  # unlike knowledge/investigation search, this reveals unfiltered chat content - worth an audit trail
)
async def search(ctx: CallContext, params: SearchArchiveParams) -> SearchArchiveResult:
    results = await search_archive(ctx.db, params.query, source=params.source, limit=params.limit)
    return SearchArchiveResult(
        messages=[
            ArchiveMessageResult(
                message_id=r.message_id,
                source=r.source,
                channel_id=r.channel_id,
                author_name=r.author_name,
                content=r.content,
                timestamp=r.timestamp,
            )
            for r in results
        ]
    )
