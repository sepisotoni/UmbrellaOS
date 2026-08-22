"""
tests/test_hosting_cog.py — Tests for the pure-function pieces of
HostingCog (_format_error, _format_server_list, _format_server_status,
_format_server_stats), plus the parts of _ConfirmDestructiveView that
don't require a live gateway (interaction_check's authorization logic,
which is a plain attribute comparison). See test_investigation_cog.py's
module docstring for why the actual slash-command handlers - and the
button callbacks themselves, which call real discord.py response methods
- aren't tested here.
"""
from types import SimpleNamespace

import discord
import pytest

from bot.cogs.hosting_cog import HostingCog, _ConfirmDestructiveView
from bot.services.umbrella_core_client import UmbrellaCoreError


async def _noop_coro():
    return None


def test_format_error_permission_denied():
    exc = UmbrellaCoreError("Missing permission: hosting.server.view", status_code=403, code="PERMISSION_DENIED")
    message = HostingCog._format_error(exc)
    assert "don't have permission" in message


def test_format_error_not_found():
    exc = UmbrellaCoreError("Server not found: abc", status_code=404, code="NOT_FOUND")
    message = HostingCog._format_error(exc)
    assert "No server found" in message


def test_format_error_generic():
    exc = UmbrellaCoreError("Could not reach umbrella-core: connection refused")
    message = HostingCog._format_error(exc)
    assert "Hosting request failed" in message
    assert "connection refused" in message


def test_format_server_list_with_servers():
    servers = [
        {"id": "s1", "name": "Survival", "node_id": "n1", "template_id": "t1", "template_version": 1, "status": "running", "memory_bytes": 0, "cpu_cores": 1.0},
        {"id": "s2", "name": "Creative", "node_id": "n1", "template_id": "t1", "template_version": 1, "status": "stopped", "memory_bytes": 0, "cpu_cores": 1.0},
    ]
    embed = HostingCog._format_server_list(servers)
    assert isinstance(embed, discord.Embed)
    assert "Survival" in embed.description
    assert "Creative" in embed.description
    assert "running" in embed.description


def test_format_server_list_empty():
    embed = HostingCog._format_server_list([])
    assert embed.fields[0].name == "No servers"


def test_format_server_status():
    server = {"id": "s1", "name": "Survival", "node_id": "n1", "template_id": "t1", "template_version": 1, "status": "running", "memory_bytes": 2147483648, "cpu_cores": 2.0}
    embed = HostingCog._format_server_status(server)
    assert embed.title == "Survival"
    assert embed.color == discord.Color.green()
    field_values = {f.name: f.value for f in embed.fields}
    assert field_values["Status"] == "running"
    assert field_values["Memory"] == "2048 MB"
    assert "s1" in embed.footer.text


def test_format_server_status_unknown_status_uses_default_color():
    server = {"id": "s1", "name": "Weird", "status": "provisioning", "node_id": "n1", "memory_bytes": 0, "cpu_cores": 1.0}
    embed = HostingCog._format_server_status(server)
    assert embed.color == discord.Color.light_grey()


def test_format_server_stats():
    stats = {
        "timestamp": "2026-08-04T12:00:00Z",
        "cpu_percent": 42.5,
        "memory_used_bytes": 1073741824,
        "memory_limit_bytes": 2147483648,
        "network_rx_bytes": 1048576,
        "network_tx_bytes": 2097152,
    }
    embed = HostingCog._format_server_stats("s1", stats)
    field_values = {f.name: f.value for f in embed.fields}
    assert field_values["CPU"] == "42.5%"
    assert field_values["Memory"] == "1024 / 2048 MB"
    assert "2026-08-04T12:00:00Z" in embed.footer.text


def test_destructive_commands_are_registered():
    names = {cmd.name for cmd in HostingCog.__cog_app_commands__}
    assert {"server_restart", "server_kill", "server_delete"} <= names


def test_destructive_commands_default_to_administrator_only():
    """Discord-side stopgap floor - see hosting_cog.py's module docstring.
    default_permissions() is a hint guild admins can override, not a hard
    enforcement (confirmed against discord/app_commands/commands.py's own
    docstring), so this only checks the intended default is set correctly,
    not that it's unbypassable."""
    admin_only = discord.Permissions(administrator=True)
    by_name = {cmd.name: cmd for cmd in HostingCog.__cog_app_commands__}
    for name in ("server_restart", "server_kill", "server_delete"):
        assert by_name[name].default_permissions == admin_only


def test_confirm_view_starts_unconfirmed():
    view = _ConfirmDestructiveView(author_id=123)
    assert view.confirmed is None
    assert view.message is None


@pytest.mark.asyncio
async def test_confirm_view_interaction_check_allows_original_author():
    view = _ConfirmDestructiveView(author_id=123)
    fake_interaction = SimpleNamespace(user=SimpleNamespace(id=123))
    assert await view.interaction_check(fake_interaction) is True


@pytest.mark.asyncio
async def test_confirm_view_interaction_check_denies_other_users():
    view = _ConfirmDestructiveView(author_id=123)
    sent = []
    fake_interaction = SimpleNamespace(
        user=SimpleNamespace(id=456),
        response=SimpleNamespace(send_message=lambda *a, **k: sent.append((a, k)) or _noop_coro()),
    )
    result = await view.interaction_check(fake_interaction)
    assert result is False
    assert len(sent) == 1
