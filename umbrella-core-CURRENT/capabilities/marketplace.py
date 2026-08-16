"""
capabilities/marketplace.py — marketplace plugin listing/versioning/install
flow (Phase 7 item 3, the final handoff item). Declared as capabilities,
not a bespoke router — automatically reachable over REST/CLI/AI the moment
they're registered, same rule every other domain in this codebase follows
(see capabilities/webhooks.py's module docstring for the same point made
about Phase 7 item 2).

Actual publish/install/uninstall/discovery logic lives in
services/plugins/marketplace_service.py::MarketplaceService — these
capabilities are thin adapters from CallContext/params onto that service,
plus response-model shaping. `install`/`uninstall` operate on the
process-wide registry+sandbox singletons
(registry.registry.registry / services.plugins.runtime.plugin_sandbox) —
the same ones services/plugins/runtime.py::reload_installed_plugins
rebuilds at process startup, so an install made through these capabilities
survives a restart.

Zip upload is base64-encoded inside the JSON params body rather than a
bespoke multipart endpoint — consistent with every other capability in
this codebase being reachable through one generic
`POST /api/v1/capabilities/{name}/invoke` JSON path (see
docs/design/public-rest-api-and-webhooks.md, Decision 4). Base64 in JSON
carries real size overhead for large plugin packages; that's an accepted
v1 tradeoff, not an oversight — worth revisiting if plugin packages in
practice turn out to be large enough for it to matter.
"""
from __future__ import annotations

import base64
import binascii

from pydantic import BaseModel
from sqlalchemy import select

from models import User
from registry.context import CallContext
from registry.decorator import capability
from registry.registry import registry as default_registry
from services.plugins.marketplace_service import MarketplaceService
from services.plugins.runtime import plugin_sandbox

from api.middleware.errors import ValidationException


async def _resolve_actor(ctx: CallContext) -> str | None:
    """Same actor-resolution pattern as capabilities/webhooks.py's
    `_resolve_created_by` / capabilities/identity.py's create_api_key:
    only a staff (dashboard-authenticated) actor resolves to a real user
    id; an API-key-authenticated caller has no dashboard user to
    attribute a publish/install/uninstall to."""
    if ctx.actor_type == "staff":
        result = await ctx.db.execute(select(User).where(User.discord_id == ctx.actor_id))
        user = result.scalar_one_or_none()
        return user.id if user else None
    return None


def _decode_zip(zip_base64: str) -> bytes:
    try:
        return base64.b64decode(zip_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValidationException(f"zip_base64 is not valid base64: {exc}") from exc


# --------------------------------------------------------------------------
# Result models
# --------------------------------------------------------------------------


class PluginListingResult(BaseModel):
    plugin_id: str
    name: str
    author: str
    description: str
    latest_version: str

    @classmethod
    def from_model(cls, listing) -> "PluginListingResult":
        return cls(
            plugin_id=listing.plugin_id,
            name=listing.name,
            author=listing.author,
            description=listing.description,
            latest_version=listing.latest_version,
        )


class PluginVersionResult(BaseModel):
    plugin_id: str
    version: str
    sha256_hash: str
    published_at: str

    @classmethod
    def from_model(cls, version) -> "PluginVersionResult":
        return cls(
            plugin_id=version.plugin_id,
            version=version.version,
            sha256_hash=version.sha256_hash,
            published_at=version.published_at.isoformat(),
        )


class PluginInstallResult(BaseModel):
    plugin_id: str
    installed_version: str
    registered_capability_names: list[str]

    @classmethod
    def from_model(cls, install) -> "PluginInstallResult":
        return cls(
            plugin_id=install.plugin_id,
            installed_version=install.installed_version,
            registered_capability_names=list(install.registered_capability_names),
        )


class DiscordCommandResult(BaseModel):
    plugin_id: str
    name: str
    description: str
    capability_name: str

    @classmethod
    def from_entry(cls, entry) -> "DiscordCommandResult":
        return cls(
            plugin_id=entry.plugin_id, name=entry.name,
            description=entry.description, capability_name=entry.capability_name,
        )


class DashboardSlotResult(BaseModel):
    plugin_id: str
    slot: str
    label: str
    capability_name: str
    # Phase 10, Decision 7 (DASHBOARD-PLUGIN-UI-SCOPING.md "Confirmed gap"
    # section). None when the plugin's manifest didn't declare a shape —
    # the dashboard falls back to shape-based inference from the actual
    # result payload in that case; this field is the reliable path, not
    # the only path.
    render_as: str | None = None

    @classmethod
    def from_entry(cls, entry) -> "DashboardSlotResult":
        return cls(
            plugin_id=entry.plugin_id, slot=entry.slot,
            label=entry.label, capability_name=entry.capability_name,
            render_as=entry.render_as,
        )


# --------------------------------------------------------------------------
# marketplace.listing.publish
# --------------------------------------------------------------------------


class PublishListingParams(BaseModel):
    zip_base64: str


@capability(
    name="marketplace.listing.publish",
    summary="Publish a new plugin version to the marketplace catalog from a base64-encoded plugin zip.",
    params_model=PublishListingParams,
    result_model=PluginVersionResult,
    required_permission="marketplace.listing.manage",
    destructive=False,
    reversible=False,
    audit_category="marketplace",
)
async def publish_listing(ctx: CallContext, params: PublishListingParams) -> PluginVersionResult:
    zip_bytes = _decode_zip(params.zip_base64)
    published_by = await _resolve_actor(ctx)
    version = await MarketplaceService.publish_version(ctx.db, zip_bytes=zip_bytes, published_by=published_by)
    return PluginVersionResult.from_model(version)


# --------------------------------------------------------------------------
# marketplace.listing.list
# --------------------------------------------------------------------------


class ListListingsParams(BaseModel):
    pass


@capability(
    name="marketplace.listing.list",
    summary="List every plugin in the marketplace catalog.",
    params_model=ListListingsParams,
    result_model=list[PluginListingResult],
    required_permission="marketplace.listing.view",
    destructive=False,
    audited=False,
)
async def list_listings(ctx: CallContext, params: ListListingsParams) -> list[PluginListingResult]:
    listings = await MarketplaceService.list_listings(ctx.db)
    return [PluginListingResult.from_model(listing) for listing in listings]


# --------------------------------------------------------------------------
# marketplace.listing.versions
# --------------------------------------------------------------------------


class ListVersionsParams(BaseModel):
    plugin_id: str


@capability(
    name="marketplace.listing.versions",
    summary="List every published version of one plugin, oldest first.",
    params_model=ListVersionsParams,
    result_model=list[PluginVersionResult],
    required_permission="marketplace.listing.view",
    destructive=False,
    audited=False,
)
async def list_versions(ctx: CallContext, params: ListVersionsParams) -> list[PluginVersionResult]:
    versions = await MarketplaceService.list_versions(ctx.db, params.plugin_id)
    return [PluginVersionResult.from_model(v) for v in versions]


# --------------------------------------------------------------------------
# marketplace.install.install
# --------------------------------------------------------------------------


class InstallParams(BaseModel):
    plugin_id: str
    version: str

    def audit_target(self) -> str:
        return self.plugin_id


@capability(
    name="marketplace.install.install",
    summary="Install a published plugin version on this instance, or update it if a different version is already installed.",
    params_model=InstallParams,
    result_model=PluginInstallResult,
    required_permission="marketplace.install.manage",
    destructive=True,
    reversible=True,
    audit_category="marketplace",
)
async def install(ctx: CallContext, params: InstallParams) -> PluginInstallResult:
    installed_by = await _resolve_actor(ctx)
    install_row = await MarketplaceService.install(
        ctx.db,
        plugin_id=params.plugin_id,
        version=params.version,
        installed_by=installed_by,
        sandbox=plugin_sandbox,
        registry=default_registry,
    )
    return PluginInstallResult.from_model(install_row)


# --------------------------------------------------------------------------
# marketplace.install.uninstall
# --------------------------------------------------------------------------


class UninstallParams(BaseModel):
    plugin_id: str

    def audit_target(self) -> str:
        return self.plugin_id


class UninstallResult(BaseModel):
    uninstalled: bool


@capability(
    name="marketplace.install.uninstall",
    summary="Uninstall a plugin from this instance, unregistering its capabilities.",
    params_model=UninstallParams,
    result_model=UninstallResult,
    required_permission="marketplace.install.manage",
    destructive=True,
    reversible=True,
    audit_category="marketplace",
)
async def uninstall(ctx: CallContext, params: UninstallParams) -> UninstallResult:
    await MarketplaceService.uninstall(
        ctx.db, plugin_id=params.plugin_id, sandbox=plugin_sandbox, registry=default_registry
    )
    return UninstallResult(uninstalled=True)


# --------------------------------------------------------------------------
# marketplace.install.list
# --------------------------------------------------------------------------


class ListInstalledParams(BaseModel):
    pass


@capability(
    name="marketplace.install.list",
    summary="List every plugin currently installed on this instance.",
    params_model=ListInstalledParams,
    result_model=list[PluginInstallResult],
    required_permission="marketplace.install.view",
    destructive=False,
    audited=False,
)
async def list_installed(ctx: CallContext, params: ListInstalledParams) -> list[PluginInstallResult]:
    installs = await MarketplaceService.list_installed(ctx.db)
    return [PluginInstallResult.from_model(i) for i in installs]


# --------------------------------------------------------------------------
# marketplace.install.discord_commands — the discovery surface that makes
# discord_commands genuinely usable post-install (design decision 1). A
# Discord bot process syncs slash commands from this list and invokes them
# via the normal generic capability-invoke path — see module docstring.
# --------------------------------------------------------------------------


class ListDiscordCommandsParams(BaseModel):
    pass


@capability(
    name="marketplace.install.discord_commands",
    summary="List every Discord command declared by an installed plugin, with the capability name to invoke for each.",
    params_model=ListDiscordCommandsParams,
    result_model=list[DiscordCommandResult],
    required_permission="marketplace.install.view",
    destructive=False,
    audited=False,
)
async def discord_commands(ctx: CallContext, params: ListDiscordCommandsParams) -> list[DiscordCommandResult]:
    entries = await MarketplaceService.discord_commands(ctx.db)
    return [DiscordCommandResult.from_entry(e) for e in entries]


# --------------------------------------------------------------------------
# marketplace.install.dashboard_slots — same discovery role for
# dashboard_ui_slots.
# --------------------------------------------------------------------------


class PageWidgetResult(BaseModel):
    label: str
    capability_name: str
    render_as: str | None = None

    @classmethod
    def from_entry(cls, entry) -> "PageWidgetResult":
        return cls(label=entry.label, capability_name=entry.capability_name, render_as=entry.render_as)


class PageNavResult(BaseModel):
    plugin_id: str
    nav_label: str
    nav_icon: str

    @classmethod
    def from_entry(cls, entry) -> "PageNavResult":
        return cls(plugin_id=entry.plugin_id, nav_label=entry.nav_label, nav_icon=entry.nav_icon)


class PageLayoutResult(BaseModel):
    plugin_id: str
    nav_label: str
    nav_icon: str
    widgets: list[PageWidgetResult]

    @classmethod
    def from_entry(cls, entry) -> "PageLayoutResult":
        return cls(
            plugin_id=entry.plugin_id,
            nav_label=entry.nav_label,
            nav_icon=entry.nav_icon,
            widgets=[PageWidgetResult.from_entry(w) for w in entry.widgets],
        )


class ListDashboardSlotsParams(BaseModel):
    slot: str | None = None


@capability(
    name="marketplace.install.dashboard_slots",
    summary="List every dashboard UI slot entry declared by an installed plugin, optionally filtered to one slot.",
    params_model=ListDashboardSlotsParams,
    result_model=list[DashboardSlotResult],
    required_permission="marketplace.install.view",
    destructive=False,
    audited=False,
)
async def dashboard_slots(ctx: CallContext, params: ListDashboardSlotsParams) -> list[DashboardSlotResult]:
    entries = await MarketplaceService.dashboard_slots(ctx.db, slot=params.slot)
    return [DashboardSlotResult.from_entry(e) for e in entries]


# --------------------------------------------------------------------------
# marketplace.install.pages — Phase 10, Tier 3 discovery surface for the
# sidebar: which installed plugins declared their own page, and the nav
# metadata (label + icon) to link to it. Same required_permission and
# audited=False posture as discord_commands/dashboard_slots above — this is
# read-only discovery, not an action.
# --------------------------------------------------------------------------


class ListPagesParams(BaseModel):
    pass


@capability(
    name="marketplace.install.pages",
    summary="List nav metadata (label + icon) for every installed plugin that declared its own dashboard page.",
    params_model=ListPagesParams,
    result_model=list[PageNavResult],
    required_permission="marketplace.install.view",
    destructive=False,
    audited=False,
)
async def pages(ctx: CallContext, params: ListPagesParams) -> list[PageNavResult]:
    entries = await MarketplaceService.pages(ctx.db)
    return [PageNavResult.from_entry(e) for e in entries]


# --------------------------------------------------------------------------
# marketplace.install.configurable_plugins — Phase 10, Tier 2 (Decision 2
# Option A). What the Settings page fetches once to know which installed
# plugins have anything to show — mirrors `pages`'s exact shape above,
# same "list nav-weight metadata, fetch full data per-item lazily" split.
# --------------------------------------------------------------------------


class ConfigurablePluginResult(BaseModel):
    plugin_id: str
    plugin_name: str
    field_count: int

    @classmethod
    def from_entry(cls, entry) -> "ConfigurablePluginResult":
        return cls(
            plugin_id=entry.plugin_id, plugin_name=entry.plugin_name,
            field_count=entry.field_count,
        )


class ListConfigurablePluginsParams(BaseModel):
    pass


@capability(
    name="marketplace.install.configurable_plugins",
    summary="List every installed plugin that declared dashboard-configurable settings (Tier 2).",
    params_model=ListConfigurablePluginsParams,
    result_model=list[ConfigurablePluginResult],
    required_permission="marketplace.install.view",
    destructive=False,
    audited=False,
)
async def configurable_plugins(
    ctx: CallContext, params: ListConfigurablePluginsParams
) -> list[ConfigurablePluginResult]:
    entries = await MarketplaceService.configurable_plugins(ctx.db)
    return [ConfigurablePluginResult.from_entry(e) for e in entries]


# --------------------------------------------------------------------------
# marketplace.install.page_layout — the full declared layout for one
# plugin's page, resolved to fully-qualified capability names. What
# app/marketplace/[pluginId]/page.tsx's one generic dynamic route (Decision
# 5) fetches on every visit.
# --------------------------------------------------------------------------


class GetPageLayoutParams(BaseModel):
    plugin_id: str


@capability(
    name="marketplace.install.page_layout",
    summary="Get the declared page layout (nav metadata + ordered widget list) for one installed plugin.",
    params_model=GetPageLayoutParams,
    result_model=PageLayoutResult,
    required_permission="marketplace.install.view",
    destructive=False,
    audited=False,
)
async def page_layout(ctx: CallContext, params: GetPageLayoutParams) -> PageLayoutResult:
    entry = await MarketplaceService.page_layout(ctx.db, params.plugin_id)
    return PageLayoutResult.from_entry(entry)
