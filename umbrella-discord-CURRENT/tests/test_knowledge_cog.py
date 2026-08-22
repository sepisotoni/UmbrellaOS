"""
tests/test_knowledge_cog.py — Tests for the pure-function pieces of
KnowledgeCog (_format_error, _format_result). See test_investigation_cog.py's
module docstring for why the actual slash-command handler isn't tested
here (needs a live discord.Interaction/gateway connection).
"""
import discord
import pytest

from bot.cogs.knowledge_cog import KnowledgeCog
from bot.services.umbrella_core_client import UmbrellaCoreError


def test_format_error_permission_denied():
    exc = UmbrellaCoreError("Missing permission: knowledge.entry.search", status_code=403, code="PERMISSION_DENIED")
    message = KnowledgeCog._format_error(exc)
    assert "don't have permission" in message


def test_format_error_generic():
    exc = UmbrellaCoreError("Could not reach umbrella-core: connection refused")
    message = KnowledgeCog._format_error(exc)
    assert "Knowledge search failed" in message
    assert "connection refused" in message


def test_format_result_includes_all_entries():
    result = {
        "entries": [
            {"id": "1", "channel_name": "ai-ip", "content": "The IP is play.example.com", "review_status": "approved", "confidence_score": 0.9},
            {"id": "2", "channel_name": "ai-rules", "content": "No griefing.", "review_status": "approved", "confidence_score": 0.95},
        ]
    }
    embed = KnowledgeCog._format_result("server ip", result)
    assert isinstance(embed, discord.Embed)
    assert "server ip" in embed.description
    field_names = {f.name for f in embed.fields}
    assert field_names == {"#ai-ip", "#ai-rules"}


def test_format_result_handles_no_entries():
    embed = KnowledgeCog._format_result("nonexistent thing", {"entries": []})
    assert len(embed.fields) == 1
    assert embed.fields[0].name == "No results"


def test_format_result_truncates_long_content():
    long_content = "x" * 600
    result = {"entries": [{"id": "1", "channel_name": "ai-ip", "content": long_content, "review_status": "approved", "confidence_score": 0.9}]}
    embed = KnowledgeCog._format_result("q", result)
    assert embed.fields[0].value.endswith("…")
    assert len(embed.fields[0].value) == 501
