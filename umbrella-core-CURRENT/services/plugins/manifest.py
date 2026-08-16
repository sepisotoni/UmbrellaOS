"""
services/plugins/manifest.py — PluginManifest: validated representation of
a plugin's `plugin.json`.

See docs/design/plugin-sdk-manifest-and-registration.md for the full
design rationale. This module only parses and structurally validates a
manifest; it does not touch the database (permission-key validation
against the real `Permission` table happens in
`services/plugins/registration.py`, which has a `db` session) and does not
execute any plugin code (that's `services/plugins/sandbox.py`).
"""
from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator, model_validator

# Deliberately tiny vocabulary — see the design doc's "Param/result schema
# vocabulary" section for why nested objects/arrays/$ref are out of scope.
_ALLOWED_FIELD_TYPES = {"string", "integer", "number", "boolean"}

_PLUGIN_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_LOCAL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+)?$"
)

_DASHBOARD_SLOTS = {"sidebar.tools", "sidebar.moderation", "dashboard.widgets"}

# Phase 10, Decision 7 (DASHBOARD-PLUGIN-UI-SCOPING.md): tiny vocabulary for
# the widget-shape signal, same pattern as _ALLOWED_FIELD_TYPES. "table" is
# deliberately withheld until Tier 3 (plugin-owned pages) needs it — Tier 1
# widgets never render a table-shaped slot.
_ALLOWED_RENDER_AS = {"stat_pair", "status_badge", "simple_list"}

# Phase 10, Tier 3 (DASHBOARD-PLUGIN-UI-SCOPING.md, "Tier 3 — Plugin-owned
# pages"): the same tiny vocabulary as Tier 1, plus "table" — the one shape
# Tier 1 never needs (a stat card can't represent an inventory-status view)
# but a whole page reasonably can. Still schema-driven, still no
# plugin-supplied markup — same trust boundary as Tier 1, just one shape
# richer.
_ALLOWED_PAGE_RENDER_AS = _ALLOWED_RENDER_AS | {"table"}

# Phase 10, Tier 3, Decision 5's "nav metadata" bullet: an icon reference
# from the dashboard's own existing lucide-react set, never a plugin-
# supplied icon asset — same no-plugin-assets stance as the rendering
# model. Deliberately small and hand-picked rather than "any lucide-react
# name": keeps the dashboard's icon lookup table (a fixed, reviewable
# import list) in lockstep with what a manifest can actually request, and
# a plugin author can't request an icon that reads as misleading (e.g.
# "shield" for something with no security meaning) — small, curated set,
# same tiny-vocabulary discipline as _ALLOWED_FIELD_TYPES.
_ALLOWED_NAV_ICONS = {
    "box", "layout-grid", "activity", "database", "list",
    "bar-chart", "puzzle", "settings", "server",
}

# Phase 10, Tier 2 (Decision 2, DASHBOARD-PLUGIN-UI-SCOPING.md): "starting
# scope: booleans/toggles only — text/number fields are a natural
# follow-on if a real plugin needs them, don't build them speculatively."
# One-element set today on purpose — same tiny-vocabulary discipline as
# every other _ALLOWED_* set in this module, just smaller because the
# scoping doc explicitly said not to get ahead of real demand here.
_ALLOWED_CONFIG_FIELD_TYPES = {"boolean"}


class ManifestValidationError(ValueError):
    """Raised for a structurally invalid manifest. Caught by the install
    flow and surfaced as a rejected install, never as an unhandled 500 —
    a malformed manifest is an expected, untrusted-input condition, not a
    programming error the way `CapabilityAlreadyRegisteredError` is for
    core capabilities."""


class ParamField(BaseModel):
    type: str
    required: bool = True

    @field_validator("type")
    @classmethod
    def _known_type(cls, v: str) -> str:
        if v not in _ALLOWED_FIELD_TYPES:
            raise ManifestValidationError(
                f"Unsupported field type {v!r}. Allowed: {sorted(_ALLOWED_FIELD_TYPES)}."
            )
        return v


class PluginCapability(BaseModel):
    local_name: str
    summary: str
    entrypoint: str  # "module:function" inside the plugin zip
    params: dict[str, ParamField] = Field(default_factory=dict)
    result: dict[str, ParamField] = Field(default_factory=dict)
    required_permission: str | None = None
    destructive: bool = False
    reversible: bool = True
    audited: bool = True

    @field_validator("local_name")
    @classmethod
    def _local_name_shape(cls, v: str) -> str:
        # No dots allowed: this is what stops a plugin from declaring
        # local_name="other_plugin.foo" and spoofing another plugin's
        # namespace, or "platform.whoami" and colliding with a core
        # capability's exact name once the "plugin.<id>." prefix is
        # prepended (a leading dot-containing local_name would otherwise
        # still produce a globally-unique-looking but confusing name).
        if "." in v:
            raise ManifestValidationError(
                f"capabilities[].local_name {v!r} must not contain '.' — "
                "the 'plugin.<plugin_id>.' prefix is added automatically "
                "at registration time."
            )
        if not _LOCAL_NAME_RE.match(v):
            raise ManifestValidationError(
                f"capabilities[].local_name {v!r} must match {_LOCAL_NAME_RE.pattern!r}."
            )
        return v

    @field_validator("entrypoint")
    @classmethod
    def _entrypoint_shape(cls, v: str) -> str:
        if ":" not in v or v.count(":") != 1:
            raise ManifestValidationError(
                f"entrypoint {v!r} must be exactly 'module:function'."
            )
        module, _, func = v.partition(":")
        if not module or not func:
            raise ManifestValidationError(
                f"entrypoint {v!r} must be exactly 'module:function' with both parts non-empty."
            )
        return v


class DiscordCommandDecl(BaseModel):
    name: str
    description: str
    capability: str  # references a capabilities[].local_name in this manifest


class DashboardSlotDecl(BaseModel):
    slot: str
    label: str
    capability: str  # references a capabilities[].local_name in this manifest
    # Phase 10, Decision 7: optional widget-shape signal. None is valid and
    # expected for plugins written before this field existed, or that don't
    # care to be explicit — the dashboard falls back to shape-based
    # inference from the capability's actual result payload in that case.
    # render_as is the reliable path; inference is graceful degradation,
    # never the other way around.
    render_as: str | None = None

    @field_validator("slot")
    @classmethod
    def _known_slot(cls, v: str) -> str:
        if v not in _DASHBOARD_SLOTS:
            raise ManifestValidationError(
                f"dashboard_ui_slots[].slot {v!r} is not a recognized slot. "
                f"Allowed: {sorted(_DASHBOARD_SLOTS)}."
            )
        return v

    @field_validator("render_as")
    @classmethod
    def _known_render_as(cls, v: str | None) -> str | None:
        if v is not None and v not in _ALLOWED_RENDER_AS:
            raise ManifestValidationError(
                f"dashboard_ui_slots[].render_as {v!r} is not a recognized "
                f"shape. Allowed: {sorted(_ALLOWED_RENDER_AS)}, or omit the "
                "field entirely to fall back to shape-based inference."
            )
        return v


class PageWidgetDecl(BaseModel):
    """One widget on a plugin's Tier 3 page. Deliberately not the same
    class as `DashboardSlotDecl` even though the fields overlap heavily:
    a page widget has no `slot` (it isn't slotted into the dashboard grid
    or sidebar, it's positioned on the plugin's own page in declared
    order) and allows the wider `_ALLOWED_PAGE_RENDER_AS` vocabulary."""

    label: str
    capability: str  # references a capabilities[].local_name in this manifest
    render_as: str | None = None

    @field_validator("render_as")
    @classmethod
    def _known_page_render_as(cls, v: str | None) -> str | None:
        if v is not None and v not in _ALLOWED_PAGE_RENDER_AS:
            raise ManifestValidationError(
                f"page.widgets[].render_as {v!r} is not a recognized shape. "
                f"Allowed: {sorted(_ALLOWED_PAGE_RENDER_AS)}, or omit the field "
                "entirely to fall back to shape-based inference."
            )
        return v


class PageDecl(BaseModel):
    """Phase 10, Tier 3: a plugin's own dashboard page. Strictly opt-in —
    omitting this field entirely (the default) means no page, no sidebar
    nav entry, nothing rendered. This is the confirmed default from
    DASHBOARD-PLUGIN-UI-SCOPING.md's Tier 3 section, not just a
    nice-to-have."""

    nav_label: str
    nav_icon: str
    widgets: list[PageWidgetDecl] = Field(default_factory=list)

    @field_validator("nav_icon")
    @classmethod
    def _known_nav_icon(cls, v: str) -> str:
        if v not in _ALLOWED_NAV_ICONS:
            raise ManifestValidationError(
                f"page.nav_icon {v!r} is not a recognized icon. "
                f"Allowed: {sorted(_ALLOWED_NAV_ICONS)}."
            )
        return v

    @field_validator("widgets")
    @classmethod
    def _at_least_one_widget(cls, v: list["PageWidgetDecl"]) -> list["PageWidgetDecl"]:
        if len(v) == 0:
            raise ManifestValidationError(
                "page.widgets must declare at least one widget — a page with "
                "no content isn't a real page. Omit the 'page' field entirely "
                "if the plugin doesn't need one."
            )
        return v


class ConfigFieldDecl(BaseModel):
    """Phase 10, Tier 2 (Decision 2 — DECIDED: Option A, per-plugin
    auto-generated config-write capability; see
    docs/design/phase10-decision2-config-write-capability-shape.md).

    Unlike DashboardSlotDecl/PageWidgetDecl, `key` does not reference a
    capability — it names a slot in this plugin's own kv storage
    (models/plugin_kv.py), read/written only through the auto-generated
    plugin.<plugin_id>.config.get/.set capabilities
    (services/plugins/registration.py), never through a plugin-declared
    capability the plugin author writes themselves. That's the whole
    point of Option A: the write path is platform-owned, not
    plugin-owned, so its permission can be scoped per-plugin without
    trusting plugin code to enforce that scoping itself.
    """

    key: str
    type: str
    label: str
    default_value: bool

    @field_validator("key")
    @classmethod
    def _key_shape(cls, v: str) -> str:
        if not _LOCAL_NAME_RE.match(v):
            raise ManifestValidationError(
                f"config_fields[].key {v!r} must match {_LOCAL_NAME_RE.pattern!r} "
                "(same shape as a capability's local_name)."
            )
        return v

    @field_validator("type")
    @classmethod
    def _known_type(cls, v: str) -> str:
        if v not in _ALLOWED_CONFIG_FIELD_TYPES:
            raise ManifestValidationError(
                f"config_fields[].type {v!r} is not supported yet. "
                f"Allowed: {sorted(_ALLOWED_CONFIG_FIELD_TYPES)} (Tier 2's "
                "starting scope is boolean toggles only — see "
                "DASHBOARD-PLUGIN-UI-SCOPING.md)."
            )
        return v


class PluginManifest(BaseModel):
    schema_version: int
    plugin_id: str
    name: str
    version: str
    author: str
    description: str = ""
    storage: str = "kv"

    capabilities: list[PluginCapability] = Field(default_factory=list)
    discord_commands: list[DiscordCommandDecl] = Field(default_factory=list)
    dashboard_ui_slots: list[DashboardSlotDecl] = Field(default_factory=list)
    # Phase 10, Tier 3: strictly opt-in — None (the default) means this
    # plugin has no page at all, not an empty/placeholder one.
    page: PageDecl | None = None
    # Phase 10, Tier 2: strictly opt-in, same as `page` — an empty list
    # (the default) means this plugin has no dashboard-configurable
    # settings at all, not a placeholder Settings section with nothing in
    # it.
    config_fields: list[ConfigFieldDecl] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def _known_schema_version(cls, v: int) -> int:
        if v != 1:
            raise ManifestValidationError(f"Unsupported schema_version {v!r}; only 1 is currently supported.")
        return v

    @field_validator("plugin_id")
    @classmethod
    def _plugin_id_shape(cls, v: str) -> str:
        if not _PLUGIN_ID_RE.match(v):
            raise ManifestValidationError(f"plugin_id {v!r} must match {_PLUGIN_ID_RE.pattern!r}.")
        return v

    @field_validator("version")
    @classmethod
    def _version_shape(cls, v: str) -> str:
        if not _SEMVER_RE.match(v):
            raise ManifestValidationError(f"version {v!r} must be a valid semver string.")
        return v

    @field_validator("storage")
    @classmethod
    def _storage_mode(cls, v: str) -> str:
        if v not in ("kv", "sqlite"):
            raise ManifestValidationError(f"storage {v!r} must be one of 'kv', 'sqlite'.")
        return v

    @model_validator(mode="after")
    def _cross_reference_capabilities(self) -> "PluginManifest":
        local_names = [c.local_name for c in self.capabilities]
        dupes = {n for n in local_names if local_names.count(n) > 1}
        if dupes:
            raise ManifestValidationError(
                f"capabilities[].local_name values must be unique within a manifest; duplicated: {sorted(dupes)}."
            )
        known = set(local_names)
        for cmd in self.discord_commands:
            if cmd.capability not in known:
                raise ManifestValidationError(
                    f"discord_commands[].capability {cmd.capability!r} does not match any "
                    f"capabilities[].local_name in this manifest."
                )
        for slot in self.dashboard_ui_slots:
            if slot.capability not in known:
                raise ManifestValidationError(
                    f"dashboard_ui_slots[].capability {slot.capability!r} does not match any "
                    f"capabilities[].local_name in this manifest."
                )
        if self.page is not None:
            for widget in self.page.widgets:
                if widget.capability not in known:
                    raise ManifestValidationError(
                        f"page.widgets[].capability {widget.capability!r} does not match any "
                        f"capabilities[].local_name in this manifest."
                    )
        config_keys = [f.key for f in self.config_fields]
        config_dupes = {k for k in config_keys if config_keys.count(k) > 1}
        if config_dupes:
            raise ManifestValidationError(
                f"config_fields[].key values must be unique within a manifest; "
                f"duplicated: {sorted(config_dupes)}."
            )
        return self


def parse_manifest(raw: dict) -> PluginManifest:
    """Entry point the install flow calls with the parsed JSON body of
    `plugin.json`. Wraps pydantic's ValidationError into our own
    ManifestValidationError so callers only need to catch one exception
    type regardless of which validator inside the model tripped."""
    try:
        return PluginManifest.model_validate(raw)
    except ManifestValidationError:
        raise
    except Exception as exc:  # pydantic.ValidationError and friends
        raise ManifestValidationError(str(exc)) from exc
