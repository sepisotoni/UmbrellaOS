"""
tests/test_bridge_cog.py — Tests for the pure-function piece of
BridgeCog (_format_broadcast). Deliberately does NOT test
handle_dashboard_message_push end-to-end — that needs a live
bot/channel (dpytest would be the normal tool for that; not available
in this sandbox). See test_investigation_cog.py's module docstring for
the general rule this project follows.
"""
import discord
import pytest

from bot.cogs.bridge_cog import BridgeCog


def test_format_broadcast_includes_message_and_sender():
    payload = {"message": "Server restarting in 5 minutes", "player_name": "AdminBob"}
    embed = BridgeCog._format_broadcast(payload)
    assert embed.description == "Server restarting in 5 minutes"
    assert "AdminBob" in embed.footer.text


def test_format_broadcast_falls_back_to_staff_when_no_sender():
    payload = {"message": "Test message"}
    embed = BridgeCog._format_broadcast(payload)
    assert "Staff" in embed.footer.text


def test_format_broadcast_handles_missing_message():
    payload = {"player_name": "AdminBob"}
    embed = BridgeCog._format_broadcast(payload)
    assert embed.description == ""
