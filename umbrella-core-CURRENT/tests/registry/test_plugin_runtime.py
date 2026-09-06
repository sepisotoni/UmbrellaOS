"""tests/registry/test_plugin_runtime.py — reload_installed_plugins:
restoring already-installed plugins' capabilities into a fresh
CapabilityRegistry/ProcessSandbox at process startup, from PluginInstall
rows alone.
"""
import io
import json
import zipfile

import pytest

from config import get_settings
from models.marketplace import PluginInstall
from registry.registry import CapabilityRegistry
from services.plugins.runtime import reload_installed_plugins
from services.plugins.sandbox import ProcessSandbox
from services.plugins.source_store import compute_sha256, store_zip


@pytest.fixture(autouse=True)
def _plugin_storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "plugin_storage_root", str(tmp_path / "plugins"))
    yield


def _manifest_dict(plugin_id="queue-tools", version="1.0.0") -> dict:
    return {
        "schema_version": 1,
        "plugin_id": plugin_id,
        "name": "Queue Tools",
        "version": version,
        "author": "example-author",
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
    }


def _zip_for(manifest: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("plugin.json", json.dumps(manifest))
        zf.writestr("handlers.py", "def queue_status(params):\n    return {'queue_depth': 3}\n")
    return buf.getvalue()


async def _seed_install(db_session, plugin_id="queue-tools", version="1.0.0") -> None:
    manifest = _manifest_dict(plugin_id, version)
    zip_bytes = _zip_for(manifest)
    relative_path, sha = store_zip(plugin_id, version, zip_bytes)
    async with db_session() as db:
        db.add(
            PluginInstall(
                plugin_id=plugin_id,
                installed_version=version,
                manifest_json=json.dumps(manifest),
                zip_path=relative_path,
                sha256_hash=sha,
                registered_capability_names=[f"plugin.{plugin_id}.queue_status"],
            )
        )
        await db.commit()


@pytest.mark.asyncio
async def test_reload_registers_installed_plugin_capability(db_session):
    await _seed_install(db_session)
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})

    async with db_session() as db:
        registered = await reload_installed_plugins(db, sandbox=sandbox, registry=registry)

    assert registered == ["plugin.queue-tools.queue_status"]
    assert registry.get("plugin.queue-tools.queue_status") is not None
    assert "handlers" in sandbox._sources["queue-tools"]


@pytest.mark.asyncio
async def test_reload_with_no_installs_returns_empty_list(db_session):
    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        registered = await reload_installed_plugins(db, sandbox=sandbox, registry=registry)
    assert registered == []


@pytest.mark.asyncio
async def test_reload_skips_install_with_tampered_hash_but_continues(db_session):
    """A corrupted/tampered install must not take the whole startup down
    — it's logged and skipped, and other installs still load."""
    await _seed_install(db_session, plugin_id="broken-plugin")
    await _seed_install(db_session, plugin_id="queue-tools")

    async with db_session() as db:
        result = await db.execute(
            __import__("sqlalchemy").select(PluginInstall).where(PluginInstall.plugin_id == "broken-plugin")
        )
        install = result.scalar_one()
        install.sha256_hash = "0" * 64
        await db.commit()

    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        registered = await reload_installed_plugins(db, sandbox=sandbox, registry=registry)

    assert registered == ["plugin.queue-tools.queue_status"]
    with pytest.raises(Exception):
        registry.get("plugin.broken-plugin.queue_status")


@pytest.mark.asyncio
async def test_reload_skips_install_with_missing_zip_file(db_session, tmp_path):
    await _seed_install(db_session, plugin_id="queue-tools")
    # Delete the stored zip out from under the install row entirely.
    for f in tmp_path.rglob("*.zip"):
        f.unlink()

    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        registered = await reload_installed_plugins(db, sandbox=sandbox, registry=registry)

    assert registered == []


@pytest.mark.asyncio
async def test_reload_restores_multiple_installed_plugins(db_session):
    await _seed_install(db_session, plugin_id="queue-tools")
    await _seed_install(db_session, plugin_id="another-plugin")

    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        registered = await reload_installed_plugins(db, sandbox=sandbox, registry=registry)

    assert set(registered) == {
        "plugin.queue-tools.queue_status",
        "plugin.another-plugin.queue_status",
    }
    assert "queue-tools" in sandbox._sources
    assert "another-plugin" in sandbox._sources


def _manifest_with_unknown_permission(plugin_id="stale-perm-plugin", version="1.0.0") -> dict:
    manifest = _manifest_dict(plugin_id, version)
    manifest["capabilities"][0]["required_permission"] = "this.permission.does.not.exist"
    return manifest


async def _seed_install_with_manifest(db_session, manifest: dict) -> None:
    """Same as _seed_install, but takes a caller-built manifest dict instead
    of always using the default queue_status one — needed to construct a
    manifest with a required_permission that won't validate."""
    zip_bytes = _zip_for(manifest)
    plugin_id = manifest["plugin_id"]
    version = manifest["version"]
    relative_path, sha = store_zip(plugin_id, version, zip_bytes)
    async with db_session() as db:
        db.add(
            PluginInstall(
                plugin_id=plugin_id,
                installed_version=version,
                manifest_json=json.dumps(manifest),
                zip_path=relative_path,
                sha256_hash=sha,
                registered_capability_names=[f"plugin.{plugin_id}.queue_status"],
            )
        )
        await db.commit()


@pytest.mark.asyncio
async def test_reload_skips_install_referencing_a_permission_that_no_longer_exists(db_session):
    """FIX ([PLUGIN] subsystem audit): register_plugin_capabilities raises
    PluginRegistrationError (not ManifestValidationError/PluginPackageError)
    when an installed plugin's manifest references a required_permission
    that isn't a known permission key — a real, plausible scenario if a
    permission is renamed/removed after the plugin was installed against
    the old set. This exception type wasn't caught before this fix, so it
    would have crashed the entire app's startup instead of just skipping
    this one plugin, contradicting this function's own stated design goal
    (verified by reverting the runtime.py fix locally and confirming this
    exact test fails with an unhandled PluginRegistrationError, before
    re-applying the fix)."""
    await _seed_install_with_manifest(db_session, _manifest_with_unknown_permission())
    await _seed_install(db_session, plugin_id="queue-tools")

    registry = CapabilityRegistry()
    sandbox = ProcessSandbox(sources={})
    async with db_session() as db:
        # Must not raise — the whole point of this fix.
        registered = await reload_installed_plugins(db, sandbox=sandbox, registry=registry)

    # The valid plugin still loads; the stale one is skipped, not crashed on.
    assert registered == ["plugin.queue-tools.queue_status"]
    with pytest.raises(Exception):
        registry.get("plugin.stale-perm-plugin.queue_status")
