"""
tests/test_memory_cog.py — Tests for the pure-function pieces of MemoryCog
(_format_error, _format_set_result, _format_list_result). See
test_investigation_cog.py's module docstring for why the actual
slash-command handlers aren't tested here.
"""
import discord
import pytest

from bot.cogs.memory_cog import MemoryCog
from bot.services.umbrella_core_client import UmbrellaCoreError


def test_format_error_permission_denied():
    exc = UmbrellaCoreError("Missing permission: memory.manage", status_code=403, code="PERMISSION_DENIED")
    message = MemoryCog._format_error(exc)
    assert "don't have permission" in message


def test_format_error_generic():
    exc = UmbrellaCoreError("Could not reach umbrella-core: connection refused")
    message = MemoryCog._format_error(exc)
    assert "Memory operation failed" in message
    assert "connection refused" in message


def test_format_set_result():
    entry = {"key": "server_ip", "value": "play.example.com", "hit_count": 0}
    message = MemoryCog._format_set_result(entry)
    assert "server_ip" in message
    assert "✅" in message


def test_format_list_result_includes_facts_and_recurring():
    facts = {"facts": [{"key": "server_ip", "value": "play.example.com", "hit_count": 0}]}
    recurring = {"entries": [{"key": "recurring:lag", "value": "restart the node", "hit_count": 7}]}
    embed = MemoryCog._format_list_result(facts, recurring)
    assert isinstance(embed, discord.Embed)
    field_names = {f.name for f in embed.fields}
    assert field_names == {"Server facts", "Top recurring topics"}
    facts_field = next(f for f in embed.fields if f.name == "Server facts")
    assert "server_ip" in facts_field.value
    recurring_field = next(f for f in embed.fields if f.name == "Top recurring topics")
    assert "seen 7×" in recurring_field.value


def test_format_list_result_handles_empty():
    embed = MemoryCog._format_list_result({"facts": []}, {"entries": []})
    for field in embed.fields:
        assert field.value == "(none)"


def test_memory_purge_command_is_registered():
    assert "memory_purge" in {cmd.name for cmd in MemoryCog.__cog_app_commands__}
