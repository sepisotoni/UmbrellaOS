"""
tests/test_operational_intelligence_cog.py — Tests for the pure-function
pieces of OperationalIntelligenceCog (_format_error, _format_crash_risk,
_format_query_result, _format_postmortem). See test_investigation_cog.py's
module docstring for why the actual slash-command handlers aren't tested
here.
"""
import discord
import pytest

from bot.cogs.operational_intelligence_cog import OperationalIntelligenceCog
from bot.services.umbrella_core_client import UmbrellaCoreError


def test_format_error_permission_denied():
    exc = UmbrellaCoreError("Missing permission: operational_intelligence.view", status_code=403, code="PERMISSION_DENIED")
    message = OperationalIntelligenceCog._format_error(exc)
    assert "don't have permission" in message


def test_format_error_generic():
    exc = UmbrellaCoreError("Could not reach umbrella-core: connection refused")
    message = OperationalIntelligenceCog._format_error(exc)
    assert "Operational intelligence request failed" in message
    assert "connection refused" in message


def test_format_crash_risk_critical():
    result = {
        "server_id": "srv-1",
        "risk_level": "critical",
        "current_tps": 8.2,
        "trend_delta": -3.5,
        "samples_analyzed": 12,
        "reasoning": "TPS has dropped sharply over the last 10 minutes.",
    }
    embed = OperationalIntelligenceCog._format_crash_risk(result)
    assert isinstance(embed, discord.Embed)
    assert embed.color == discord.Color.red()
    field_values = {f.name: f.value for f in embed.fields}
    assert field_values["Risk level"] == "Critical"
    assert field_values["Current TPS"] == "8.20"
    assert field_values["Trend"] == "-3.50"
    assert "12 samples" in embed.footer.text


def test_format_crash_risk_insufficient_data_handles_missing_metrics():
    result = {"server_id": "srv-1", "risk_level": "insufficient_data", "current_tps": None, "trend_delta": None, "samples_analyzed": 1, "reasoning": "Not enough data."}
    embed = OperationalIntelligenceCog._format_crash_risk(result)
    field_values = {f.name: f.value for f in embed.fields}
    assert field_values["Current TPS"] == "—"
    assert field_values["Trend"] == "—"


def test_format_query_result_escalated():
    result = {"answer": "Lag was caused by a chunk-loading spike.", "confidence": 0.72, "escalated": True, "evidence": "..."}
    embed = OperationalIntelligenceCog._format_query_result("Why did it lag?", result)
    assert embed.description == "Why did it lag?"
    field_names = {f.name for f in embed.fields}
    assert "⚠️ Status" in field_names
    assert "72%" in embed.footer.text


def test_format_query_result_not_escalated():
    result = {"answer": "No anomalies found.", "confidence": 0.9, "escalated": False, "evidence": "..."}
    embed = OperationalIntelligenceCog._format_query_result("q", result)
    field_names = {f.name for f in embed.fields}
    assert "⚠️ Status" not in field_names


def test_format_postmortem_truncates_long_draft():
    long_draft = "x" * 1500
    result = {"server_id": "srv-1", "draft": long_draft, "confidence": 0.5, "escalated": False, "evidence": "...", "status": "pending_review"}
    embed = OperationalIntelligenceCog._format_postmortem(result)
    assert embed.description.endswith("…")
    assert len(embed.description) == 1001


def test_format_postmortem_shows_escalated_field():
    result = {"server_id": "srv-1", "draft": "short draft", "confidence": 0.4, "escalated": True, "evidence": "...", "status": "pending_review"}
    embed = OperationalIntelligenceCog._format_postmortem(result)
    field_names = {f.name for f in embed.fields}
    assert "⚠️ Escalated" in field_names
