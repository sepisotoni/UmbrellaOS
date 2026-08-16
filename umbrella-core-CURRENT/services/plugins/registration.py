"""
services/plugins/registration.py — turns a validated PluginManifest into
real entries in the process-wide CapabilityRegistry.

See docs/design/plugin-sdk-manifest-and-registration.md ("Tool-registration
contract") for the full rationale. Short version: this mirrors
capabilities/investigation.py's `_make_tool_capability` boilerplate
generator, generalized to data-driven manifests instead of a fixed list of
Python classes, and to a sandboxed executor instead of a direct in-process
call.
"""
from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ValidationError, create_model
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.permissions import Permission
from registry.context import CallContext
from registry.registry import CapabilityRegistry
from registry.registry import registry as default_registry
from registry.spec import CapabilitySpec
from services.plugin_kv.service import PluginKvService
from services.plugins.manifest import ConfigFieldDecl, ParamField, PluginCapability, PluginManifest

_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}


class PluginRegistrationError(ValueError):
    """Raised when a structurally-valid manifest still can't be safely
    registered — e.g. it asks for a permission key that doesn't exist.
    Deliberately distinct from ManifestValidationError: that one is about
    the manifest's own shape, this one is about whether the *system*
    (the live permission table) can support what it's asking for."""


class SandboxExecutor(Protocol):
    """What `register_plugin_capabilities` needs from a sandbox
    implementation. Kept as a Protocol (structural typing) rather than a
    concrete base class so the real subprocess-based sandbox
    (services/plugins/sandbox.py) and a fake/no-op sandbox used in tests
    for this module are equally valid without any inheritance
    relationship — this module should not need to change if the sandbox's
    internals change, only if this exact call shape does."""

    async def run(
        self,
        *,
        plugin_id: str,
        entrypoint: str,
        params: dict[str, Any],
        actor_id: str,
    ) -> dict[str, Any]:
        """Execute `entrypoint` inside `plugin_id`'s sandbox with `params`,
        returning a plain dict result. Must raise on failure (timeout,
        resource limit, uncaught exception in the plugin) rather than
        returning an error payload — CapabilityRegistry.call() already
        knows how to turn a handler exception into a failed, audited call;
        a second in-band error convention would just be a second thing to
        keep in sync with it.

        Phase 8 completion, Task A: implementations now also persist a
        PluginExecutionRecord (timing/resource-usage telemetry) after
        execution — see services/plugins/sandbox.py::ProcessSandbox.run's
        docstring for why that happens via its own independent DB session
        rather than a `db` parameter on this Protocol method. This method's
        signature is unchanged specifically so that stays true: nothing
        crosses into a SandboxExecutor beyond plugin_id/entrypoint/params/
        actor_id — see "What crosses the sandbox boundary, and what
        deliberately doesn't" in docs/design/plugin-sdk-manifest-and-
        registration.md."""
        ...


def _build_pydantic_model(model_name: str, fields: dict[str, ParamField]) -> type[BaseModel]:
    field_defs: dict[str, Any] = {}
    for field_name, spec in fields.items():
        py_type = _TYPE_MAP[spec.type]
        default = ... if spec.required else None
        field_defs[field_name] = (py_type if spec.required else py_type | None, default)
    return create_model(model_name, **field_defs)  # type: ignore[call-overload]


async def _known_permission_keys(db: AsyncSession) -> set[str]:
    result = await db.execute(select(Permission.permission_key))
    return set(result.scalars().all())


def _make_plugin_capability_handler(
    manifest: PluginManifest,
    cap: PluginCapability,
    sandbox: SandboxExecutor,
    result_model: type[BaseModel],
):
    """Generates the CapabilitySpec.handler wrapper for one declared
    plugin capability. This is the one piece of new glue code the design
    doc calls out: it adapts CapabilityRegistry.call()'s normal
    (ctx, params) -> result shape onto a sandboxed, out-of-process call,
    while deliberately not forwarding ctx.db or ctx.permissions across
    that boundary (see the design doc's "what crosses the sandbox
    boundary" section)."""

    async def handler(ctx: CallContext, params: BaseModel) -> BaseModel:
        raw_result = await sandbox.run(
            plugin_id=manifest.plugin_id,
            entrypoint=cap.entrypoint,
            params=params.model_dump(),
            actor_id=ctx.actor_id,
        )
        try:
            return result_model.model_validate(raw_result)
        except ValidationError as exc:
            # Deliberate choice (documented in the design doc): a plugin
            # returning a malformed result is treated as an ordinary
            # capability-call failure, not a distinct plugin error type,
            # so it flows through CapabilityRegistry.call()'s existing
            # failed-outcome audit path unchanged.
            raise ValueError(
                f"Plugin '{manifest.plugin_id}' capability '{cap.local_name}' "
                f"returned a result that doesn't match its declared schema: {exc}"
            ) from exc

    return handler


async def register_plugin_capabilities(
    manifest: PluginManifest,
    sandbox: SandboxExecutor,
    db: AsyncSession,
    registry: CapabilityRegistry = default_registry,
) -> list[str]:
    """Registers every capability declared in `manifest` into `registry`.

    Returns the fully-qualified names registered, in manifest order. Raises
    PluginRegistrationError (and registers nothing) if any capability's
    `required_permission` doesn't reference a real permission key — this
    check runs for *all* capabilities before *any* of them are registered,
    so a manifest either registers completely or not at all; a partial
    registration would leave some of a plugin's declared surface callable
    and some silently missing, which is a confusing state for an admin
    debugging an install.
    """
    known_permissions = await _known_permission_keys(db)

    for cap in manifest.capabilities:
        if cap.required_permission is not None and cap.required_permission not in known_permissions:
            raise PluginRegistrationError(
                f"Plugin '{manifest.plugin_id}' capability '{cap.local_name}' declares "
                f"required_permission={cap.required_permission!r}, which is not a known "
                "permission key. Plugins cannot mint new permission keys — see "
                "docs/design/plugin-sdk-manifest-and-registration.md."
            )

    registered: list[str] = []
    for cap in manifest.capabilities:
        full_name = f"plugin.{manifest.plugin_id}.{cap.local_name}"
        params_model = _build_pydantic_model(f"{full_name}.Params", cap.params)
        result_model = _build_pydantic_model(f"{full_name}.Result", cap.result)
        handler = _make_plugin_capability_handler(manifest, cap, sandbox, result_model)

        spec = CapabilitySpec(
            name=full_name,
            summary=cap.summary,
            params_model=params_model,
            result_model=result_model,
            handler=handler,
            required_permission=cap.required_permission,
            destructive=cap.destructive,
            reversible=cap.reversible,
            audited=cap.audited,
            audit_category="plugin",
        )
        registry.register(spec)
        registered.append(full_name)

    return registered


async def _get_or_create_permission(db: AsyncSession, *, key: str, description: str) -> Permission:
    """Idempotent get-or-create, same pattern as
    services/roles_service.py::RolesService.seed_defaults — the only other
    place in this codebase that mints Permission rows dynamically rather
    than assuming they already exist. Reinstalling the same plugin (or
    installing a second plugin that happens to declare the same key,
    though plugin_id-namespacing makes that impossible in practice) must
    not create a duplicate row or error — same idempotency requirement
    seed_defaults already has."""
    perm = await db.scalar(select(Permission).where(Permission.permission_key == key))
    if perm is None:
        perm = Permission(permission_key=key, description=description)
        db.add(perm)
        await db.flush()
    return perm


def _make_config_set_handler(manifest: PluginManifest, fields_by_key: dict[str, ConfigFieldDecl]):
    """Phase 10, Tier 2, Decision 2 Option A: the write path is entirely
    platform-owned code, not a sandboxed plugin call — unlike
    _make_plugin_capability_handler above, there is no sandbox.run() here
    at all. This is the concrete difference Decision 2's writeup meant by
    "the write path is platform-owned, not plugin-owned": a plugin cannot
    write an arbitrary key or an arbitrary value shape into its own kv
    storage through this capability, only one of the keys it declared in
    config_fields, type-checked against what it declared."""

    async def handler(ctx: CallContext, params: BaseModel) -> BaseModel:
        key = params.key  # type: ignore[attr-defined]
        value = params.value  # type: ignore[attr-defined]
        field = fields_by_key.get(key)
        if field is None:
            raise ValueError(
                f"'{key}' is not a config field declared by plugin "
                f"'{manifest.plugin_id}'. Known keys: {sorted(fields_by_key)}."
            )
        # Tier 2's starting scope is boolean-only (_ALLOWED_CONFIG_FIELD_TYPES);
        # the params_model itself is already typed `bool` for this field
        # (see _build_config_params_model below), so an isinstance check
        # here is a defense-in-depth belt-and-suspenders, not the primary
        # enforcement — pydantic's own validation is.
        if field.type == "boolean" and not isinstance(value, bool):
            raise ValueError(f"config field '{key}' expects a boolean value.")
        await PluginKvService.set(ctx.db, plugin_id=manifest.plugin_id, key=key, value=value)
        return ConfigSetResult(key=key, value=value)

    return handler


def _make_config_get_handler(manifest: PluginManifest, fields_by_key: dict[str, ConfigFieldDecl]):
    async def handler(ctx: CallContext, params: BaseModel) -> BaseModel:
        entries = await PluginKvService.get_all(ctx.db, plugin_id=manifest.plugin_id)
        stored = {e.key: PluginKvService.parse_value(e) for e in entries}
        values = []
        for key, field in fields_by_key.items():
            # A field declared in the manifest but never written yet
            # (fresh install, nobody's touched the toggle) falls back to
            # its declared default_value rather than a missing/null
            # entry — the dashboard's Settings page should never render
            # an "unset" state for a boolean toggle, only its current
            # effective value.
            current = stored.get(key, field.default_value)
            values.append(
                ConfigFieldValue(key=key, label=field.label, type=field.type, value=current)
            )
        return ConfigGetResult(values=values)

    return handler


class ConfigSetParams(BaseModel):
    key: str
    value: bool


class ConfigSetResult(BaseModel):
    key: str
    value: bool


class ConfigFieldValue(BaseModel):
    key: str
    label: str
    type: str
    value: bool


class ConfigGetParams(BaseModel):
    pass


class ConfigGetResult(BaseModel):
    values: list[ConfigFieldValue]


async def register_plugin_config_capabilities(
    manifest: PluginManifest,
    db: AsyncSession,
    registry: CapabilityRegistry = default_registry,
) -> list[str]:
    """Phase 10, Tier 2 (Decision 2 — DECIDED: Option A). Registers
    `plugin.<plugin_id>.config.get` and `.config.set` for a manifest that
    declares `config_fields`. No-op (returns []) for a manifest with no
    config_fields — most plugins have none, same "strictly opt-in" stance
    as `page` (Tier 3) and `dashboard_ui_slots`.

    Deliberately separate from register_plugin_capabilities rather than
    folded into it: that function's capabilities are all sandbox-executed
    (_make_plugin_capability_handler), a fundamentally different handler
    shape than these two, which never touch the sandbox at all — see
    _make_config_set_handler's docstring for why that boundary is the
    whole point of Option A. Called from MarketplaceService.install()
    right after register_plugin_capabilities, into the same
    dry_run_registry, so both fail (or both succeed) together — a plugin
    installing with a manifest error in *either* half shouldn't end up
    half-registered.
    """
    if not manifest.config_fields:
        return []

    fields_by_key = {f.key: f for f in manifest.config_fields}
    write_key = f"plugin.{manifest.plugin_id}.config.write"
    await _get_or_create_permission(
        db, key=write_key,
        description=f"Write {manifest.plugin_id}'s dashboard-configurable settings",
    )

    set_spec = CapabilitySpec(
        name=f"plugin.{manifest.plugin_id}.config.set",
        summary=f"Set a dashboard-configurable setting for '{manifest.plugin_id}'.",
        params_model=ConfigSetParams,
        result_model=ConfigSetResult,
        handler=_make_config_set_handler(manifest, fields_by_key),
        required_permission=write_key,
        destructive=False,
        reversible=True,
        audited=True,
        audit_category="plugin",
    )
    get_spec = CapabilitySpec(
        name=f"plugin.{manifest.plugin_id}.config.get",
        summary=f"Read '{manifest.plugin_id}'s current dashboard-configurable settings.",
        params_model=ConfigGetParams,
        result_model=ConfigGetResult,
        handler=_make_config_get_handler(manifest, fields_by_key),
        # Softer than the write side, deliberately: anyone who can already
        # see this plugin is installed (marketplace.install.view, the same
        # permission marketplace.install.pages/.dashboard_slots use) can
        # see its current config values — only *changing* them needs the
        # narrower per-plugin write grant. Matches the read/write asymmetry
        # every other discovery capability in this file already has.
        required_permission="marketplace.install.view",
        destructive=False,
        reversible=True,
        audited=False,
        audit_category="plugin",
    )
    registry.register(set_spec)
    registry.register(get_spec)
    return [set_spec.name, get_spec.name]
