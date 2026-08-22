"""
tests/test_investigation_cog.py — Tests for the pure-function pieces of
InvestigationCog (_format_error, _format_result). Deliberately does NOT
test the actual slash-command handler (investigate()) or cog registration
end-to-end - that needs a live discord.Interaction/gateway connection
(dpytest would be the normal tool for that; not available in this
sandbox). Extracting the formatting logic into static methods is what
makes this much tested without one.
"""
import discord
import pytest

from bot.cogs.investigation_cog import InvestigationCog
from bot.services.umbrella_core_client import UmbrellaCoreError


def test_format_error_permission_denied():
    exc = UmbrellaCoreError("Missing permission: investigation.run", status_code=403, code="PERMISSION_DENIED")
    message = InvestigationCog._format_error(exc)
    assert "don't have permission" in message


def test_format_error_generic():
    exc = UmbrellaCoreError("Could not reach umbrella-core: connection refused")
    message = InvestigationCog._format_error(exc)
    assert "Investigation failed" in message
    assert "connection refused" in message


def test_format_result_includes_all_findings():
    result = {
        "confidence": 0.85,
        "findings": [
            {"tool_key": "known_issues", "finding_text": "No open issues."},
            {"tool_key": "whitelist_status", "finding_text": "Approved."},
        ],
    }
    embed = InvestigationCog._format_result("why can't they join", result)
    assert isinstance(embed, discord.Embed)
    assert embed.description == "why can't they join"
    field_names = {f.name for f in embed.fields}
    assert field_names == {"known_issues", "whitelist_status"}
    assert "85%" in embed.footer.text


def test_format_result_handles_no_findings():
    embed = InvestigationCog._format_result("test", {"confidence": 0.0, "findings": []})
    assert len(embed.fields) == 0
