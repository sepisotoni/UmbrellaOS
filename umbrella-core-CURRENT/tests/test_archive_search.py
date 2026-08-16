"""
tests/test_archive_search.py — Tests for services/archive_search/service.py.
"""
from datetime import datetime, timezone

import pytest

from models.discord import ChatMessage
from services.archive_search.service import search


@pytest.mark.asyncio
async def test_search_finds_matching_message(db_session):
    async with db_session() as db:
        db.add(
            ChatMessage(
                source="discord", discord_channel_id="chan-1", player_name="Alice",
                message="the server restarts at midnight", timestamp=datetime.now(timezone.utc),
            )
        )
        await db.flush()

        results = await search(db, "restarts")
        assert len(results) == 1
        assert results[0].author_name == "Alice"
        assert results[0].source == "discord"


@pytest.mark.asyncio
async def test_search_respects_source_filter(db_session):
    async with db_session() as db:
        now = datetime.now(timezone.utc)
        db.add(ChatMessage(source="discord", player_name="Alice", message="hello world", timestamp=now))
        db.add(ChatMessage(source="minecraft", player_name="Bob", message="hello world", timestamp=now))
        await db.flush()

        discord_only = await search(db, "hello", source="discord")
        assert len(discord_only) == 1
        assert discord_only[0].source == "discord"

        both = await search(db, "hello")
        assert len(both) == 2


@pytest.mark.asyncio
async def test_search_orders_most_recent_first(db_session):
    async with db_session() as db:
        older = datetime(2026, 1, 1, tzinfo=timezone.utc)
        newer = datetime(2026, 6, 1, tzinfo=timezone.utc)
        db.add(ChatMessage(source="discord", player_name="Alice", message="unique-marker old", timestamp=older))
        db.add(ChatMessage(source="discord", player_name="Alice", message="unique-marker new", timestamp=newer))
        await db.flush()

        results = await search(db, "unique-marker")
        assert results[0].content == "unique-marker new"
        assert results[1].content == "unique-marker old"


@pytest.mark.asyncio
async def test_search_respects_limit(db_session):
    async with db_session() as db:
        for i in range(5):
            db.add(
                ChatMessage(
                    source="discord", player_name="Alice", message=f"limit-test message {i}",
                    timestamp=datetime.now(timezone.utc),
                )
            )
        await db.flush()

        results = await search(db, "limit-test", limit=2)
        assert len(results) == 2


@pytest.mark.asyncio
async def test_search_empty_query_matches_everything(db_session):
    async with db_session() as db:
        db.add(ChatMessage(source="discord", player_name="Alice", message="anything at all", timestamp=datetime.now(timezone.utc)))
        await db.flush()

        results = await search(db, "")
        assert len(results) == 1
