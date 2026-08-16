"""
tests/test_knowledge.py — Tests for services/knowledge/*.py.
"""
import pytest

from config import get_settings
from models.knowledge import KnowledgeReviewStatus
from services.knowledge.repository import KnowledgeRepository
from services.knowledge.service import KnowledgeService, channel_names_configured, is_knowledge_channel


@pytest.mark.asyncio
async def test_channel_names_configured_parses_comma_separated_list(monkeypatch):
    monkeypatch.setattr(get_settings(), "knowledge_channel_names", "ai-faq, ai-news ,AI-STORE")
    assert channel_names_configured() == {"ai-faq", "ai-news", "ai-store"}


@pytest.mark.asyncio
async def test_channel_names_configured_empty_by_default(monkeypatch):
    monkeypatch.setattr(get_settings(), "knowledge_channel_names", "")
    assert channel_names_configured() == set()
    assert is_knowledge_channel("ai-faq") is False


@pytest.mark.asyncio
async def test_index_entry_skips_unconfigured_channel(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "knowledge_channel_names", "ai-faq")
    async with db_session() as db:
        entry = await KnowledgeService.index_entry(
            db, channel_id="chan-1", channel_name="general", discord_message_id="msg-1",
            author_id="user-1", author_name="Alice", content="hello",
        )
        assert entry is None


@pytest.mark.asyncio
async def test_index_entry_indexes_configured_channel(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "knowledge_channel_names", "ai-faq")
    async with db_session() as db:
        entry = await KnowledgeService.index_entry(
            db, channel_id="chan-1", channel_name="ai-faq", discord_message_id="msg-2",
            author_id="user-1", author_name="Alice", content="The server IP is play.example.com",
        )
        assert entry is not None
        assert entry.review_status == KnowledgeReviewStatus.APPROVED


@pytest.mark.asyncio
async def test_index_entry_is_idempotent_on_same_message_id(db_session, monkeypatch):
    """The bug fix: reprocessing the same discord_message_id must update,
    not raise an IntegrityError on the unique constraint."""
    monkeypatch.setattr(get_settings(), "knowledge_channel_names", "ai-faq")
    async with db_session() as db:
        first = await KnowledgeService.index_entry(
            db, channel_id="chan-1", channel_name="ai-faq", discord_message_id="msg-3",
            author_id="user-1", author_name="Alice", content="original content",
        )
        await db.commit()

        # Reprocess the same message - must not raise.
        second = await KnowledgeService.index_entry(
            db, channel_id="chan-1", channel_name="ai-faq", discord_message_id="msg-3",
            author_id="user-1", author_name="Alice", content="original content",
        )
        assert second.id == first.id


@pytest.mark.asyncio
async def test_index_entry_snapshots_version_on_content_change(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "knowledge_channel_names", "ai-faq")
    async with db_session() as db:
        entry = await KnowledgeService.index_entry(
            db, channel_id="chan-1", channel_name="ai-faq", discord_message_id="msg-4",
            author_id="user-1", author_name="Alice", content="v1 content",
        )
        await db.commit()

        updated = await KnowledgeService.index_entry(
            db, channel_id="chan-1", channel_name="ai-faq", discord_message_id="msg-4",
            author_id="user-1", author_name="Alice", content="v2 content",
        )
        await db.commit()

        assert updated.content == "v2 content"
        history = await KnowledgeRepository.history(db, entry.id)
        assert len(history) == 1
        assert history[0].content == "v1 content"  # the PRE-edit content was archived


@pytest.mark.asyncio
async def test_search_only_returns_approved_non_superseded_entries(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "knowledge_channel_names", "ai-faq")
    async with db_session() as db:
        await KnowledgeService.index_entry(
            db, channel_id="chan-1", channel_name="ai-faq", discord_message_id="msg-5",
            author_id="user-1", author_name="Alice", content="the store link is example.com/store",
        )
        await db.commit()

        results = await KnowledgeService.search(db, "store")
        assert len(results) == 1


@pytest.mark.asyncio
async def test_propose_and_approve_correction_supersedes_original(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "knowledge_channel_names", "ai-faq")
    async with db_session() as db:
        original = await KnowledgeService.index_entry(
            db, channel_id="chan-1", channel_name="ai-faq", discord_message_id="msg-6",
            author_id="user-1", author_name="Alice", content="old IP: 1.2.3.4",
        )
        await db.commit()

        correction = await KnowledgeService.propose_correction(
            db, original_entry_id=original.id, channel_id="chan-1", channel_name="ai-faq",
            discord_message_id="msg-7", author_id="staff-1", author_name="Staff", content="new IP: 5.6.7.8",
        )
        await db.commit()
        assert correction.review_status == KnowledgeReviewStatus.PENDING

        # Not yet retrievable - only the original (still un-superseded) is.
        results_before = await KnowledgeService.search(db, "IP")
        assert {r.id for r in results_before} == {original.id}

        approved = await KnowledgeService.approve(db, correction.id, reviewed_by="admin-1")
        await db.commit()
        assert approved.review_status == KnowledgeReviewStatus.APPROVED

        results_after = await KnowledgeService.search(db, "IP")
        assert {r.id for r in results_after} == {correction.id}  # original is now superseded, excluded


@pytest.mark.asyncio
async def test_reject_correction_leaves_original_live(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "knowledge_channel_names", "ai-faq")
    async with db_session() as db:
        original = await KnowledgeService.index_entry(
            db, channel_id="chan-1", channel_name="ai-faq", discord_message_id="msg-8",
            author_id="user-1", author_name="Alice", content="store hours: 9-5",
        )
        await db.commit()

        correction = await KnowledgeService.propose_correction(
            db, original_entry_id=original.id, channel_id="chan-1", channel_name="ai-faq",
            discord_message_id="msg-9", author_id="staff-1", author_name="Staff", content="store hours: 24/7",
        )
        await db.commit()

        rejected = await KnowledgeService.reject(db, correction.id, reviewed_by="admin-1")
        await db.commit()
        assert rejected.review_status == KnowledgeReviewStatus.REJECTED

        results = await KnowledgeService.search(db, "hours")
        assert {r.id for r in results} == {original.id}


@pytest.mark.asyncio
async def test_list_pending_only_shows_pending(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "knowledge_channel_names", "ai-faq")
    async with db_session() as db:
        original = await KnowledgeService.index_entry(
            db, channel_id="chan-1", channel_name="ai-faq", discord_message_id="msg-10",
            author_id="user-1", author_name="Alice", content="entry A",
        )
        await db.commit()
        await KnowledgeService.propose_correction(
            db, original_entry_id=original.id, channel_id="chan-1", channel_name="ai-faq",
            discord_message_id="msg-11", author_id="staff-1", author_name="Staff", content="entry A corrected",
        )
        await db.commit()

        pending = await KnowledgeService.list_pending(db)
        assert len(pending) == 1
        assert pending[0].review_status == KnowledgeReviewStatus.PENDING
