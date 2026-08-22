"""
bot/services/marketplace_sync.py — turns umbrella-core's
`marketplace.install.discord_commands` discovery capability (Phase 7's
stated loose end - see PHASE7-COMPLETE-AND-PHASE8-HANDOFF.md, "The one
real loose end Phase 7 leaves behind") into real, invokable discord.py
slash commands.

Two capabilities on umbrella-core are combined here, deliberately:

1. `marketplace.install.discord_commands` (capabilities/marketplace.py) -
   gives plugin_id/name/description/capability_name per declared command,
   but NOT the param shape a Discord slash command needs to expose as
   options - see services/plugins/marketplace_service.py's
   DiscordCommandEntry, which only carries those four fields.
2. `GET /api/v1/capabilities` (registry/adapters/rest.py's
   `list_capabilities`) - the same generic introspection endpoint the CLI
   adapter and (Phase 5) the AI Tool Registry already use, which exposes
   every registered capability's `params_schema` (a plain pydantic
   `model_json_schema()` dict). A plugin's capabilities are registered
   under `plugin.<plugin_id>.<local_name>`
   (services/plugins/registration.py::register_plugin_capabilities) with a
   schema built from the manifest's `capabilities[].params` -
   `_build_pydantic_model`, restricted to string/integer/number/boolean
   fields (services/plugins/manifest.py's `_ALLOWED_FIELD_TYPES`) - so
   this module only ever needs to resolve that same tiny vocabulary.

`discord_commands()`'s `capability_name` is exactly what's returned by
`list_capabilities()`'s `name` field, so joining the two by that string is
the whole mechanism - no umbrella-core change was needed to make the param
shape discoverable, it already was, just not yet consumed.

This module is split into two halves on purpose:

- **Pure** (`build_desired_specs`, `_options_from_schema`,
  `_is_valid_discord_name`, `_is_valid_option_name`): takes plain dicts in,
  returns plain dataclasses out, touches neither discord.py's Command
  class nor the network. Fully unit-testable without a live bot.
- **Impure** (`MarketplaceCommandSync`): calls umbrella-core, builds real
  `discord.app_commands.Command` objects from the pure half's output,
  diffs them against what's currently registered, and pushes the result
  to Discord via `CommandTree.sync()`. See `bot/cogs/marketplace_cog.py`
  for *when* this runs (that cog owns the poll/on-demand triggers this
  module doesn't concern itself with).

Defensive validation, stated plainly: the plugin manifest schema
(services/plugins/manifest.py) does not constrain `discord_commands[].name`
or `capabilities[].params` keys to Discord-legal or Python-identifier-safe
strings at all - a manifest with a command named "hello world!" or a param
key "class" is structurally valid on the core side. Every such case is
skipped here (never crashes the sync) with a logged warning naming the
plugin - see `build_desired_specs`'s docstring for the full list of skip
conditions. This is the same "malformed input is an expected condition,
not a bug" stance services/plugins/manifest.py's own
`ManifestValidationError` docstring already takes for manifests generally.
"""
from __future__ import annotations

import keyword
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import discord
from discord import app_commands

from bot.services.umbrella_core_client import UmbrellaCoreError

logger = logging.getLogger(__name__)

# Mirrors services/plugins/manifest.py's _ALLOWED_FIELD_TYPES exactly -
# these are the only param types a plugin capability can ever declare, so
# there is deliberately no fallback/"unknown type" handling beyond this set.
_ALLOWED_SCHEMA_TYPES = {"string", "integer", "number", "boolean"}
_PY_TYPE_NAMES = {"string": "str", "integer": "int", "number": "float", "boolean": "bool"}

# Deliberately more conservative than Discord's actual allowed command-name
# character set (which permits many unicode ranges) - ASCII lowercase only,
# matching services/plugins/manifest.py's own _PLUGIN_ID_RE/_LOCAL_NAME_RE
# choice on the core side for the same "tiny, unambiguous vocabulary"
# reasoning stated in that module. Widening this later is a compatible,
# additive change if a real plugin needs it.
_COMMAND_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
# Stricter still: this string is also used as a real Python parameter
# identifier in the generated callback (see _build_dynamic_callback), so
# hyphens are excluded on top of the command-name rule above.
_OPTION_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")

_MAX_OPTIONS = 25  # Discord's hard limit per slash command.
_MAX_DESCRIPTION_LEN = 100  # Discord's hard limit for a command description.


class _UnsupportedParamError(ValueError):
    """Raised internally by `_options_from_schema` for a single param this
    module can't turn into a Discord option - caught by
    `build_desired_specs`, which skips just that one command."""


@dataclass(frozen=True)
class OptionSpec:
    name: str
    type: str  # one of _ALLOWED_SCHEMA_TYPES
    required: bool


@dataclass(frozen=True)
class PluginCommandSpec:
    """Everything needed to build (or recognize an unchanged) Discord slash
    command for one plugin-declared Discord command. Frozen + comparable by
    value on purpose: `MarketplaceCommandSync.sync()` diffs the previous
    sync's specs against the newly-fetched ones with plain `==`, so a
    plugin update that changes a description or param shape is detected as
    "this command changed, rebuild it" without any extra bookkeeping."""

    discord_name: str
    description: str
    capability_name: str
    plugin_id: str
    options: tuple[OptionSpec, ...] = field(default_factory=tuple)


@dataclass
class SyncOutcome:
    added: list[str]
    removed: list[str]
    warnings: list[str]


def _is_valid_discord_name(name: str) -> bool:
    return bool(_COMMAND_NAME_RE.match(name))


def _is_valid_option_name(name: str) -> bool:
    return bool(_OPTION_NAME_RE.match(name)) and not keyword.iskeyword(name) and name != "interaction"


def _resolve_option_type(prop_schema: dict) -> str | None:
    """A required field's schema has a direct `"type"`; an optional field
    (see registration.py's `_build_pydantic_model`, which types every
    non-required field as `py_type | None`) is emitted by pydantic as
    `"anyOf": [{"type": ...}, {"type": "null"}]` instead - both shapes are
    resolved to the same underlying type name here."""
    t = prop_schema.get("type")
    if t in _ALLOWED_SCHEMA_TYPES:
        return t
    for sub in prop_schema.get("anyOf", []):
        if sub.get("type") in _ALLOWED_SCHEMA_TYPES:
            return sub["type"]
    return None


def _options_from_schema(schema: dict) -> list[OptionSpec]:
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    options: list[OptionSpec] = []
    for prop_name, prop_schema in properties.items():
        if not _is_valid_option_name(prop_name):
            raise _UnsupportedParamError(
                f"parameter {prop_name!r} isn't a usable Discord option name/Python identifier."
            )
        option_type = _resolve_option_type(prop_schema)
        if option_type is None:
            raise _UnsupportedParamError(f"parameter {prop_name!r} has an unsupported/unresolvable type.")
        options.append(OptionSpec(name=prop_name, type=option_type, required=prop_name in required))
    return options


def build_desired_specs(
    discord_commands: list[dict], capabilities: list[dict], reserved_names: set[str]
) -> tuple[list[PluginCommandSpec], list[str]]:
    """Pure function: given the raw `marketplace.install.discord_commands`
    entries, the raw `GET /api/v1/capabilities` list, and the set of
    command names already in use that this sync doesn't own (built-in cog
    commands, or a plugin command from an earlier iteration of this same
    call - see the loop below), returns the specs that are safe to
    register as real Discord slash commands plus human-readable warnings
    for anything skipped.

    A command is skipped (with a warning, never an exception) when:
    - its declared name isn't a valid Discord command name
      (`_is_valid_discord_name`)
    - its name collides with `reserved_names` (a static cog command, or an
      earlier plugin command already claimed in this same batch - first
      declared wins, matching install order since
      MarketplaceService.list_installed orders by plugin_id)
    - its `capability_name` doesn't match any currently-registered
      capability (e.g. a stale manifest referencing a capability that
      failed to register, or a race with an in-progress uninstall)
    - any of its resolved params can't be represented as a Discord option
      (`_options_from_schema` raising `_UnsupportedParamError`)
    - it would need more than Discord's 25-option limit
    """
    cap_by_name = {c["name"]: c for c in capabilities}
    specs: list[PluginCommandSpec] = []
    used_names: set[str] = set(reserved_names)
    warnings: list[str] = []

    for entry in discord_commands:
        name = entry.get("name", "")
        plugin_id = entry.get("plugin_id", "?")
        capability_name = entry.get("capability_name", "")

        if not _is_valid_discord_name(name):
            warnings.append(f"plugin {plugin_id!r} command {name!r} skipped: not a valid Discord command name.")
            continue
        if name in used_names:
            warnings.append(
                f"plugin {plugin_id!r} command {name!r} skipped: name collides with an existing command."
            )
            continue

        cap = cap_by_name.get(capability_name)
        if cap is None:
            warnings.append(
                f"plugin {plugin_id!r} command {name!r} skipped: capability {capability_name!r} isn't registered."
            )
            continue

        try:
            options = _options_from_schema(cap.get("params_schema", {}))
        except _UnsupportedParamError as exc:
            warnings.append(f"plugin {plugin_id!r} command {name!r} skipped: {exc}")
            continue

        if len(options) > _MAX_OPTIONS:
            warnings.append(
                f"plugin {plugin_id!r} command {name!r} skipped: "
                f"{len(options)} options exceeds Discord's {_MAX_OPTIONS}-option limit."
            )
            continue

        description = entry.get("description") or "…"
        if len(description) > _MAX_DESCRIPTION_LEN:
            description = description[: _MAX_DESCRIPTION_LEN - 3] + "..."

        specs.append(
            PluginCommandSpec(
                discord_name=name,
                description=description,
                capability_name=capability_name,
                plugin_id=plugin_id,
                options=tuple(options),
            )
        )
        used_names.add(name)

    return specs, warnings


def _build_dynamic_callback(
    spec: PluginCommandSpec,
    run_capability: Callable[[PluginCommandSpec, discord.Interaction, dict[str, Any]], Awaitable[None]],
) -> Callable[..., Awaitable[None]]:
    """Builds a real, individually-signatured async function via `exec` so
    discord.py's `inspect.signature()`-based parameter extraction
    (`_extract_parameters_from_callback` in discord/app_commands/commands.py,
    checked against the installed discord.py 2.7.1 rather than assumed)
    sees genuine, per-parameter type annotations - there is no supported
    discord.py API for attaching options to a `Command` from data alone,
    only by inspecting a real callback signature.

    The generated body is intentionally trivial - it only collects its own
    named arguments into a dict and forwards to `run_capability`, which is
    the one shared, hand-written, tested implementation
    (`MarketplaceCommandSync._run_capability`). No business logic, error
    handling, or umbrella-core call ever lives inside generated code.

    Required options are ordered before optional ones (a stable sort,
    preserving each group's original declaration order) because Python
    function signatures require it - `def f(a, b=1, c)` is a SyntaxError.
    This doesn't change what Discord displays: discord.py's own extractor
    re-sorts the same way internally (`_extract_parameters_from_callback`'s
    `sorted(parameters, key=lambda a: a.required, reverse=True)`), so this
    is matching existing behavior, not introducing new ordering.
    """
    ordered_options = sorted(spec.options, key=lambda o: not o.required)

    arg_defs = []
    forward_pairs = []
    for opt in ordered_options:
        type_name = _PY_TYPE_NAMES[opt.type]
        if opt.required:
            arg_defs.append(f"{opt.name}: {type_name}")
        else:
            arg_defs.append(f"{opt.name}: {type_name} | None = None")
        forward_pairs.append(f"{opt.name!r}: {opt.name}")

    signature_src = ", ".join(["interaction", *arg_defs])
    kwargs_src = ", ".join(forward_pairs)
    source = (
        f"async def _plugin_command({signature_src}):\n"
        f"    await _run({{{kwargs_src}}}, interaction)\n"
    )

    async def _run(kwargs: dict[str, Any], interaction: discord.Interaction) -> None:
        await run_capability(spec, interaction, kwargs)

    namespace: dict[str, Any] = {"_run": _run}
    exec(compile(source, f"<umbrella-marketplace:{spec.discord_name}>", "exec"), namespace)  # noqa: S102
    return namespace["_plugin_command"]


class MarketplaceCommandSync:
    """Owns the live `discord.app_commands.Command` objects this bot has
    dynamically registered from installed umbrella-core plugins, and the
    fetch/diff/add/remove/re-sync cycle that keeps them matching what
    `marketplace.install.discord_commands` currently reports. See this
    module's docstring for the pure/impure split, and
    `bot/cogs/marketplace_cog.py` for what decides *when* `sync()` runs.
    """

    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self._active: dict[str, PluginCommandSpec] = {}

    async def sync(self) -> SyncOutcome:
        try:
            discord_commands = await self.bot.core.invoke("marketplace.install.discord_commands", {})
        except UmbrellaCoreError:
            logger.exception(
                "marketplace command sync: failed to fetch discord_commands from umbrella-core; "
                "leaving currently-registered plugin commands unchanged."
            )
            return SyncOutcome(added=[], removed=[], warnings=[])

        try:
            capabilities = await self.bot.core.list_capabilities()
        except UmbrellaCoreError:
            logger.exception(
                "marketplace command sync: failed to fetch capability schemas from umbrella-core; "
                "leaving currently-registered plugin commands unchanged."
            )
            return SyncOutcome(added=[], removed=[], warnings=[])

        reserved = {cmd.name for cmd in self.bot.tree.get_commands() if cmd.name not in self._active}
        desired_specs, warnings = build_desired_specs(discord_commands, capabilities, reserved)
        for warning in warnings:
            logger.warning("marketplace command sync: %s", warning)
        desired_by_name = {s.discord_name: s for s in desired_specs}

        removed: list[str] = []
        for name in list(self._active):
            if name not in desired_by_name:
                self.bot.tree.remove_command(name)
                del self._active[name]
                removed.append(name)

        added: list[str] = []
        for name, spec in desired_by_name.items():
            if self._active.get(name) == spec:
                continue  # Unchanged since last sync - nothing to do.
            if name in self._active:
                # Spec changed (plugin updated its command/params) - drop
                # the stale Command object before re-adding under the same
                # name; CommandTree.add_command refuses a duplicate name.
                self.bot.tree.remove_command(name)
            command = self._build_command(spec)
            self.bot.tree.add_command(command)
            self._active[name] = spec
            added.append(name)

        if added or removed:
            await self.bot.tree.sync()
            logger.info(
                "marketplace command sync: pushed to Discord (%d added/updated, %d removed).",
                len(added), len(removed),
            )

        return SyncOutcome(added=added, removed=removed, warnings=warnings)

    def _build_command(self, spec: PluginCommandSpec) -> app_commands.Command:
        callback = _build_dynamic_callback(spec, self._run_capability)
        # mypy can't verify a dynamically-exec'd function's signature
        # against app_commands.Command's expected callback protocol -
        # correctness here is covered by the real-signature assertions in
        # tests/test_marketplace_sync.py's
        # test_build_dynamic_callback_has_real_inspectable_signature and
        # the end-to-end sync() tests that add the resulting Command to a
        # real CommandTree and inspect its actual .parameters.
        return app_commands.Command(name=spec.discord_name, description=spec.description, callback=callback)  # type: ignore[arg-type]

    async def _run_capability(
        self, spec: PluginCommandSpec, interaction: discord.Interaction, kwargs: dict[str, Any]
    ) -> None:
        # discord_user_id is always sent here, same as every other cog's
        # invoke() calls (Phase 6's slash-command -> REST-permission
        # mapping) - a plugin capability's required_permission is checked
        # server-side exactly like a core capability's.
        await interaction.response.defer(thinking=True)
        try:
            result = await self.bot.core.invoke(
                spec.capability_name, kwargs, discord_user_id=str(interaction.user.id)
            )
        except UmbrellaCoreError as exc:
            await interaction.followup.send(self._format_error(exc))
            return
        await interaction.followup.send(embed=self._format_result(spec, result))

    @staticmethod
    def _format_error(exc: UmbrellaCoreError) -> str:
        """Separated from the callback body so it's testable without a
        live discord.Interaction - same reasoning as every other
        _format_error in this project."""
        if exc.status_code == 403:
            return "You don't have permission to run this command."
        return f"Command failed: {exc}"

    @staticmethod
    def _format_result(spec: PluginCommandSpec, result: Any) -> discord.Embed:
        """A plugin capability's result shape is arbitrary (whatever the
        plugin's manifest declares) - unlike every other cog's _format_*,
        this can't build a domain-specific embed. A generic key/value
        rendering for a dict result (the common case - every current core
        capability returns one) with a plain string fallback for anything
        else is honest about that rather than pretending to understand a
        shape it can't know ahead of time."""
        embed = discord.Embed(title=f"/{spec.discord_name}", color=discord.Color.blurple())
        embed.set_footer(text=f"Plugin: {spec.plugin_id}")
        if isinstance(result, dict) and result:
            for key, value in result.items():
                embed.add_field(name=str(key), value=str(value)[:1024], inline=False)
        elif isinstance(result, dict):
            embed.description = "Done."
        else:
            embed.description = str(result)[:4096]
        return embed
