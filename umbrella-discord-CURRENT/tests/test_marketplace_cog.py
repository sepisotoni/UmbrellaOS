"""
tests/test_marketplace_cog.py — Tests for MarketplaceCog._format_outcome,
the one pure function in this cog. See test_notifications_cog.py's module
docstring for why the cog itself can't be instantiated in a test without a
live bot event loop (its __init__ calls self.periodic_sync.start(), same
as notifications_cog.py's poll_escalations.start()) - only the static
method is exercised here. The actual sync-triggering behavior
(startup/periodic/on-demand) is discord.py task-loop machinery, not this
project's own logic to test - MarketplaceCommandSync.sync() itself is
covered by tests/test_marketplace_sync.py.
"""
from __future__ import annotations

from bot.cogs.marketplace_cog import MarketplaceCog
from bot.services.marketplace_sync import SyncOutcome


def test_format_outcome_no_changes():
    outcome = SyncOutcome(added=[], removed=[], warnings=[])
    assert MarketplaceCog._format_outcome(outcome) == "No changes — plugin commands already match umbrella-core."


def test_format_outcome_added_only():
    outcome = SyncOutcome(added=["status", "greet"], removed=[], warnings=[])
    message = MarketplaceCog._format_outcome(outcome)
    assert "Registered/updated: /status, /greet" in message
    assert "Removed" not in message


def test_format_outcome_removed_only():
    outcome = SyncOutcome(added=[], removed=["oldcmd"], warnings=[])
    message = MarketplaceCog._format_outcome(outcome)
    assert "Removed: /oldcmd" in message
    assert "Registered" not in message


def test_format_outcome_warnings_only():
    outcome = SyncOutcome(added=[], removed=[], warnings=["plugin 'foo' command 'bad' skipped: reason"])
    message = MarketplaceCog._format_outcome(outcome)
    assert "1 command(s) skipped" in message


def test_format_outcome_combines_all_three():
    outcome = SyncOutcome(added=["a"], removed=["b"], warnings=["w1", "w2"])
    message = MarketplaceCog._format_outcome(outcome)
    assert "Registered/updated: /a" in message
    assert "Removed: /b" in message
    assert "2 command(s) skipped" in message


def test_marketplace_cog_registers_plugin_sync_command():
    names = {cmd.name for cmd in MarketplaceCog.__cog_app_commands__}
    assert "plugin_sync" in names


def test_plugin_sync_command_defaults_to_administrator_only():
    """Discord-side stopgap, not real enforcement - see the cog's own
    module docstring and hosting_cog.py's test of the same pattern
    (test_destructive_commands_default_to_administrator_only)."""
    import discord

    by_name = {cmd.name: cmd for cmd in MarketplaceCog.__cog_app_commands__}
    assert by_name["plugin_sync"].default_permissions == discord.Permissions(administrator=True)
