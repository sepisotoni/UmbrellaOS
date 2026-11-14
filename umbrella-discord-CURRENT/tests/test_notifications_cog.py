"""
tests/test_notifications_cog.py — Tests for NotificationsCog._format_escalation,
the one pure function in this cog. See test_investigation_cog.py's module
docstring for the general rule on what is/isn't pure-function-testable;
NotificationsCog additionally can't be instantiated in a test at all
without a running bot event loop (its __init__ calls
self.poll_escalations.start(), which requires one - see the cog's own
module docstring for why that's the correct, standard discord.py
pattern), so only the static method is exercised here.
"""

import asyncio
from unittest.mock import MagicMock

import discord
import pytest

from bot.cogs.notifications_cog import NotificationsCog


@pytest.mark.asyncio
async def test_successful_push_is_durably_acknowledged_before_poll():
    escalation = {
        "id": "esc-push",
        "source": "moderation",
        "summary": "Review this report.",
        "confidence": 0.8,
    }

    class Core:
        notified = False

        async def invoke(self, name, params):
            if name == "moderation_intelligence.escalation.mark_notified":
                self.notified = True
                return {}
            if name == "moderation_intelligence.escalation.list":
                row = {**escalation, "notified_at": "now" if self.notified else None}
                return {"escalations": [row]}
            raise AssertionError(name)

    class Channel:
        def __init__(self):
            self.sent = []

        async def send(self, **kwargs):
            self.sent.append(kwargs)

    core = Core()
    channels = {321: Channel(), 654: Channel()}
    bot = type(
        "Bot",
        (),
        {
            "core": core,
            "guild_configs": {
                123: type("GuildConfig", (), {"staff_alert_channel_id": 321})(),
                456: type("GuildConfig", (), {"staff_alert_channel_id": 654})(),
            },
            "get_channel": lambda self, channel_id: channels.get(channel_id),
        },
    )()
    cog = NotificationsCog.__new__(NotificationsCog)
    cog.bot = bot
    cog._ack_tasks = set()

    await cog.handle_escalation_push(escalation)
    await asyncio.gather(*list(cog._ack_tasks))
    await cog.poll_escalations()

    assert core.notified
    assert [len(channel.sent) for channel in channels.values()] == [1, 1]


@pytest.mark.asyncio
async def test_partial_guild_delivery_is_not_acknowledged():
    class Core:
        notified = False

        async def invoke(self, name, params):
            if name == "moderation_intelligence.escalation.mark_notified":
                self.notified = True
                return {}
            raise AssertionError(name)

    class Channel:
        def __init__(self, fails=False):
            self.sent = []
            self.fails = fails

        async def send(self, **kwargs):
            if self.fails:
                raise discord.HTTPException(MagicMock(), "Discord unavailable")
            self.sent.append(kwargs)

    core = Core()
    channels = {321: Channel(), 654: Channel(fails=True)}
    bot = type(
        "Bot",
        (),
        {
            "core": core,
            "guild_configs": {
                123: type("GuildConfig", (), {"staff_alert_channel_id": 321})(),
                456: type("GuildConfig", (), {"staff_alert_channel_id": 654})(),
            },
            "get_channel": lambda self, channel_id: channels.get(channel_id),
        },
    )()
    cog = NotificationsCog.__new__(NotificationsCog)
    cog.bot = bot
    cog._ack_tasks = set()

    await cog.handle_escalation_push(
        {"id": "esc-partial", "source": "moderation", "summary": "Review this."}
    )

    assert not core.notified
    assert len(channels[321].sent) == 1


def test_format_escalation_known_source_label():
    escalation = {
        "id": "esc-1",
        "source": "moderation",
        "summary": "Repeated harassment reports against a player.",
        "confidence": 0.82,
        "resolved": False,
        "related_report_id": "rep-1",
        "notified_at": None,
    }
    embed = NotificationsCog._format_escalation(escalation)
    assert isinstance(embed, discord.Embed)
    assert "Moderation report" in embed.title
    assert embed.description == "Repeated harassment reports against a player."
    field_values = {f.name: f.value for f in embed.fields}
    assert field_values["AI confidence"] == "82%"
    assert field_values["Related report"] == "rep-1"
    assert "esc-1" in embed.footer.text


def test_format_escalation_unknown_source_falls_back_to_raw_value():
    escalation = {
        "id": "esc-2",
        "source": "some_new_domain",
        "summary": "x",
        "confidence": None,
        "resolved": False,
        "related_report_id": None,
    }
    embed = NotificationsCog._format_escalation(escalation)
    assert "some_new_domain" in embed.title


def test_format_escalation_omits_optional_fields_when_absent():
    escalation = {
        "id": "esc-3",
        "source": "investigation",
        "summary": "y",
        "confidence": None,
        "resolved": False,
        "related_report_id": None,
    }
    embed = NotificationsCog._format_escalation(escalation)
    field_names = {f.name for f in embed.fields}
    assert "AI confidence" not in field_names
    assert "Related report" not in field_names
