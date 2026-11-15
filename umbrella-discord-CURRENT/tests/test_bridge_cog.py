"""
tests/test_bridge_cog.py — Tests for the pure-function piece of
BridgeCog (_format_broadcast). Deliberately does NOT test
handle_dashboard_message_push end-to-end — that needs a live
bot/channel (dpytest would be the normal tool for that; not available
in this sandbox). See test_investigation_cog.py's module docstring for
the general rule this project follows.
"""

from types import SimpleNamespace

import discord
import pytest

from bot.cogs.bridge_cog import BridgeCog


@pytest.mark.asyncio
async def test_dashboard_broadcast_retries_transient_discord_send_failure(caplog):
    class Channel:
        calls = 0

        async def send(self, **kwargs):
            self.calls += 1
            if self.calls < 3:
                response = SimpleNamespace(status=500, reason="temporary")
                raise discord.HTTPException(response, "temporary")

    channel = Channel()
    cog = BridgeCog.__new__(BridgeCog)
    cog.bot = SimpleNamespace(get_channel=lambda channel_id: channel)

    delivered = await cog.handle_dashboard_message_push(
        {"message_id": "msg-1", "channel_id": "123", "message": "Hello"}
    )

    assert delivered is True
    assert channel.calls == 3
    assert "retrying" in caplog.text


@pytest.mark.asyncio
async def test_exhausted_dashboard_send_retries_are_logged(monkeypatch, caplog):
    monkeypatch.setattr("bot.cogs.bridge_cog._SEND_RETRY_DELAYS", (0, 0))

    class Channel:
        calls = 0

        async def send(self, **kwargs):
            self.calls += 1
            response = SimpleNamespace(status=500, reason="unavailable")
            raise discord.HTTPException(response, "unavailable")

    channel = Channel()
    cog = BridgeCog.__new__(BridgeCog)
    cog.bot = SimpleNamespace(get_channel=lambda channel_id: channel)

    delivered = await cog.handle_dashboard_message_push(
        {"message_id": "msg-failed", "channel_id": "123", "message": "Hello"}
    )

    assert delivered is False
    assert channel.calls == 3
    assert "after 3 attempts" in caplog.text


def test_format_broadcast_includes_message_and_sender():
    payload = {"message": "Server restarting in 5 minutes", "player_name": "AdminBob"}
    embed = BridgeCog._format_broadcast(payload)
    assert embed.description == "Server restarting in 5 minutes"
    assert "AdminBob" in embed.footer.text


def test_format_broadcast_applies_custom_embed_appearance():
    embed = BridgeCog._format_broadcast(
        {
            "message": "Service update",
            "embed_title": "Maintenance notice",
            "embed_color": 0x123456,
            "icon_url": "https://example.com/icon.png",
            "image_url": "https://example.com/banner.png",
        }
    )

    assert embed.title == "Maintenance notice"
    assert embed.color.value == 0x123456
    assert embed.thumbnail.url == "https://example.com/icon.png"
    assert embed.image.url == "https://example.com/banner.png"


def test_format_broadcast_ignores_invalid_custom_appearance_values():
    embed = BridgeCog._format_broadcast(
        {
            "embed_title": "",
            "embed_color": 0x1000000,
            "icon_url": "http://example.com/icon.png",
            "image_url": "javascript:alert(1)",
        }
    )

    assert embed.title == "📢 Staff Broadcast"
    assert embed.color.value == 0x9B59B6
    assert embed.thumbnail.url is None
    assert embed.image.url is None


def test_format_broadcast_falls_back_to_staff_when_no_sender():
    payload = {"message": "Test message"}
    embed = BridgeCog._format_broadcast(payload)
    assert "Staff" in embed.footer.text


def test_format_broadcast_handles_missing_message():
    payload = {"player_name": "AdminBob"}
    embed = BridgeCog._format_broadcast(payload)
    assert embed.description == ""
