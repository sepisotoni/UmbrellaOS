"""
capabilities/memory.py — Memory domain capabilities (Phase 5), ported from
Moo-assistant's bot/services/memory_service.py.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from models.memory import MemoryScope
from registry.context import CallContext
from registry.decorator import capability
from services.memory.repository import MemoryRepository
from services.memory.service import MemoryService


class EntryResult(BaseModel):
    key: str
    value: str
    hit_count: int


def _entry_to_result(entry) -> EntryResult:
    return EntryResult(key=entry.key, value=entry.value, hit_count=entry.hit_count)


# --------------------------------------------------------------------------
# memory.server_fact.set / get / list
# --------------------------------------------------------------------------


class SetServerFactParams(BaseModel):
    fact_key: str
    value: str

    def audit_target(self) -> str:
        return self.fact_key


@capability(
    name="memory.server_fact.set",
    summary="Set a durable server fact (server IP, store URL, voting link, etc).",
    params_model=SetServerFactParams,
    result_model=EntryResult,
    required_permission="memory.manage",
    destructive=False,
    reversible=True,
)
async def set_server_fact(ctx: CallContext, params: SetServerFactParams) -> EntryResult:
    await MemoryService.set_server_fact(ctx.db, fact_key=params.fact_key, value=params.value)
    entry = await MemoryRepository.get(ctx.db, MemoryScope.SERVER, f"fact:{params.fact_key}")
    return _entry_to_result(entry)


class GetServerFactParams(BaseModel):
    fact_key: str


class GetServerFactResult(BaseModel):
    value: str | None


@capability(
    name="memory.server_fact.get",
    summary="Get a durable server fact by key.",
    params_model=GetServerFactParams,
    result_model=GetServerFactResult,
    required_permission="memory.manage",
    destructive=False,
    reversible=True,
    audited=False,
)
async def get_server_fact(ctx: CallContext, params: GetServerFactParams) -> GetServerFactResult:
    value = await MemoryService.get_server_fact(ctx.db, fact_key=params.fact_key)
    return GetServerFactResult(value=value)


class NoParams(BaseModel):
    pass


class ListServerFactsResult(BaseModel):
    facts: list[EntryResult]


@capability(
    name="memory.server_fact.list",
    summary="List all durable server facts.",
    params_model=NoParams,
    result_model=ListServerFactsResult,
    required_permission="memory.manage",
    destructive=False,
    reversible=True,
    audited=False,
)
async def list_server_facts(ctx: CallContext, params: NoParams) -> ListServerFactsResult:
    entries = await MemoryService.list_server_facts(ctx.db)
    return ListServerFactsResult(facts=[_entry_to_result(e) for e in entries])


# --------------------------------------------------------------------------
# memory.recurring.record / get / top
# --------------------------------------------------------------------------


class RecordRecurringParams(BaseModel):
    topic_key: str
    resolution: str

    def audit_target(self) -> str:
        return self.topic_key


@capability(
    name="memory.recurring.record",
    summary="Record a recurring issue/question and how it was resolved.",
    params_model=RecordRecurringParams,
    result_model=EntryResult,
    required_permission="memory.manage",
    destructive=False,
    reversible=True,
)
async def record_recurring(ctx: CallContext, params: RecordRecurringParams) -> EntryResult:
    await MemoryService.record_recurring(ctx.db, topic_key=params.topic_key, resolution=params.resolution)
    entry = await MemoryRepository.get(ctx.db, MemoryScope.OPERATIONAL, f"recurring:{params.topic_key}")
    return _entry_to_result(entry)


class TopRecurringParams(BaseModel):
    limit: int = Field(default=10, ge=1, le=50)


class TopRecurringResult(BaseModel):
    entries: list[EntryResult]


@capability(
    name="memory.recurring.top",
    summary="List the most commonly recurring issues/questions, most frequent first.",
    params_model=TopRecurringParams,
    result_model=TopRecurringResult,
    required_permission="memory.manage",
    destructive=False,
    reversible=True,
    audited=False,
)
async def top_recurring(ctx: CallContext, params: TopRecurringParams) -> TopRecurringResult:
    entries = await MemoryService.top_recurring(ctx.db, limit=params.limit)
    return TopRecurringResult(entries=[_entry_to_result(e) for e in entries])


# --------------------------------------------------------------------------
# memory.maintenance.purge_expired
#
# Closes a gap flagged during umbrella-discord's Phase 6 buildout:
# MemoryService.purge_expired() already existed on the service layer
# (sweeps short-term/SHORT_TERM entries past their expires_at - server and
# operational entries are never given an expiry, see MemoryService's own
# class docstring, so this can never touch durable facts or recurring-topic
# records) but was never wrapped as a capability, so nothing - not the
# REST adapter, not umbrella-discord's memory_cog.py - could reach it.
# Moo-assistant's `!ai-memory purge` called the equivalent service method
# directly, being a monolith; this is that same action's capability-system
# equivalent.
# --------------------------------------------------------------------------


class PurgeExpiredResult(BaseModel):
    purged_count: int


@capability(
    name="memory.maintenance.purge_expired",
    summary="Remove expired short-term memory entries. Never touches server facts or recurring topics, which are never given an expiry.",
    params_model=NoParams,
    result_model=PurgeExpiredResult,
    required_permission="memory.manage",
    destructive=True,
    reversible=False,
)
async def purge_expired(ctx: CallContext, params: NoParams) -> PurgeExpiredResult:
    count = await MemoryService.purge_expired(ctx.db)
    return PurgeExpiredResult(purged_count=count)
