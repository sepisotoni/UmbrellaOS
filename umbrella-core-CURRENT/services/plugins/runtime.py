"""
services/plugins/runtime.py — the process-wide ProcessSandbox instance, and
`reload_installed_plugins`, which re-registers every already-installed
plugin's capabilities into the CapabilityRegistry and sandbox at process
startup.

Why this needs to exist at all: `CapabilityRegistry` and `ProcessSandbox`
are both in-memory, process-lifetime objects — nothing about a plugin
capability survives a restart on its own. `models/marketplace.py`'s
`PluginInstall` table is what makes an install durable *as a fact*; this
module is what turns that durable fact back into live, callable capability
registrations every time the process starts, exactly as
services/plugins/__init__.py's own docstring already anticipated
("registered dynamically... from the installed-plugins table at startup").

A single shared ProcessSandbox instance (not one per plugin) is used
because sandbox.py's own `sources` shape is already
`{plugin_id: {module_name: source_text}}` — one instance naturally holds
every installed plugin's sources side by side, and `set_plugin_sources`/
`remove_plugin_sources` (added alongside this module) let the marketplace
install flow update it live without swapping the instance other code may
already hold a reference to.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.marketplace import PluginInstall
from registry.registry import CapabilityRegistry
from registry.registry import registry as default_registry
from services.plugins.manifest import ManifestValidationError, parse_manifest
from services.plugins.registration import register_plugin_capabilities
from services.plugins.sandbox import ProcessSandbox
from services.plugins.source_store import PluginPackageError, extract_sources, load_verified_zip_bytes
from services.metrics_service import installed_plugins

logger = logging.getLogger(__name__)

# Process-wide sandbox instance every installed plugin's source lives in.
# Mirrors registry/registry.py's module-level `registry` singleton — same
# "one shared instance, adapters/services import and use it directly
# rather than constructing their own" pattern already established there.
plugin_sandbox = ProcessSandbox(sources={})


async def reload_installed_plugins(
    db: AsyncSession,
    *,
    sandbox: ProcessSandbox = plugin_sandbox,
    registry: CapabilityRegistry = default_registry,
) -> list[str]:
    """Re-registers every row in `plugin_installs` into `registry` and
    `sandbox`, in plugin_id order. Called once at app startup (main.py's
    lifespan, after `create_tables`/defaults-seeding), and directly by
    tests that want to exercise the same path without a full app boot.

    Deliberately tolerant of a single corrupt/unreadable install: an admin
    who force-deleted a plugin's zip off disk, or a manifest that somehow
    no longer parses, must not be able to take the *entire* app down at
    startup by leaving one bad PluginInstall row behind — that row is
    logged and skipped, and every other installed plugin still loads.
    This mirrors the general principle behind
    services/plugins/registration.py's own all-or-nothing-*per-manifest*
    rule (one plugin's registration failing is contained to that plugin);
    here that containment is just applied at process-startup granularity
    instead of single-install-call granularity.

    Returns the flat list of capability names successfully re-registered,
    across every plugin — mainly useful for tests/startup logging.
    """
    result = await db.execute(select(PluginInstall).order_by(PluginInstall.plugin_id))
    installs = list(result.scalars().all())

    registered: list[str] = []
    for install in installs:
        try:
            manifest = parse_manifest(json.loads(install.manifest_json))
            zip_bytes = load_verified_zip_bytes(install.zip_path, install.sha256_hash)
            sources = extract_sources(zip_bytes)
            sandbox.set_plugin_sources(install.plugin_id, sources)
            names = await register_plugin_capabilities(manifest, sandbox, db, registry=registry)
            registered.extend(names)
        except (ManifestValidationError, PluginPackageError) as exc:
            logger.error(
                "Skipping plugin %r at startup re-registration: %s", install.plugin_id, exc
            )
            continue

    installed_plugins.set(len(installs))
    return registered
