"""
capabilities/knowledge.py — Knowledge base capabilities (Phase 5), ported
from Moo-assistant's bot/knowledge/*.py. See services/knowledge/service.py's
module docstring for the merge/idempotency-fix rationale.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from api.middleware.errors import ResourceNotFoundException
from registry.context import CallContext
from registry.decorator import capability
from services.knowledge.service import KnowledgeService


class EntryResult(BaseModel):
    id: str
    channel_name: str
    content: str
    review_status: str
    confidence_score: float


def _entry_to_result(entry) -> EntryResult:
    return EntryResult(
        id=entry.id,
        channel_name=entry.channel_name,
        content=entry.content,
        review_status=entry.review_status.value,
        confidence_score=entry.confidence_score,
    )


# --------------------------------------------------------------------------
# knowledge.entry.index
# --------------------------------------------------------------------------


class IndexEntryParams(BaseModel):
    channel_id: str
    channel_name: str
    discord_message_id: str
    author_id: str
    author_name: str
    content: str

    def audit_target(self) -> str:
        return self.discord_message_id


class IndexEntryResult(BaseModel):
    indexed: bool
    entry: EntryResult | None = None


@capability(
    name="knowledge.entry.index",
    summary="Index a message into the knowledge base, if its channel is configured for indexing.",
    params_model=IndexEntryParams,
    result_model=IndexEntryResult,
    required_permission="knowledge.entry.manage",
    destructive=False,
    reversible=True,
)
async def index_entry(ctx: CallContext, params: IndexEntryParams) -> IndexEntryResult:
    entry = await KnowledgeService.index_entry(
        ctx.db,
        channel_id=params.channel_id,
        channel_name=params.channel_name,
        discord_message_id=params.discord_message_id,
        author_id=params.author_id,
        author_name=params.author_name,
        content=params.content,
    )
    if entry is None:
        return IndexEntryResult(indexed=False)
    return IndexEntryResult(indexed=True, entry=_entry_to_result(entry))


# --------------------------------------------------------------------------
# knowledge.entry.search
# --------------------------------------------------------------------------


class SearchParams(BaseModel):
    query: str = Field(default="", description="Keyword to search for; empty returns most recent entries")
    limit: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    entries: list[EntryResult]


@capability(
    name="knowledge.entry.search",
    summary="Search the knowledge base by keyword.",
    params_model=SearchParams,
    result_model=SearchResult,
    required_permission="knowledge.entry.search",
    destructive=False,
    reversible=True,
    audited=False,
)
async def search(ctx: CallContext, params: SearchParams) -> SearchResult:
    entries = await KnowledgeService.search(ctx.db, params.query, limit=params.limit)
    return SearchResult(entries=[_entry_to_result(e) for e in entries])


# --------------------------------------------------------------------------
# knowledge.correction.propose
# --------------------------------------------------------------------------


class ProposeCorrectionParams(BaseModel):
    original_entry_id: str
    channel_id: str
    channel_name: str
    discord_message_id: str
    author_id: str
    author_name: str
    content: str

    def audit_target(self) -> str:
        return self.original_entry_id


@capability(
    name="knowledge.correction.propose",
    summary="Propose a correction to an existing knowledge entry, pending staff approval.",
    params_model=ProposeCorrectionParams,
    result_model=EntryResult,
    required_permission="knowledge.entry.manage",
    destructive=False,
    reversible=True,
)
async def propose_correction(ctx: CallContext, params: ProposeCorrectionParams) -> EntryResult:
    entry = await KnowledgeService.propose_correction(
        ctx.db,
        original_entry_id=params.original_entry_id,
        channel_id=params.channel_id,
        channel_name=params.channel_name,
        discord_message_id=params.discord_message_id,
        author_id=params.author_id,
        author_name=params.author_name,
        content=params.content,
    )
    return _entry_to_result(entry)


# --------------------------------------------------------------------------
# knowledge.correction.list_pending
# --------------------------------------------------------------------------


class NoParams(BaseModel):
    pass


class ListPendingResult(BaseModel):
    entries: list[EntryResult]


@capability(
    name="knowledge.correction.list_pending",
    summary="List knowledge corrections awaiting staff review.",
    params_model=NoParams,
    result_model=ListPendingResult,
    required_permission="knowledge.correction.review",
    destructive=False,
    reversible=True,
    audited=False,
)
async def list_pending(ctx: CallContext, params: NoParams) -> ListPendingResult:
    entries = await KnowledgeService.list_pending(ctx.db)
    return ListPendingResult(entries=[_entry_to_result(e) for e in entries])


# --------------------------------------------------------------------------
# knowledge.correction.approve / reject
# --------------------------------------------------------------------------


class ReviewCorrectionParams(BaseModel):
    entry_id: str

    def audit_target(self) -> str:
        return self.entry_id


@capability(
    name="knowledge.correction.approve",
    summary="Approve a pending knowledge correction, superseding the entry it corrects.",
    params_model=ReviewCorrectionParams,
    result_model=EntryResult,
    required_permission="knowledge.correction.review",
    destructive=False,
    reversible=True,
)
async def approve(ctx: CallContext, params: ReviewCorrectionParams) -> EntryResult:
    entry = await KnowledgeService.approve(ctx.db, params.entry_id, reviewed_by=ctx.actor_id)
    if entry is None:
        raise ResourceNotFoundException("Knowledge entry", params.entry_id)
    return _entry_to_result(entry)


@capability(
    name="knowledge.correction.reject",
    summary="Reject a pending knowledge correction.",
    params_model=ReviewCorrectionParams,
    result_model=EntryResult,
    required_permission="knowledge.correction.review",
    destructive=False,
    reversible=True,
)
async def reject(ctx: CallContext, params: ReviewCorrectionParams) -> EntryResult:
    entry = await KnowledgeService.reject(ctx.db, params.entry_id, reviewed_by=ctx.actor_id)
    if entry is None:
        raise ResourceNotFoundException("Knowledge entry", params.entry_id)
    return _entry_to_result(entry)
