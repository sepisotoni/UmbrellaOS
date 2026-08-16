"""
services/plugins/marketplace_service.py — MarketplaceService: publish new
plugin listings/versions, install/update/uninstall a plugin on this
instance, and list what installed plugins expose (capabilities,
discord_commands, dashboard_ui_slots) for any consumer to query.

This is Phase 7 item 3, the final handoff item. See
docs/design/plugin-sdk-manifest-and-registration.md for the manifest/
registration layer this builds on, and the two design decisions this
service implements directly:

1. discord_commands/dashboard_ui_slots must be genuinely usable post-
   install, not just validated-and-stored — see `discord_commands()` and
   `dashboard_slots()` below. These make that data live and queryable via
   capabilities (capabilities/marketplace.py), the same generic REST/CLI/
   AI-reachable path every other capability in this codebase uses — so any
   consumer (a Discord bot process, the dashboard frontend) can sync
   against it without UmbrellaOS-core hand-writing a per-plugin cog or
   per-plugin dashboard widget. Actually registering a slash command with
   Discord's API, or rendering a dashboard widget, is a *consumer-side*
   concern outside this repo's boundary — see the Phase 7 handoff
   checkpoint notes for why that's a deliberate scope line, not an
   oversight.

2. Local disk storage under
   f"{plugin_storage_root}/{plugin_id}/{version}/plugin.zip"
   (services/plugins/source_store.py), SHA-256 verified against the
   marketplace listing's declared hash before source ever reaches the
   sandbox (`load_verified_zip_bytes`), and explicit admin action
   required to update an already-installed plugin — `install()` below is
   the only path that changes what's installed; nothing calls it
   automatically.

Known limitation, documented rather than silently engineered around: an
update's manifest is fully validated (permission refs checked, capability
specs built) against a throwaway registry *before* anything about the
live registry/sandbox is touched — see `install()`'s docstring — so a
failing update never leaves the plugin's old capabilities unregistered
with nothing to replace them. The one gap that validation can't catch is
a new version renaming a `local_name` so its fully-qualified capability
name collides with a *different, unrelated* plugin's already-registered
capability — that's only discovered at the final commit step, after this
plugin's old capabilities have already been unregistered. This is judged
an acceptable, rare edge case for v1 rather than a reason to build full
cross-plugin dry-run/rollback machinery; a future increment could close
it by dry-running the commit step against a registry snapshot that
already contains every *other* installed plugin's capabilities, not just
an empty scratch one.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import ConflictException, ResourceNotFoundException, ValidationException
from models.marketplace import PluginInstall, PluginListing, PluginVersion
from registry.registry import CapabilityNotFoundError, CapabilityRegistry
from services.plugins.manifest import ManifestValidationError, PluginManifest, parse_manifest
from services.plugins.registration import (
    PluginRegistrationError,
    register_plugin_capabilities,
    register_plugin_config_capabilities,
)
from services.plugins.sandbox import ProcessSandbox
from services.plugins.source_store import PluginPackageError, extract_sources, load_verified_zip_bytes, read_manifest_dict, store_zip

logger = logging.getLogger(__name__)


class DiscordCommandEntry:
    """One installed plugin's declared Discord command, resolved to the
    fully-qualified capability name a consumer (the Discord bot process)
    would invoke via the generic capability-invoke path."""

    def __init__(self, plugin_id: str, name: str, description: str, capability_name: str):
        self.plugin_id = plugin_id
        self.name = name
        self.description = description
        self.capability_name = capability_name


class DashboardSlotEntry:
    """One installed plugin's declared dashboard UI slot, resolved to its
    fully-qualified capability name."""

    def __init__(
        self,
        plugin_id: str,
        slot: str,
        label: str,
        capability_name: str,
        render_as: str | None = None,
    ):
        self.plugin_id = plugin_id
        self.slot = slot
        self.label = label
        self.capability_name = capability_name
        # Phase 10, Decision 7 — see DashboardSlotDecl.render_as. None means
        # the manifest didn't declare a shape; the dashboard falls back to
        # inference from the capability's actual result payload.
        self.render_as = render_as


class PageWidgetEntry:
    """One resolved widget on an installed plugin's Tier 3 page —
    structurally the same idea as `DashboardSlotEntry` (label +
    fully-qualified capability name + optional render_as), just without a
    `slot` value since a page widget isn't slotted into the dashboard grid
    or sidebar."""

    def __init__(self, label: str, capability_name: str, render_as: str | None = None):
        self.label = label
        self.capability_name = capability_name
        self.render_as = render_as


class PageNavEntry:
    """Nav metadata for one installed plugin's Tier 3 page — deliberately
    lightweight (no widget data) since this is what the sidebar needs to
    render a nav link, not what a visit to the page itself needs."""

    def __init__(self, plugin_id: str, nav_label: str, nav_icon: str):
        self.plugin_id = plugin_id
        self.nav_label = nav_label
        self.nav_icon = nav_icon


class ConfigurablePluginEntry:
    """Phase 10, Tier 2 (Decision 2 Option A). One entry per installed
    plugin that declared `config_fields` — what the Settings page needs
    to know which plugins have anything to show, without resolving every
    field's current kv value here (that's a live config.get call per
    plugin, done lazily by the Settings page only for plugins it's
    actually about to render — same "nav metadata is cheap, full data is
    fetched separately" split PageNavEntry/page_layout already use)."""

    def __init__(self, plugin_id: str, plugin_name: str, field_count: int):
        self.plugin_id = plugin_id
        self.plugin_name = plugin_name
        self.field_count = field_count


class PageLayoutEntry:
    """The full declared layout for one installed plugin's Tier 3 page —
    nav metadata plus the resolved widget list, in manifest-declared
    order."""

    def __init__(
        self, plugin_id: str, nav_label: str, nav_icon: str, widgets: list[PageWidgetEntry]
    ):
        self.plugin_id = plugin_id
        self.nav_label = nav_label
        self.nav_icon = nav_icon
        self.widgets = widgets


class MarketplaceService:
    # ----------------------------------------------------------------
    # Publishing / listing
    # ----------------------------------------------------------------

    @staticmethod
    async def publish_version(
        db: AsyncSession, *, zip_bytes: bytes, published_by: str | None
    ) -> PluginVersion:
        """Validates and stores a new plugin version. The manifest inside
        the zip is the sole source of truth for plugin_id/name/version/
        author/description — there's no separate form field a publisher
        could get out of sync with what's actually in the package."""
        try:
            manifest = parse_manifest(read_manifest_dict(zip_bytes))
        except (ManifestValidationError, PluginPackageError) as exc:
            raise ValidationException(f"Invalid plugin package: {exc}") from exc

        existing_version = await db.scalar(
            select(PluginVersion).where(
                PluginVersion.plugin_id == manifest.plugin_id,
                PluginVersion.version == manifest.version,
            )
        )
        if existing_version is not None:
            raise ConflictException(
                f"Version {manifest.version!r} of plugin {manifest.plugin_id!r} is already "
                "published — versions are immutable once published; publish a new version instead."
            )

        zip_path, sha256_hash = store_zip(manifest.plugin_id, manifest.version, zip_bytes)

        listing = await db.get(PluginListing, manifest.plugin_id)
        now = datetime.now(timezone.utc)
        if listing is None:
            listing = PluginListing(
                plugin_id=manifest.plugin_id,
                name=manifest.name,
                author=manifest.author,
                description=manifest.description,
                latest_version=manifest.version,
            )
            db.add(listing)
        else:
            listing.name = manifest.name
            listing.author = manifest.author
            listing.description = manifest.description
            listing.latest_version = manifest.version
            listing.updated_at = now

        version_row = PluginVersion(
            plugin_id=manifest.plugin_id,
            version=manifest.version,
            manifest_json=json.dumps(manifest.model_dump()),
            sha256_hash=sha256_hash,
            zip_path=zip_path,
            published_by=published_by,
        )
        db.add(version_row)
        await db.flush()
        return version_row

    @staticmethod
    async def list_listings(db: AsyncSession) -> list[PluginListing]:
        result = await db.execute(select(PluginListing).order_by(PluginListing.plugin_id))
        return list(result.scalars().all())

    @staticmethod
    async def list_versions(db: AsyncSession, plugin_id: str) -> list[PluginVersion]:
        listing = await db.get(PluginListing, plugin_id)
        if listing is None:
            raise ResourceNotFoundException("Plugin listing", plugin_id)
        result = await db.execute(
            select(PluginVersion)
            .where(PluginVersion.plugin_id == plugin_id)
            .order_by(PluginVersion.published_at)
        )
        return list(result.scalars().all())

    # ----------------------------------------------------------------
    # Install / update / uninstall
    # ----------------------------------------------------------------

    @staticmethod
    async def install(
        db: AsyncSession,
        *,
        plugin_id: str,
        version: str,
        installed_by: str | None,
        sandbox: ProcessSandbox,
        registry: CapabilityRegistry,
    ) -> PluginInstall:
        """Installs `version` of `plugin_id`, or — if some other version of
        the same plugin_id is already installed — updates it in place
        (single-install-per-plugin model; there is no separate "update"
        capability, this is both, matching the explicit-admin-action
        decision: an admin still has to name the exact version either way).

        Validates the target version's manifest and package integrity
        completely, against a throwaway registry, before touching the
        live registry or sandbox at all — see the module docstring's
        "known limitation" note for the one edge case this doesn't cover.
        """
        version_row = await db.scalar(
            select(PluginVersion).where(
                PluginVersion.plugin_id == plugin_id, PluginVersion.version == version
            )
        )
        if version_row is None:
            raise ResourceNotFoundException("Plugin version", f"{plugin_id}@{version}")

        existing_install = await db.get(PluginInstall, plugin_id)
        if existing_install is not None and existing_install.installed_version == version:
            raise ConflictException(
                f"Plugin {plugin_id!r} is already installed at version {version!r}."
            )

        try:
            manifest: PluginManifest = parse_manifest(json.loads(version_row.manifest_json))
            zip_bytes = load_verified_zip_bytes(version_row.zip_path, version_row.sha256_hash)
            sources = extract_sources(zip_bytes)
        except (ManifestValidationError, PluginPackageError) as exc:
            raise ValidationException(f"Cannot install {plugin_id}@{version}: {exc}") from exc

        dry_run_registry = CapabilityRegistry()
        try:
            await register_plugin_capabilities(manifest, sandbox, db, registry=dry_run_registry)
            # Phase 10, Tier 2 (Decision 2, Option A): registered into the
            # same dry_run_registry as the line above, so a manifest error
            # in either half aborts the whole install before anything
            # touches the live registry — see
            # register_plugin_config_capabilities's docstring. No-op for a
            # manifest with no config_fields (most plugins).
            await register_plugin_config_capabilities(manifest, db, registry=dry_run_registry)
        except PluginRegistrationError as exc:
            raise ValidationException(f"Cannot install {plugin_id}@{version}: {exc}") from exc

        # Validation passed — safe to commit. Unregister the previous
        # install's capabilities first (if any), then set the new source
        # and register the validated specs, in that order, so a plugin
        # never briefly has stale-version handlers pointed at new sources.
        if existing_install is not None:
            for name in existing_install.registered_capability_names:
                try:
                    registry.unregister(name)
                except CapabilityNotFoundError:
                    logger.warning(
                        "Plugin %r's tracked capability %r was already missing from the "
                        "registry at update time — registering the new version anyway.",
                        plugin_id, name,
                    )

        sandbox.set_plugin_sources(manifest.plugin_id, sources)
        new_names: list[str] = []
        for spec in dry_run_registry.list():
            registry.register(spec)
            new_names.append(spec.name)

        if existing_install is not None:
            existing_install.installed_version = version
            existing_install.manifest_json = version_row.manifest_json
            existing_install.zip_path = version_row.zip_path
            existing_install.sha256_hash = version_row.sha256_hash
            existing_install.registered_capability_names = new_names
            existing_install.installed_by = installed_by
            install_row = existing_install
        else:
            install_row = PluginInstall(
                plugin_id=plugin_id,
                installed_version=version,
                manifest_json=version_row.manifest_json,
                zip_path=version_row.zip_path,
                sha256_hash=version_row.sha256_hash,
                registered_capability_names=new_names,
                installed_by=installed_by,
            )
            db.add(install_row)

        await db.flush()
        return install_row

    @staticmethod
    async def uninstall(
        db: AsyncSession,
        *,
        plugin_id: str,
        sandbox: ProcessSandbox,
        registry: CapabilityRegistry,
    ) -> None:
        install_row = await db.get(PluginInstall, plugin_id)
        if install_row is None:
            raise ResourceNotFoundException("Plugin install", plugin_id)

        for name in install_row.registered_capability_names:
            try:
                registry.unregister(name)
            except CapabilityNotFoundError:
                logger.warning(
                    "Plugin %r's tracked capability %r was already missing from the "
                    "registry at uninstall time.", plugin_id, name,
                )
        sandbox.remove_plugin_sources(plugin_id)
        await db.delete(install_row)
        await db.flush()

    @staticmethod
    async def list_installed(db: AsyncSession) -> list[PluginInstall]:
        result = await db.execute(select(PluginInstall).order_by(PluginInstall.plugin_id))
        return list(result.scalars().all())

    # ----------------------------------------------------------------
    # Discovery — the part that makes discord_commands/dashboard_ui_slots
    # genuinely usable rather than validated-and-inert. See module
    # docstring, design decision 1.
    # ----------------------------------------------------------------

    @staticmethod
    async def discord_commands(db: AsyncSession) -> list[DiscordCommandEntry]:
        installs = await MarketplaceService.list_installed(db)
        entries: list[DiscordCommandEntry] = []
        for install in installs:
            manifest = parse_manifest(json.loads(install.manifest_json))
            for cmd in manifest.discord_commands:
                entries.append(
                    DiscordCommandEntry(
                        plugin_id=install.plugin_id,
                        name=cmd.name,
                        description=cmd.description,
                        capability_name=f"plugin.{install.plugin_id}.{cmd.capability}",
                    )
                )
        return entries

    @staticmethod
    async def dashboard_slots(db: AsyncSession, *, slot: str | None = None) -> list[DashboardSlotEntry]:
        installs = await MarketplaceService.list_installed(db)
        entries: list[DashboardSlotEntry] = []
        for install in installs:
            manifest = parse_manifest(json.loads(install.manifest_json))
            for decl in manifest.dashboard_ui_slots:
                if slot is not None and decl.slot != slot:
                    continue
                entries.append(
                    DashboardSlotEntry(
                        plugin_id=install.plugin_id,
                        slot=decl.slot,
                        label=decl.label,
                        capability_name=f"plugin.{install.plugin_id}.{decl.capability}",
                        render_as=decl.render_as,
                    )
                )
        return entries

    # ----------------------------------------------------------------
    # Phase 10, Tier 3 — plugin-owned pages. Same discovery role as
    # discord_commands/dashboard_slots above: strictly opt-in per plugin
    # (DASHBOARD-PLUGIN-UI-SCOPING.md's Tier 3 section) — a plugin whose
    # manifest doesn't declare `page` contributes nothing to either method
    # below, not a placeholder or an empty entry.
    # ----------------------------------------------------------------

    @staticmethod
    async def pages(db: AsyncSession) -> list[PageNavEntry]:
        """Nav metadata only, for every installed plugin that declared a
        page — what the sidebar needs to build its plugin-page links.
        Deliberately doesn't resolve widget data here; that's a live
        per-widget capability call each, wasted work for entries the
        sidebar only turns into a `<Link>`."""
        installs = await MarketplaceService.list_installed(db)
        entries: list[PageNavEntry] = []
        for install in installs:
            manifest = parse_manifest(json.loads(install.manifest_json))
            if manifest.page is None:
                continue
            entries.append(
                PageNavEntry(
                    plugin_id=install.plugin_id,
                    nav_label=manifest.page.nav_label,
                    nav_icon=manifest.page.nav_icon,
                )
            )
        return entries

    @staticmethod
    async def configurable_plugins(db: AsyncSession) -> list[ConfigurablePluginEntry]:
        """Phase 10, Tier 2 (Decision 2 Option A). Every installed plugin
        that declared config_fields — what the Settings page fetches once
        to know which plugins to render a section for. Mirrors pages()'s
        exact shape (list_installed, parse each manifest, skip plugins
        with nothing declared) rather than inventing a different
        discovery pattern for this one tier."""
        installs = await MarketplaceService.list_installed(db)
        entries: list[ConfigurablePluginEntry] = []
        for install in installs:
            manifest = parse_manifest(json.loads(install.manifest_json))
            if not manifest.config_fields:
                continue
            entries.append(
                ConfigurablePluginEntry(
                    plugin_id=install.plugin_id,
                    plugin_name=manifest.name,
                    field_count=len(manifest.config_fields),
                )
            )
        return entries

    @staticmethod
    async def page_layout(db: AsyncSession, plugin_id: str) -> PageLayoutEntry:
        """The full declared layout for one plugin's page. Raises
        `ResourceNotFoundException` — not a nullable return — when the
        plugin isn't installed *or* is installed but declared no page;
        both are "this route has nothing to show" from the caller's
        perspective, and `ResourceNotFoundException` is the existing
        vocabulary this module already uses for exactly that (see
        `list_versions`), not a new response shape invented for this one
        capability."""
        install = await db.get(PluginInstall, plugin_id)
        if install is None:
            raise ResourceNotFoundException("Plugin install", plugin_id)
        manifest = parse_manifest(json.loads(install.manifest_json))
        if manifest.page is None:
            raise ResourceNotFoundException("Plugin page", plugin_id)
        widgets = [
            PageWidgetEntry(
                label=w.label,
                capability_name=f"plugin.{install.plugin_id}.{w.capability}",
                render_as=w.render_as,
            )
            for w in manifest.page.widgets
        ]
        return PageLayoutEntry(
            plugin_id=install.plugin_id,
            nav_label=manifest.page.nav_label,
            nav_icon=manifest.page.nav_icon,
            widgets=widgets,
        )
