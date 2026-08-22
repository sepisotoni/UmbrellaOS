"""
tests/test_archive_search_cog.py — Tests for the pure-function pieces of
ArchiveSearchCog (_format_error, _format_result). See
test_investigation_cog.py's module docstring for why the actual
slash-command handler isn't tested here.
"""
import discord
import pytest

from bot.cogs.archive_search_cog import ArchiveSearchCog
from bot.services.umbrella_core_client import UmbrellaCoreError


def test_format_error_permission_denied():
    exc = UmbrellaCoreError("Missing permission: archive.search", status_code=403, code="PERMISSION_DENIED")
    message = ArchiveSearchCog._format_error(exc)
    assert "don't have permission" in message


def test_format_error_generic():
    exc = UmbrellaCoreError("Could not reach umbrella-core: connection refused")
    message = ArchiveSearchCog._format_error(exc)
    assert "Archive search failed" in message
    assert "connection refused" in message


def test_format_result_includes_messages():
    result = {
        "messages": [
            {"message_id": 1, "source": "discord", "channel_id": "c1", "author_name": "Alice", "content": "server is laggy", "timestamp": "2026-08-04T12:00:00Z"},
            {"message_id": 2, "source": "minecraft", "channel_id": None, "author_name": "Bob", "content": "same here", "timestamp": "2026-08-04T12:01:00Z"},
        ]
    }
    embed = ArchiveSearchCog._format_result("laggy", result)
    assert isinstance(embed, discord.Embed)
    assert "laggy" in embed.description
    field_names = {f.name for f in embed.fields}
    assert "[discord] Alice" in field_names
    assert "[minecraft] Bob" in field_names


def test_format_result_handles_no_results():
    embed = ArchiveSearchCog._format_result("nonexistent", {"messages": []})
    assert embed.fields[0].name == "No results"


def test_format_result_caps_at_ten_and_shows_footer():
    messages = [
        {"message_id": i, "source": "discord", "channel_id": "c1", "author_name": f"user{i}", "content": "x", "timestamp": "t"}
        for i in range(15)
    ]
    embed = ArchiveSearchCog._format_result("x", {"messages": messages})
    assert len(embed.fields) == 10
    assert "10 of 15" in embed.footer.text


def test_format_result_handles_missing_author_name():
    result = {"messages": [{"message_id": 1, "source": "minecraft", "channel_id": None, "author_name": None, "content": "hi", "timestamp": "t"}]}
    embed = ArchiveSearchCog._format_result("hi", result)
    assert embed.fields[0].name == "[minecraft] unknown"
