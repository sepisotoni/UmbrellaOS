"""
tests/test_player_risk_cog.py — Tests for the pure-function pieces of
PlayerRiskCog (_format_error, _format_risk_score). See
test_investigation_cog.py's module docstring for why the actual
slash-command handler isn't tested here.
"""
import discord
import pytest

from bot.cogs.player_risk_cog import PlayerRiskCog
from bot.services.umbrella_core_client import UmbrellaCoreError


def test_format_error_permission_denied():
    exc = UmbrellaCoreError("Missing permission: player_risk.view", status_code=403, code="PERMISSION_DENIED")
    message = PlayerRiskCog._format_error(exc)
    assert "don't have permission" in message


def test_format_error_not_found():
    exc = UmbrellaCoreError("Player not found: abc", status_code=404, code="NOT_FOUND")
    message = PlayerRiskCog._format_error(exc)
    assert "No player found" in message


def test_format_error_generic():
    exc = UmbrellaCoreError("Could not reach umbrella-core: connection refused")
    message = PlayerRiskCog._format_error(exc)
    assert "Player risk lookup failed" in message
    assert "connection refused" in message


def test_format_risk_score_with_linked_discord():
    result = {
        "player_uuid": "1234-uuid",
        "discord_id": "999",
        "total_score": 47,
        "reasoning": "Confirmed alt group plus 2 moderation actions.",
        "breakdown": {
            "anticheat_points": 12,
            "confirmed_alt_group": True,
            "moderation_action_count": 2,
            "investigation_count": 1,
            "anticheat_component": 12,
            "alt_component": 30,
            "moderation_component": 10,
            "investigation_component": 2,
        },
    }
    embed = PlayerRiskCog._format_risk_score(result)
    assert isinstance(embed, discord.Embed)
    assert "47" in embed.title
    field_values = {f.name: f.value for f in embed.fields}
    assert field_values["Player UUID"] == "1234-uuid"
    assert field_values["Linked Discord account"] == "<@999>"
    assert "+30" in field_values["Breakdown"]


def test_player_risk_by_discord_command_is_registered():
    assert "player_risk_by_discord" in {cmd.name for cmd in PlayerRiskCog.__cog_app_commands__}


def test_format_risk_score_without_linked_discord():
    result = {
        "player_uuid": "1234-uuid",
        "discord_id": None,
        "total_score": 0,
        "reasoning": "No signals found.",
        "breakdown": {
            "anticheat_points": 0,
            "confirmed_alt_group": False,
            "moderation_action_count": 0,
            "investigation_count": 0,
            "anticheat_component": 0,
            "alt_component": 0,
            "moderation_component": 0,
            "investigation_component": 0,
        },
    }
    embed = PlayerRiskCog._format_risk_score(result)
    field_values = {f.name: f.value for f in embed.fields}
    assert field_values["Linked Discord account"] == "Not linked"
    assert "Confirmed alt group: 0" in field_values["Breakdown"]
