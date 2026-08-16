"""tests/registry/test_marketplace_service.py — MarketplaceService: publish/
list/versions/install/update/uninstall/discovery, exercised directly
against the service layer (capabilities/marketplace.py's own tests cover
the capability-invocation/permission wiring on top of this).
"""
import io
import json
import zipfile

import pytest

from api.middleware.errors import ConflictException, ResourceNotFoundException, ValidationException
from config import get_settings
from registry.registry import CapabilityNotFoundError, CapabilityRegistry
from services.plugins.marketplace_service import MarketplaceService
from services.plugins.sandbox import ProcessSandbox


@pytest.fixture(autouse=True)
def _plugin_storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "plugin_storage_root", str(tmp_path / "plugins"))
    yield


def _manifest(**overrides) -> dict:
    raw = {
        "schema_version": 1,
        "plugin_id": "queue-tools",
        "name": "Queue Tools",
        "version": "1.0.0",
        "author": "example-author",
        "description": "Queue status reporting.",
        "capabilities": [
            {
                "local_name": "queue_status",
                "summary": "Report current queue depth.",
                "entrypoint": "handlers:queue_status",
                "params": {},
                "result": {"queue_depth": {"type": "integer"}},
                "required_permission": None,
            }
        ],
        "discord_commands": [
            {"name": "queue", "description": "Show queue status", "capability": "queue_status"}
        ],
        "dashboard_ui_slots": [
            {"slot": "sidebar.tools", "label": "Queue Status", "capability": "queue_status"}
        ],
    }
    raw.update(overrides)
    return raw


def _zip_for(manifest: dict, module_body: str = "def queue_status(params):\n    return {'queue_depth': 3}\n") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("plugin.json", json.dumps(manifest))
        zf.writestr("handlers.py", module_body)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_publish_version_creates_listing_and_version(db_session):
    async with db_session() as db:
        version_row = await MarketplaceService.publish_version(
            db, zip_bytes=_zip_for(_manifest()), published_by=None
        )
        await db.commit()
    assert version_row.plugin_id == "queue-tools"
    assert version_row.version == "1.0.0"

    async with db_session() as db:
        listings = await MarketplaceService.list_listings(db)
    assert len(listings) == 1
    assert listings[0].plugin_id == "queue-tools"
    assert listings[0].latest_version == "1.0.0"


@pytest.mark.asyncio
async def test_publish_second_version_updates_listing_latest_version(db_session):
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(_manifest()), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.publish_version(
            db, zip_bytes=_zip_for(_manifest(version="1.1.0")), published_by=None
        )
        await db.commit()

    async with db_session() as db:
        listings = await MarketplaceService.list_listings(db)
        versions = await MarketplaceService.list_versions(db, "queue-tools")

    assert listings[0].latest_version == "1.1.0"
    assert [v.version for v in versions] == ["1.0.0", "1.1.0"]


@pytest.mark.asyncio
async def test_publish_duplicate_version_raises_conflict(db_session):
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(_manifest()), published_by=None)
        await db.commit()
    async with db_session() as db:
        with pytest.raises(ConflictException):
            await MarketplaceService.publish_version(db, zip_bytes=_zip_for(_manifest()), published_by=None)


@pytest.mark.asyncio
async def test_publish_invalid_manifest_raises_validation_error(db_session):
    bad_zip = _zip_for(_manifest(schema_version=99))
    async with db_session() as db:
        with pytest.raises(ValidationException):
            await MarketplaceService.publish_version(db, zip_bytes=bad_zip, published_by=None)


@pytest.mark.asyncio
async def test_list_versions_unknown_plugin_raises_not_found(db_session):
    async with db_session() as db:
        with pytest.raises(ResourceNotFoundException):
            await MarketplaceService.list_versions(db, "never-published")


@pytest.mark.asyncio
async def test_install_registers_capability_and_creates_install_row(db_session):
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(_manifest()), published_by=None)
        await db.commit()

    async with db_session() as db:
        install_row = await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    assert install_row.installed_version == "1.0.0"
    assert install_row.registered_capability_names == ["plugin.queue-tools.queue_status"]
    assert registry.get("plugin.queue-tools.queue_status") is not None
    assert "handlers" in sandbox._sources["queue-tools"]


@pytest.mark.asyncio
async def test_install_unknown_version_raises_not_found(db_session):
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(_manifest()), published_by=None)
        await db.commit()

    async with db_session() as db:
        with pytest.raises(ResourceNotFoundException):
            await MarketplaceService.install(
                db, plugin_id="queue-tools", version="9.9.9", installed_by=None,
                sandbox=sandbox, registry=registry,
            )


@pytest.mark.asyncio
async def test_install_same_version_twice_raises_conflict(db_session):
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(_manifest()), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    async with db_session() as db:
        with pytest.raises(ConflictException):
            await MarketplaceService.install(
                db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
                sandbox=sandbox, registry=registry,
            )


@pytest.mark.asyncio
async def test_install_new_version_updates_in_place_and_unregisters_old_capability(db_session):
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(_manifest()), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    v2_manifest = _manifest(version="1.1.0")
    v2_manifest["capabilities"][0]["local_name"] = "queue_status_v2"
    v2_manifest["discord_commands"][0]["capability"] = "queue_status_v2"
    v2_manifest["dashboard_ui_slots"][0]["capability"] = "queue_status_v2"
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(v2_manifest), published_by=None)
        await db.commit()

    async with db_session() as db:
        install_row = await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.1.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    assert install_row.installed_version == "1.1.0"
    assert install_row.registered_capability_names == ["plugin.queue-tools.queue_status_v2"]
    with pytest.raises(CapabilityNotFoundError):
        registry.get("plugin.queue-tools.queue_status")
    assert registry.get("plugin.queue-tools.queue_status_v2") is not None

    async with db_session() as db:
        installed = await MarketplaceService.list_installed(db)
    assert len(installed) == 1  # single row updated in place, not a second row


@pytest.mark.asyncio
async def test_install_bad_permission_ref_raises_validation_and_leaves_nothing_registered(db_session):
    bad_manifest = _manifest()
    bad_manifest["capabilities"][0]["required_permission"] = "not.a.real.permission"
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})

    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(bad_manifest), published_by=None)
        await db.commit()

    async with db_session() as db:
        with pytest.raises(ValidationException):
            await MarketplaceService.install(
                db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
                sandbox=sandbox, registry=registry,
            )

    with pytest.raises(CapabilityNotFoundError):
        registry.get("plugin.queue-tools.queue_status")


@pytest.mark.asyncio
async def test_uninstall_removes_capability_and_install_row(db_session):
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(_manifest()), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    async with db_session() as db:
        await MarketplaceService.uninstall(db, plugin_id="queue-tools", sandbox=sandbox, registry=registry)
        await db.commit()

    with pytest.raises(CapabilityNotFoundError):
        registry.get("plugin.queue-tools.queue_status")
    assert "queue-tools" not in sandbox._sources

    async with db_session() as db:
        installed = await MarketplaceService.list_installed(db)
    assert installed == []


@pytest.mark.asyncio
async def test_uninstall_not_installed_raises_not_found(db_session):
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        with pytest.raises(ResourceNotFoundException):
            await MarketplaceService.uninstall(db, plugin_id="never-installed", sandbox=sandbox, registry=registry)


@pytest.mark.asyncio
async def test_discord_commands_lists_declared_commands_for_installed_plugins(db_session):
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(_manifest()), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    async with db_session() as db:
        commands = await MarketplaceService.discord_commands(db)

    assert len(commands) == 1
    assert commands[0].plugin_id == "queue-tools"
    assert commands[0].name == "queue"
    assert commands[0].capability_name == "plugin.queue-tools.queue_status"


@pytest.mark.asyncio
async def test_discord_commands_empty_when_nothing_installed(db_session):
    async with db_session() as db:
        commands = await MarketplaceService.discord_commands(db)
    assert commands == []


@pytest.mark.asyncio
async def test_dashboard_slots_lists_and_filters_by_slot(db_session):
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(_manifest()), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    async with db_session() as db:
        all_slots = await MarketplaceService.dashboard_slots(db)
        matching = await MarketplaceService.dashboard_slots(db, slot="sidebar.tools")
        other = await MarketplaceService.dashboard_slots(db, slot="sidebar.moderation")

    assert len(all_slots) == 1
    assert all_slots[0].capability_name == "plugin.queue-tools.queue_status"
    # Phase 10, Decision 7: _manifest() doesn't declare render_as, so it
    # must come through as None (falls back to dashboard-side inference),
    # not be silently dropped or default to some other value.
    assert all_slots[0].render_as is None
    assert len(matching) == 1
    assert other == []


@pytest.mark.asyncio
async def test_dashboard_slots_carries_render_as_when_declared(db_session):
    """Phase 10, Decision 7. Same flow as
    test_dashboard_slots_lists_and_filters_by_slot, but the manifest
    declares render_as explicitly — confirms it survives the
    publish -> install -> discovery round trip, not just manifest parsing
    in isolation."""
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    manifest = _manifest()
    manifest["dashboard_ui_slots"][0]["render_as"] = "stat_pair"

    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(manifest), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    async with db_session() as db:
        slots = await MarketplaceService.dashboard_slots(db)

    assert len(slots) == 1
    assert slots[0].render_as == "stat_pair"


# --------------------------------------------------------------------------
# Phase 10, Tier 3 — plugin-owned pages
# --------------------------------------------------------------------------


def _manifest_with_page(**page_overrides) -> dict:
    raw = _manifest()
    raw["page"] = {
        "nav_label": "Queue Tools",
        "nav_icon": "list",
        "widgets": [
            {"label": "Queue depth", "capability": "queue_status", "render_as": "stat_pair"}
        ],
    }
    raw["page"].update(page_overrides)
    return raw


async def _install_manifest(db_session, manifest: dict):
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(manifest), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id=manifest["plugin_id"], version=manifest["version"], installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()


@pytest.mark.asyncio
async def test_pages_empty_when_no_installed_plugin_declares_one(db_session):
    """Strictly opt-in: a plugin installed without `page` in its manifest
    contributes nothing to the nav list — not an entry with blank fields."""
    await _install_manifest(db_session, _manifest())
    async with db_session() as db:
        nav_entries = await MarketplaceService.pages(db)
    assert nav_entries == []


@pytest.mark.asyncio
async def test_pages_lists_nav_metadata_for_declaring_plugin(db_session):
    await _install_manifest(db_session, _manifest_with_page())
    async with db_session() as db:
        nav_entries = await MarketplaceService.pages(db)
    assert len(nav_entries) == 1
    assert nav_entries[0].plugin_id == "queue-tools"
    assert nav_entries[0].nav_label == "Queue Tools"
    assert nav_entries[0].nav_icon == "list"


@pytest.mark.asyncio
async def test_page_layout_resolves_widgets_with_fully_qualified_capability_names(db_session):
    await _install_manifest(db_session, _manifest_with_page())
    async with db_session() as db:
        layout = await MarketplaceService.page_layout(db, "queue-tools")
    assert layout.plugin_id == "queue-tools"
    assert layout.nav_label == "Queue Tools"
    assert len(layout.widgets) == 1
    assert layout.widgets[0].capability_name == "plugin.queue-tools.queue_status"
    assert layout.widgets[0].render_as == "stat_pair"


@pytest.mark.asyncio
async def test_page_layout_raises_not_found_for_uninstalled_plugin(db_session):
    async with db_session() as db:
        with pytest.raises(ResourceNotFoundException):
            await MarketplaceService.page_layout(db, "nonexistent-plugin")


@pytest.mark.asyncio
async def test_page_layout_raises_not_found_when_plugin_declares_no_page(db_session):
    """An installed plugin that never opted into a page must 404 the same
    way an uninstalled one does — not return an empty/placeholder layout."""
    await _install_manifest(db_session, _manifest())
    async with db_session() as db:
        with pytest.raises(ResourceNotFoundException):
            await MarketplaceService.page_layout(db, "queue-tools")


# --- Phase 10, Tier 2 (Decision 2 Option A) ------------------------------


def _manifest_with_config(**config_overrides) -> dict:
    raw = _manifest()
    raw["config_fields"] = [
        {
            "key": "auto_purge",
            "type": "boolean",
            "label": "Auto-purge stale entries",
            "default_value": False,
            **config_overrides,
        }
    ]
    return raw


@pytest.mark.asyncio
async def test_install_with_config_fields_registers_both_capabilities(db_session):
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    manifest = _manifest_with_config()
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(manifest), published_by=None)
        await db.commit()

    async with db_session() as db:
        install_row = await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    assert "plugin.queue-tools.config.set" in install_row.registered_capability_names
    assert "plugin.queue-tools.config.get" in install_row.registered_capability_names
    set_spec = registry.get("plugin.queue-tools.config.set")
    get_spec = registry.get("plugin.queue-tools.config.get")
    assert set_spec.required_permission == "plugin.queue-tools.config.write"
    assert get_spec.required_permission == "marketplace.install.view"
    assert set_spec.audited is True
    assert get_spec.audited is False


@pytest.mark.asyncio
async def test_install_with_config_fields_creates_permission_row(db_session):
    """The get-or-create Permission this needs is the actual point of
    Option A — without a real row, RBAC has nothing to grant an admin."""
    from sqlalchemy import select
    from models.permissions import Permission

    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    manifest = _manifest_with_config()
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(manifest), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    async with db_session() as db:
        perm = await db.scalar(
            select(Permission).where(Permission.permission_key == "plugin.queue-tools.config.write")
        )
        assert perm is not None


@pytest.mark.asyncio
async def test_install_with_no_config_fields_registers_no_config_capabilities(db_session):
    """The common case — most plugins don't declare config_fields — must
    stay a true no-op, not register empty/placeholder capabilities."""
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(_manifest()), published_by=None)
        await db.commit()
    async with db_session() as db:
        install_row = await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    assert not any(n.endswith(".config.set") or n.endswith(".config.get")
                    for n in install_row.registered_capability_names)


@pytest.mark.asyncio
async def test_config_set_writes_kv_and_get_reads_it_back(db_session):
    """Real round trip through the actual handlers, not a mock — this is
    Option A's whole point: the write path is genuine platform code, no
    sandbox involved."""
    from registry.context import CallContext

    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    manifest = _manifest_with_config()
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(manifest), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    async with db_session() as db:
        ctx = CallContext(
            actor_id="admin-key", actor_type="system", source="system",
            permissions=set(), is_superuser=True, db=db,
        )
        set_spec = registry.get("plugin.queue-tools.config.set")
        await set_spec.handler(ctx, set_spec.params_model(key="auto_purge", value=True))
        await db.commit()

    async with db_session() as db:
        ctx = CallContext(
            actor_id="admin-key", actor_type="system", source="system",
            permissions=set(), is_superuser=True, db=db,
        )
        get_spec = registry.get("plugin.queue-tools.config.get")
        result = await get_spec.handler(ctx, get_spec.params_model())

    assert result.values[0].key == "auto_purge"
    assert result.values[0].value is True


@pytest.mark.asyncio
async def test_config_get_falls_back_to_default_when_never_set(db_session):
    """A fresh install with a config field that's never been touched must
    surface the declared default, not an unset/null state."""
    from registry.context import CallContext

    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    manifest = _manifest_with_config(default_value=True)
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(manifest), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    async with db_session() as db:
        ctx = CallContext(
            actor_id="admin-key", actor_type="system", source="system",
            permissions=set(), is_superuser=True, db=db,
        )
        get_spec = registry.get("plugin.queue-tools.config.get")
        result = await get_spec.handler(ctx, get_spec.params_model())

    assert result.values[0].value is True


@pytest.mark.asyncio
async def test_config_set_rejects_undeclared_key(db_session):
    from registry.context import CallContext

    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    manifest = _manifest_with_config()
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(manifest), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    async with db_session() as db:
        ctx = CallContext(
            actor_id="admin-key", actor_type="system", source="system",
            permissions=set(), is_superuser=True, db=db,
        )
        set_spec = registry.get("plugin.queue-tools.config.set")
        with pytest.raises(ValueError):
            await set_spec.handler(ctx, set_spec.params_model(key="not_a_real_key", value=True))


@pytest.mark.asyncio
async def test_reinstall_same_plugin_does_not_duplicate_permission_row(db_session):
    """Idempotency check for _get_or_create_permission — the update path
    (installing a new version of an already-installed plugin) must not
    error or create a second Permission row for the same key."""
    from sqlalchemy import select
    from models.permissions import Permission

    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    manifest_v1 = _manifest_with_config()
    manifest_v2 = _manifest_with_config()
    manifest_v2["version"] = "1.1.0"

    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(manifest_v1), published_by=None)
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(manifest_v2), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.1.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    async with db_session() as db:
        result = await db.execute(
            select(Permission).where(Permission.permission_key == "plugin.queue-tools.config.write")
        )
        rows = result.scalars().all()
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_uninstall_removes_config_capabilities(db_session):
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    manifest = _manifest_with_config()
    async with db_session() as db:
        await MarketplaceService.publish_version(db, zip_bytes=_zip_for(manifest), published_by=None)
        await db.commit()
    async with db_session() as db:
        await MarketplaceService.install(
            db, plugin_id="queue-tools", version="1.0.0", installed_by=None,
            sandbox=sandbox, registry=registry,
        )
        await db.commit()

    async with db_session() as db:
        await MarketplaceService.uninstall(db, plugin_id="queue-tools", sandbox=sandbox, registry=registry)
        await db.commit()

    with pytest.raises(CapabilityNotFoundError):
        registry.get("plugin.queue-tools.config.set")
    with pytest.raises(CapabilityNotFoundError):
        registry.get("plugin.queue-tools.config.get")


@pytest.mark.asyncio
async def test_configurable_plugins_empty_when_no_installed_plugin_declares_config(db_session):
    """Mirrors test_pages_empty_when_no_installed_plugin_declares_one —
    the common case (no config_fields) must contribute nothing."""
    await _install_manifest(db_session, _manifest())
    async with db_session() as db:
        entries = await MarketplaceService.configurable_plugins(db)
    assert entries == []


@pytest.mark.asyncio
async def test_configurable_plugins_lists_declaring_plugin(db_session):
    await _install_manifest(db_session, _manifest_with_config())
    async with db_session() as db:
        entries = await MarketplaceService.configurable_plugins(db)
    assert len(entries) == 1
    assert entries[0].plugin_id == "queue-tools"
    assert entries[0].field_count == 1
