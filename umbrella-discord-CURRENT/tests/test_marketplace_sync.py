"""
tests/test_marketplace_sync.py — Tests for bot/services/marketplace_sync.py.

Split to match the module's own pure/impure split:
- Pure-function tests (schema resolution, name validation, spec-building,
  the exec-based callback builder) need no discord.py gateway/network at
  all.
- `MarketplaceCommandSync.sync()` tests use a real, unconnected
  `discord.ext.commands.Bot` (constructible without a token or network -
  confirmed against the installed discord.py 2.7.1) so the diff/add/
  remove logic is exercised against discord.py's actual `CommandTree`,
  not a hand-rolled fake of it. `bot.tree.sync()` (the one call that would
  hit the real Discord API) is monkeypatched to a no-op, same idea as
  `httpx.MockTransport` in test_umbrella_core_client.py - no real network
  needed to test the logic.
"""
from __future__ import annotations

import asyncio

import discord
import pytest
from discord.ext import commands

from bot.services.marketplace_sync import (
    MarketplaceCommandSync,
    OptionSpec,
    PluginCommandSpec,
    _build_dynamic_callback,
    _is_valid_discord_name,
    _is_valid_option_name,
    _options_from_schema,
    build_desired_specs,
)
from bot.services.umbrella_core_client import UmbrellaCoreError

# --------------------------------------------------------------------
# Name validation
# --------------------------------------------------------------------


@pytest.mark.parametrize("name", ["status", "server-status", "server_status", "a", "a" * 32])
def test_valid_discord_names_accepted(name):
    assert _is_valid_discord_name(name)


@pytest.mark.parametrize(
    "name", ["", "Status", "hello world", "server!", "_status", "1status", "a" * 33, "hello.world"]
)
def test_invalid_discord_names_rejected(name):
    assert not _is_valid_discord_name(name)


@pytest.mark.parametrize("name", ["server_id", "a", "loud", "x" * 32])
def test_valid_option_names_accepted(name):
    assert _is_valid_option_name(name)


@pytest.mark.parametrize(
    "name", ["", "Server_Id", "server-id", "server id", "class", "for", "interaction", "1server", "x" * 33]
)
def test_invalid_option_names_rejected(name):
    assert not _is_valid_option_name(name)


# --------------------------------------------------------------------
# Schema resolution
# --------------------------------------------------------------------


def test_options_from_schema_required_field():
    schema = {"properties": {"server_id": {"type": "string"}}, "required": ["server_id"]}
    options = _options_from_schema(schema)
    assert options == [OptionSpec(name="server_id", type="string", required=True)]


def test_options_from_schema_optional_field_uses_anyof_null_shape():
    # This is exactly what pydantic's create_model emits for a
    # `str | None = None` field (see registration.py's
    # _build_pydantic_model) - not a synthetic simplification.
    schema = {
        "properties": {"note": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None}},
        "required": [],
    }
    options = _options_from_schema(schema)
    assert options == [OptionSpec(name="note", type="string", required=False)]


def test_options_from_schema_empty_properties():
    assert _options_from_schema({}) == []


def test_options_from_schema_rejects_invalid_param_name():
    schema = {"properties": {"class": {"type": "string"}}, "required": ["class"]}
    with pytest.raises(ValueError, match="class"):
        _options_from_schema(schema)


def test_options_from_schema_rejects_unresolvable_type():
    schema = {"properties": {"payload": {"type": "object"}}, "required": ["payload"]}
    with pytest.raises(ValueError, match="payload"):
        _options_from_schema(schema)


def test_options_from_schema_multiple_types():
    schema = {
        "properties": {
            "a": {"type": "string"},
            "b": {"type": "integer"},
            "c": {"type": "number"},
            "d": {"type": "boolean"},
        },
        "required": ["a", "b"],
    }
    options = {o.name: o for o in _options_from_schema(schema)}
    assert options["a"] == OptionSpec("a", "string", True)
    assert options["b"] == OptionSpec("b", "integer", True)
    assert options["c"] == OptionSpec("c", "number", False)
    assert options["d"] == OptionSpec("d", "boolean", False)


# --------------------------------------------------------------------
# build_desired_specs
# --------------------------------------------------------------------


def _dc_entry(plugin_id="statusboard", name="status", description="Show status", capability_name="plugin.statusboard.status"):
    return {"plugin_id": plugin_id, "name": name, "description": description, "capability_name": capability_name}


def _cap(name="plugin.statusboard.status", params_schema=None):
    return {"name": name, "params_schema": params_schema or {"properties": {}, "required": []}}


def test_build_desired_specs_happy_path():
    specs, warnings = build_desired_specs([_dc_entry()], [_cap()], reserved_names=set())
    assert warnings == []
    assert len(specs) == 1
    assert specs[0].discord_name == "status"
    assert specs[0].capability_name == "plugin.statusboard.status"
    assert specs[0].plugin_id == "statusboard"


def test_build_desired_specs_skips_invalid_name():
    entry = _dc_entry(name="Not Valid!")
    specs, warnings = build_desired_specs([entry], [_cap()], reserved_names=set())
    assert specs == []
    assert len(warnings) == 1
    assert "not a valid Discord command name" in warnings[0]


def test_build_desired_specs_skips_reserved_name_collision():
    specs, warnings = build_desired_specs([_dc_entry()], [_cap()], reserved_names={"status"})
    assert specs == []
    assert "collides with an existing command" in warnings[0]


def test_build_desired_specs_skips_duplicate_across_plugins_first_wins():
    entries = [
        _dc_entry(plugin_id="plugin-a", name="status", capability_name="plugin.plugin_a.status"),
        _dc_entry(plugin_id="plugin-b", name="status", capability_name="plugin.plugin_b.status"),
    ]
    caps = [_cap(name="plugin.plugin_a.status"), _cap(name="plugin.plugin_b.status")]
    specs, warnings = build_desired_specs(entries, caps, reserved_names=set())
    assert len(specs) == 1
    assert specs[0].plugin_id == "plugin-a"
    assert len(warnings) == 1
    assert "plugin-b" in warnings[0]


def test_build_desired_specs_skips_missing_capability():
    specs, warnings = build_desired_specs([_dc_entry()], [], reserved_names=set())
    assert specs == []
    assert "isn't registered" in warnings[0]


def test_build_desired_specs_skips_unsupported_param():
    cap = _cap(params_schema={"properties": {"payload": {"type": "object"}}, "required": ["payload"]})
    specs, warnings = build_desired_specs([_dc_entry()], [cap], reserved_names=set())
    assert specs == []
    assert "payload" in warnings[0]


def test_build_desired_specs_skips_too_many_options():
    properties = {f"field_{i}": {"type": "string"} for i in range(26)}
    cap = _cap(params_schema={"properties": properties, "required": []})
    specs, warnings = build_desired_specs([_dc_entry()], [cap], reserved_names=set())
    assert specs == []
    assert "25-option limit" in warnings[0]


def test_build_desired_specs_truncates_long_description():
    entry = _dc_entry(description="x" * 150)
    specs, _ = build_desired_specs([entry], [_cap()], reserved_names=set())
    assert len(specs[0].description) == 100
    assert specs[0].description.endswith("...")


def test_build_desired_specs_defaults_empty_description():
    entry = _dc_entry(description="")
    specs, _ = build_desired_specs([entry], [_cap()], reserved_names=set())
    assert specs[0].description == "…"


def test_build_desired_specs_one_bad_command_does_not_block_others():
    entries = [_dc_entry(name="Bad Name!"), _dc_entry(plugin_id="ok-plugin", name="goodcmd", capability_name="plugin.ok_plugin.status")]
    caps = [_cap(), _cap(name="plugin.ok_plugin.status")]
    specs, warnings = build_desired_specs(entries, caps, reserved_names=set())
    assert len(specs) == 1
    assert specs[0].discord_name == "goodcmd"
    assert len(warnings) == 1


# --------------------------------------------------------------------
# Dynamic callback builder
# --------------------------------------------------------------------


def test_build_dynamic_callback_has_real_inspectable_signature():
    import inspect

    spec = PluginCommandSpec(
        discord_name="greet", description="d", capability_name="plugin.foo.greet", plugin_id="foo",
        options=(OptionSpec("name", "string", True), OptionSpec("loud", "boolean", False)),
    )

    async def fake_run(spec, interaction, kwargs):
        pass

    cb = _build_dynamic_callback(spec, fake_run)
    sig = inspect.signature(cb)
    params = list(sig.parameters.values())
    assert params[0].name == "interaction"
    assert params[1].name == "name"
    assert params[1].default is inspect.Parameter.empty
    assert params[2].name == "loud"
    assert params[2].default is None


def test_build_dynamic_callback_required_before_optional_regardless_of_declaration_order():
    """Guards against a plugin declaring an optional param before a
    required one in its manifest - that would be a SyntaxError in the
    generated function if not reordered (`def f(a, b=1, c)` is illegal)."""
    spec = PluginCommandSpec(
        discord_name="cmd", description="d", capability_name="plugin.foo.cmd", plugin_id="foo",
        options=(OptionSpec("optional_first", "string", False), OptionSpec("required_second", "string", True)),
    )

    async def fake_run(spec, interaction, kwargs):
        pass

    cb = _build_dynamic_callback(spec, fake_run)  # must not raise
    import inspect

    names = [p.name for p in inspect.signature(cb).parameters.values()]
    assert names.index("required_second") < names.index("optional_first")


def test_build_dynamic_callback_forwards_kwargs_to_run_capability():
    spec = PluginCommandSpec(
        discord_name="greet", description="d", capability_name="plugin.foo.greet", plugin_id="foo",
        options=(OptionSpec("name", "string", True),),
    )
    calls = []

    async def fake_run(spec, interaction, kwargs):
        calls.append((spec.discord_name, interaction, kwargs))

    cb = _build_dynamic_callback(spec, fake_run)
    asyncio.run(cb("FAKE_INTERACTION", name="bob"))
    assert calls == [("greet", "FAKE_INTERACTION", {"name": "bob"})]


def test_build_dynamic_callback_with_no_options():
    spec = PluginCommandSpec(
        discord_name="ping", description="d", capability_name="plugin.foo.ping", plugin_id="foo", options=()
    )
    calls = []

    async def fake_run(spec, interaction, kwargs):
        calls.append(kwargs)

    cb = _build_dynamic_callback(spec, fake_run)
    asyncio.run(cb("FAKE_INTERACTION"))
    assert calls == [{}]


# --------------------------------------------------------------------
# MarketplaceCommandSync._format_error / _format_result (pure)
# --------------------------------------------------------------------


def test_format_error_permission_denied():
    exc = UmbrellaCoreError("Missing permission: plugin.foo.greet", status_code=403, code="PERMISSION_DENIED")
    assert "don't have permission" in MarketplaceCommandSync._format_error(exc)


def test_format_error_generic():
    exc = UmbrellaCoreError("boom")
    message = MarketplaceCommandSync._format_error(exc)
    assert "Command failed" in message
    assert "boom" in message


def test_format_result_dict_renders_fields():
    spec = PluginCommandSpec("status", "d", "plugin.foo.status", "foo", ())
    embed = MarketplaceCommandSync._format_result(spec, {"tps": 19.8, "players": 4})
    field_values = {f.name: f.value for f in embed.fields}
    assert field_values["tps"] == "19.8"
    assert field_values["players"] == "4"
    assert "foo" in embed.footer.text


def test_format_result_empty_dict():
    spec = PluginCommandSpec("status", "d", "plugin.foo.status", "foo", ())
    embed = MarketplaceCommandSync._format_result(spec, {})
    assert embed.description == "Done."


def test_format_result_non_dict_falls_back_to_string():
    spec = PluginCommandSpec("status", "d", "plugin.foo.status", "foo", ())
    embed = MarketplaceCommandSync._format_result(spec, "all good")
    assert embed.description == "all good"


# --------------------------------------------------------------------
# MarketplaceCommandSync.sync() — integration against a real (unconnected)
# discord.ext.commands.Bot / CommandTree.
# --------------------------------------------------------------------


class _FakeCore:
    def __init__(self, discord_commands=None, capabilities=None):
        self.discord_commands = discord_commands or []
        self.capabilities = capabilities or []
        self.invoke_calls = []
        self.fail_discord_commands = False
        self.fail_list_capabilities = False

    async def invoke(self, name, params, discord_user_id=None):
        self.invoke_calls.append((name, params, discord_user_id))
        if name == "marketplace.install.discord_commands":
            if self.fail_discord_commands:
                raise UmbrellaCoreError("core unreachable")
            return self.discord_commands
        raise AssertionError(f"unexpected invoke: {name}")

    async def list_capabilities(self):
        if self.fail_list_capabilities:
            raise UmbrellaCoreError("core unreachable")
        return self.capabilities


def _make_bot() -> commands.Bot:
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())

    async def _no_network_sync(*args, **kwargs):
        return []

    bot.tree.sync = _no_network_sync  # avoid a real Discord API call in tests
    return bot


@pytest.mark.asyncio
async def test_sync_registers_new_plugin_command():
    bot = _make_bot()
    bot.core = _FakeCore(
        discord_commands=[_dc_entry()],
        capabilities=[_cap(params_schema={"properties": {"server_id": {"type": "string"}}, "required": ["server_id"]})],
    )
    sync = MarketplaceCommandSync(bot)

    outcome = await sync.sync()

    assert outcome.added == ["status"]
    assert outcome.removed == []
    command = bot.tree.get_command("status")
    assert command is not None
    assert [p.name for p in command.parameters] == ["server_id"]


@pytest.mark.asyncio
async def test_sync_is_idempotent_when_nothing_changed():
    bot = _make_bot()
    bot.core = _FakeCore(discord_commands=[_dc_entry()], capabilities=[_cap()])
    sync = MarketplaceCommandSync(bot)

    await sync.sync()
    second = await sync.sync()

    assert second.added == []
    assert second.removed == []


@pytest.mark.asyncio
async def test_sync_removes_command_for_uninstalled_plugin():
    bot = _make_bot()
    core = _FakeCore(discord_commands=[_dc_entry()], capabilities=[_cap()])
    bot.core = core
    sync = MarketplaceCommandSync(bot)
    await sync.sync()

    core.discord_commands = []
    outcome = await sync.sync()

    assert outcome.removed == ["status"]
    assert bot.tree.get_command("status") is None


@pytest.mark.asyncio
async def test_sync_rebuilds_command_when_spec_changes():
    bot = _make_bot()
    core = _FakeCore(discord_commands=[_dc_entry()], capabilities=[_cap()])
    bot.core = core
    sync = MarketplaceCommandSync(bot)
    await sync.sync()

    core.discord_commands = [_dc_entry(description="A brand new description")]
    outcome = await sync.sync()

    assert outcome.added == ["status"]
    assert outcome.removed == []
    assert bot.tree.get_command("status").description == "A brand new description"


@pytest.mark.asyncio
async def test_sync_does_not_touch_static_cog_commands():
    bot = _make_bot()

    async def _existing(interaction: discord.Interaction) -> None:
        pass

    from discord import app_commands

    static_command = app_commands.Command(name="investigate", description="static", callback=_existing)
    bot.tree.add_command(static_command)

    bot.core = _FakeCore(discord_commands=[], capabilities=[])
    sync = MarketplaceCommandSync(bot)
    await sync.sync()

    assert bot.tree.get_command("investigate") is not None


@pytest.mark.asyncio
async def test_sync_skips_plugin_command_colliding_with_static_command():
    bot = _make_bot()

    async def _existing(interaction: discord.Interaction) -> None:
        pass

    from discord import app_commands

    bot.tree.add_command(app_commands.Command(name="status", description="static", callback=_existing))

    bot.core = _FakeCore(discord_commands=[_dc_entry(name="status")], capabilities=[_cap()])
    sync = MarketplaceCommandSync(bot)
    outcome = await sync.sync()

    assert outcome.added == []
    assert len(outcome.warnings) == 1
    assert bot.tree.get_command("status").description == "static"


@pytest.mark.asyncio
async def test_sync_leaves_commands_unchanged_on_discord_commands_fetch_failure():
    bot = _make_bot()
    core = _FakeCore(discord_commands=[_dc_entry()], capabilities=[_cap()])
    bot.core = core
    sync = MarketplaceCommandSync(bot)
    await sync.sync()

    core.fail_discord_commands = True
    outcome = await sync.sync()

    assert outcome.added == []
    assert outcome.removed == []
    assert bot.tree.get_command("status") is not None  # untouched, not wiped


@pytest.mark.asyncio
async def test_sync_leaves_commands_unchanged_on_list_capabilities_fetch_failure():
    bot = _make_bot()
    core = _FakeCore(discord_commands=[_dc_entry()], capabilities=[_cap()])
    bot.core = core
    sync = MarketplaceCommandSync(bot)
    await sync.sync()

    core.fail_list_capabilities = True
    outcome = await sync.sync()

    assert outcome.added == []
    assert outcome.removed == []
    assert bot.tree.get_command("status") is not None


@pytest.mark.asyncio
async def test_run_capability_sends_discord_user_id():
    bot = _make_bot()
    core = _FakeCore()
    bot.core = core
    sync = MarketplaceCommandSync(bot)
    spec = PluginCommandSpec("status", "d", "plugin.foo.status", "foo", ())

    sent = []

    class _FakeResponse:
        async def defer(self, thinking=True):
            pass

    class _FakeFollowup:
        async def send(self, *args, **kwargs):
            sent.append((args, kwargs))

    class _FakeUser:
        id = 987654321

    class _FakeInteraction:
        response = _FakeResponse()
        followup = _FakeFollowup()
        user = _FakeUser()

    async def _invoke(name, params, discord_user_id=None):
        core.invoke_calls.append((name, params, discord_user_id))
        return {"ok": True}

    core.invoke = _invoke

    await sync._run_capability(spec, _FakeInteraction(), {"a": 1})

    assert core.invoke_calls == [("plugin.foo.status", {"a": 1}, "987654321")]
    assert len(sent) == 1
