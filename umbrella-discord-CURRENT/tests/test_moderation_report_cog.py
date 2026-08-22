"""
tests/test_moderation_report_cog.py — Tests for the pure-function pieces
of ModerationReportCog (_format_error, _format_result). Deliberately does
NOT test the actual slash-command handler (report()) or cog registration
end-to-end - see tests/test_investigation_cog.py's module docstring for
why (needs a live discord.Interaction/gateway connection dpytest would
normally provide, not available in this sandbox).
"""
from types import SimpleNamespace

import pytest

from bot.cogs.moderation_report_cog import ModerationReportCog
from bot.services.umbrella_core_client import UmbrellaCoreError


def _fake_member(mention: str = "<@123>") -> SimpleNamespace:
    """A stand-in for discord.Member with just the attribute _format_result
    reads. Using the real discord.Member requires gateway state (a guild,
    a shard) that's not worth constructing for a pure formatting test -
    mirrors how test_investigation_cog.py uses real discord.Embed (cheap
    to construct standalone) but wouldn't construct a real discord.Member
    (expensive, needs connection state) either."""
    return SimpleNamespace(mention=mention)


def test_format_error_permission_denied():
    exc = UmbrellaCoreError("Missing permission: moderation_intelligence.report.manage", status_code=403, code="PERMISSION_DENIED")
    message = ModerationReportCog._format_error(exc)
    assert "don't have permission" in message


def test_format_error_generic():
    exc = UmbrellaCoreError("Could not reach umbrella-core: connection refused")
    message = ModerationReportCog._format_error(exc)
    assert "Report failed" in message
    assert "connection refused" in message


def test_format_result_escalated():
    analysis = {
        "report_id": "r1",
        "analysis_id": "a1",
        "risk_score": 0.91,
        "confidence": 0.78,
        "recommended_action": "timeout",
        "escalated": True,
        "evidence_summary": "Repeated targeted harassment across 3 messages.",
    }
    message = ModerationReportCog._format_result(_fake_member(), analysis)
    assert "Escalated to staff" in message
    assert "0.91" in message
    assert "78%" in message


def test_format_result_not_escalated_shows_recommended_action():
    analysis = {
        "risk_score": 0.12,
        "confidence": 0.60,
        "recommended_action": "none",
        "escalated": False,
    }
    message = ModerationReportCog._format_result(_fake_member(), analysis)
    assert "Escalated" not in message
    assert "Recommended action" in message
    assert "none" in message


def test_format_result_includes_member_mention():
    analysis = {"risk_score": 0.5, "confidence": 0.5, "recommended_action": "warn", "escalated": False}
    message = ModerationReportCog._format_result(_fake_member("<@999>"), analysis)
    assert "<@999>" in message
