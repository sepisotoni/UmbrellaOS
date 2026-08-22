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
import discord
import pytest

from bot.cogs.notifications_cog import NotificationsCog


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
    escalation = {"id": "esc-2", "source": "some_new_domain", "summary": "x", "confidence": None, "resolved": False, "related_report_id": None}
    embed = NotificationsCog._format_escalation(escalation)
    assert "some_new_domain" in embed.title


def test_format_escalation_omits_optional_fields_when_absent():
    escalation = {"id": "esc-3", "source": "investigation", "summary": "y", "confidence": None, "resolved": False, "related_report_id": None}
    embed = NotificationsCog._format_escalation(escalation)
    field_names = {f.name for f in embed.fields}
    assert "AI confidence" not in field_names
    assert "Related report" not in field_names
