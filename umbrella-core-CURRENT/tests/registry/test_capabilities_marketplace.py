"""
tests/registry/test_capabilities_marketplace.py — REST integration tests
for Phase 7 item 3's marketplace listing/versioning/install-flow
capabilities, through the real FastAPI app, registry, and database.

`marketplace.install.*` capabilities operate on the process-wide
registry/sandbox singletons (registry.registry.registry /
services.plugins.runtime.plugin_sandbox), which — unlike the per-test
in-memory database — are NOT reset between tests. Each test that installs
a plugin therefore uses a plugin_id unique to that test (or uninstalls
what it installed before returning) so tests in this file don't collide
with each other via that shared global state.
"""
import base64
import io
import json
import zipfile

import pytest

from config import get_settings
from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.fixture(autouse=True)
def _plugin_storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "plugin_storage_root", str(tmp_path / "plugins"))
    yield


def _manifest(plugin_id: str, version: str = "1.0.0", local_name: str = "queue_status") -> dict:
    return {
        "schema_version": 1,
        "plugin_id": plugin_id,
        "name": "Queue Tools",
        "version": version,
        "author": "example-author",
        "description": "Queue status reporting.",
        "capabilities": [
            {
                "local_name": local_name,
                "summary": "Report current queue depth.",
                "entrypoint": "handlers:queue_status",
                "params": {},
                "result": {"queue_depth": {"type": "integer"}},
                "required_permission": None,
            }
        ],
        "discord_commands": [
            {"name": "queue", "description": "Show queue status", "capability": local_name}
        ],
        "dashboard_ui_slots": [
            {"slot": "sidebar.tools", "label": "Queue Status", "capability": local_name}
        ],
    }


def _zip_base64(manifest: dict) -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("plugin.json", json.dumps(manifest))
        zf.writestr("handlers.py", "def queue_status(params):\n    return {'queue_depth': 3}\n")
    return base64.b64encode(buf.getvalue()).decode()


async def _publish(client, plugin_id: str, version: str = "1.0.0", local_name: str = "queue_status"):
    return await client.post(
        "/api/v1/capabilities/marketplace.listing.publish/invoke",
        json={"zip_base64": _zip_base64(_manifest(plugin_id, version, local_name))},
        headers=ADMIN_HEADERS,
    )


@pytest.mark.asyncio
async def test_publish_listing_returns_version_and_hash(client):
    response = await _publish(client, "rest-publish-demo")
    assert response.status_code == 200
    body = response.json()
    assert body["plugin_id"] == "rest-publish-demo"
    assert body["version"] == "1.0.0"
    assert len(body["sha256_hash"]) == 64


@pytest.mark.asyncio
async def test_publish_duplicate_version_returns_409(client):
    await _publish(client, "rest-dup-demo")
    response = await _publish(client, "rest-dup-demo")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_publish_invalid_package_returns_422(client):
    response = await client.post(
        "/api/v1/capabilities/marketplace.listing.publish/invoke",
        json={"zip_base64": base64.b64encode(b"not a zip").decode()},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_publish_invalid_base64_returns_422(client):
    response = await client.post(
        "/api/v1/capabilities/marketplace.listing.publish/invoke",
        json={"zip_base64": "not-valid-base64!!!"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_listings_includes_published_plugin(client):
    await _publish(client, "rest-list-demo")
    response = await client.post(
        "/api/v1/capabilities/marketplace.listing.list/invoke", json={}, headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    plugin_ids = [listing["plugin_id"] for listing in response.json()]
    assert "rest-list-demo" in plugin_ids


@pytest.mark.asyncio
async def test_list_versions_returns_published_versions(client):
    await _publish(client, "rest-versions-demo", version="1.0.0")
    await _publish(client, "rest-versions-demo", version="1.1.0")
    response = await client.post(
        "/api/v1/capabilities/marketplace.listing.versions/invoke",
        json={"plugin_id": "rest-versions-demo"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    versions = [v["version"] for v in response.json()]
    assert versions == ["1.0.0", "1.1.0"]


@pytest.mark.asyncio
async def test_list_versions_unknown_plugin_returns_404(client):
    response = await client.post(
        "/api/v1/capabilities/marketplace.listing.versions/invoke",
        json={"plugin_id": "never-published-anywhere"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_install_then_list_installed(client):
    await _publish(client, "rest-install-demo")
    install_response = await client.post(
        "/api/v1/capabilities/marketplace.install.install/invoke",
        json={"plugin_id": "rest-install-demo", "version": "1.0.0"},
        headers=ADMIN_HEADERS,
    )
    assert install_response.status_code == 200
    body = install_response.json()
    assert body["installed_version"] == "1.0.0"
    assert body["registered_capability_names"] == ["plugin.rest-install-demo.queue_status"]

    list_response = await client.post(
        "/api/v1/capabilities/marketplace.install.list/invoke", json={}, headers=ADMIN_HEADERS
    )
    installed_ids = [i["plugin_id"] for i in list_response.json()]
    assert "rest-install-demo" in installed_ids

    # clean up so this plugin_id's global capability registration doesn't
    # linger for other tests in this file
    await client.post(
        "/api/v1/capabilities/marketplace.install.uninstall/invoke",
        json={"plugin_id": "rest-install-demo"},
        headers=ADMIN_HEADERS,
    )


@pytest.mark.asyncio
async def test_install_unknown_version_returns_404(client):
    await _publish(client, "rest-install-404-demo")
    response = await client.post(
        "/api/v1/capabilities/marketplace.install.install/invoke",
        json={"plugin_id": "rest-install-404-demo", "version": "9.9.9"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_install_same_version_twice_returns_409(client):
    await _publish(client, "rest-install-conflict-demo")
    await client.post(
        "/api/v1/capabilities/marketplace.install.install/invoke",
        json={"plugin_id": "rest-install-conflict-demo", "version": "1.0.0"},
        headers=ADMIN_HEADERS,
    )
    response = await client.post(
        "/api/v1/capabilities/marketplace.install.install/invoke",
        json={"plugin_id": "rest-install-conflict-demo", "version": "1.0.0"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 409

    await client.post(
        "/api/v1/capabilities/marketplace.install.uninstall/invoke",
        json={"plugin_id": "rest-install-conflict-demo"},
        headers=ADMIN_HEADERS,
    )


@pytest.mark.asyncio
async def test_install_new_version_updates_in_place(client):
    plugin_id = "rest-update-demo"
    await _publish(client, plugin_id, version="1.0.0", local_name="queue_status")
    await client.post(
        "/api/v1/capabilities/marketplace.install.install/invoke",
        json={"plugin_id": plugin_id, "version": "1.0.0"},
        headers=ADMIN_HEADERS,
    )
    await _publish(client, plugin_id, version="1.1.0", local_name="queue_status_v2")

    response = await client.post(
        "/api/v1/capabilities/marketplace.install.install/invoke",
        json={"plugin_id": plugin_id, "version": "1.1.0"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["installed_version"] == "1.1.0"
    assert body["registered_capability_names"] == [f"plugin.{plugin_id}.queue_status_v2"]

    list_response = await client.post(
        "/api/v1/capabilities/marketplace.install.list/invoke", json={}, headers=ADMIN_HEADERS
    )
    matching = [i for i in list_response.json() if i["plugin_id"] == plugin_id]
    assert len(matching) == 1  # updated in place, not a second install row

    await client.post(
        "/api/v1/capabilities/marketplace.install.uninstall/invoke",
        json={"plugin_id": plugin_id},
        headers=ADMIN_HEADERS,
    )


@pytest.mark.asyncio
async def test_uninstall_removes_from_installed_list(client):
    plugin_id = "rest-uninstall-demo"
    await _publish(client, plugin_id)
    await client.post(
        "/api/v1/capabilities/marketplace.install.install/invoke",
        json={"plugin_id": plugin_id, "version": "1.0.0"},
        headers=ADMIN_HEADERS,
    )

    response = await client.post(
        "/api/v1/capabilities/marketplace.install.uninstall/invoke",
        json={"plugin_id": plugin_id},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["uninstalled"] is True

    list_response = await client.post(
        "/api/v1/capabilities/marketplace.install.list/invoke", json={}, headers=ADMIN_HEADERS
    )
    installed_ids = [i["plugin_id"] for i in list_response.json()]
    assert plugin_id not in installed_ids


@pytest.mark.asyncio
async def test_uninstall_not_installed_returns_404(client):
    response = await client.post(
        "/api/v1/capabilities/marketplace.install.uninstall/invoke",
        json={"plugin_id": "never-installed-anywhere"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_discord_commands_and_dashboard_slots_reflect_installed_plugin(client):
    plugin_id = "rest-discovery-demo"
    await _publish(client, plugin_id)
    await client.post(
        "/api/v1/capabilities/marketplace.install.install/invoke",
        json={"plugin_id": plugin_id, "version": "1.0.0"},
        headers=ADMIN_HEADERS,
    )

    commands_response = await client.post(
        "/api/v1/capabilities/marketplace.install.discord_commands/invoke", json={}, headers=ADMIN_HEADERS
    )
    assert commands_response.status_code == 200
    matching_commands = [c for c in commands_response.json() if c["plugin_id"] == plugin_id]
    assert len(matching_commands) == 1
    assert matching_commands[0]["capability_name"] == f"plugin.{plugin_id}.queue_status"

    slots_response = await client.post(
        "/api/v1/capabilities/marketplace.install.dashboard_slots/invoke",
        json={"slot": "sidebar.tools"},
        headers=ADMIN_HEADERS,
    )
    assert slots_response.status_code == 200
    matching_slots = [s for s in slots_response.json() if s["plugin_id"] == plugin_id]
    assert len(matching_slots) == 1
    # Phase 10, Decision 7: the field must round-trip through the real REST
    # response, not just internal service objects — and be None (not
    # missing) when _manifest() doesn't declare it, so a dashboard client
    # can rely on the key always being present.
    assert matching_slots[0]["render_as"] is None

    other_slot_response = await client.post(
        "/api/v1/capabilities/marketplace.install.dashboard_slots/invoke",
        json={"slot": "sidebar.moderation"},
        headers=ADMIN_HEADERS,
    )
    assert all(s["plugin_id"] != plugin_id for s in other_slot_response.json())

    await client.post(
        "/api/v1/capabilities/marketplace.install.uninstall/invoke",
        json={"plugin_id": plugin_id},
        headers=ADMIN_HEADERS,
    )


@pytest.mark.asyncio
async def test_marketplace_capabilities_denied_without_permission(client, db_session):
    headers = await session_headers_for_role(db_session, "member")
    response = await client.post(
        "/api/v1/capabilities/marketplace.listing.publish/invoke",
        json={"zip_base64": _zip_base64(_manifest("rest-denied-demo"))},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_marketplace_view_permission_denied_for_moderator(client, db_session):
    """Same deliberate-exclusion posture documented for webhooks in
    services/roles_service.py — marketplace is an ops/platform concern,
    not a moderation one, so moderator doesn't get view access by
    default either."""
    headers = await session_headers_for_role(db_session, "moderator")
    response = await client.post(
        "/api/v1/capabilities/marketplace.listing.list/invoke", json={}, headers=headers
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------
# Phase 10, Tier 3 — plugin-owned pages
# --------------------------------------------------------------------------


def _manifest_with_page(plugin_id: str, version: str = "1.0.0", local_name: str = "queue_status") -> dict:
    raw = _manifest(plugin_id, version, local_name)
    raw["page"] = {
        "nav_label": "Queue Tools",
        "nav_icon": "list",
        "widgets": [{"label": "Queue depth", "capability": local_name, "render_as": "stat_pair"}],
    }
    return raw


async def _publish_with_page(client, plugin_id: str, version: str = "1.0.0", local_name: str = "queue_status"):
    return await client.post(
        "/api/v1/capabilities/marketplace.listing.publish/invoke",
        json={"zip_base64": _zip_base64(_manifest_with_page(plugin_id, version, local_name))},
        headers=ADMIN_HEADERS,
    )


@pytest.mark.asyncio
async def test_pages_and_page_layout_reflect_installed_plugin(client):
    plugin_id = "rest-page-demo"
    await _publish_with_page(client, plugin_id)
    await client.post(
        "/api/v1/capabilities/marketplace.install.install/invoke",
        json={"plugin_id": plugin_id, "version": "1.0.0"},
        headers=ADMIN_HEADERS,
    )

    pages_response = await client.post(
        "/api/v1/capabilities/marketplace.install.pages/invoke", json={}, headers=ADMIN_HEADERS
    )
    assert pages_response.status_code == 200
    matching_pages = [p for p in pages_response.json() if p["plugin_id"] == plugin_id]
    assert len(matching_pages) == 1
    assert matching_pages[0]["nav_label"] == "Queue Tools"
    assert matching_pages[0]["nav_icon"] == "list"

    layout_response = await client.post(
        "/api/v1/capabilities/marketplace.install.page_layout/invoke",
        json={"plugin_id": plugin_id},
        headers=ADMIN_HEADERS,
    )
    assert layout_response.status_code == 200
    layout_body = layout_response.json()
    assert layout_body["plugin_id"] == plugin_id
    assert len(layout_body["widgets"]) == 1
    assert layout_body["widgets"][0]["capability_name"] == f"plugin.{plugin_id}.queue_status"
    assert layout_body["widgets"][0]["render_as"] == "stat_pair"

    await client.post(
        "/api/v1/capabilities/marketplace.install.uninstall/invoke",
        json={"plugin_id": plugin_id},
        headers=ADMIN_HEADERS,
    )


@pytest.mark.asyncio
async def test_pages_excludes_installed_plugin_with_no_declared_page(client):
    """Strictly opt-in, confirmed at the REST layer too: a plugin
    installed via the plain `_manifest()` helper (no `page` key) must not
    show up in the nav list."""
    plugin_id = "rest-no-page-demo"
    await _publish(client, plugin_id)
    await client.post(
        "/api/v1/capabilities/marketplace.install.install/invoke",
        json={"plugin_id": plugin_id, "version": "1.0.0"},
        headers=ADMIN_HEADERS,
    )

    pages_response = await client.post(
        "/api/v1/capabilities/marketplace.install.pages/invoke", json={}, headers=ADMIN_HEADERS
    )
    assert all(p["plugin_id"] != plugin_id for p in pages_response.json())

    layout_response = await client.post(
        "/api/v1/capabilities/marketplace.install.page_layout/invoke",
        json={"plugin_id": plugin_id},
        headers=ADMIN_HEADERS,
    )
    assert layout_response.status_code == 404

    await client.post(
        "/api/v1/capabilities/marketplace.install.uninstall/invoke",
        json={"plugin_id": plugin_id},
        headers=ADMIN_HEADERS,
    )


@pytest.mark.asyncio
async def test_page_layout_404_for_never_installed_plugin(client):
    response = await client.post(
        "/api/v1/capabilities/marketplace.install.page_layout/invoke",
        json={"plugin_id": "never-installed-page-demo"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_pages_and_page_layout_denied_for_moderator(client, db_session):
    """Same view-permission posture as every other marketplace.install.*
    discovery capability — moderator doesn't get marketplace access."""
    headers = await session_headers_for_role(db_session, "moderator")
    pages_response = await client.post(
        "/api/v1/capabilities/marketplace.install.pages/invoke", json={}, headers=headers
    )
    assert pages_response.status_code == 403

    layout_response = await client.post(
        "/api/v1/capabilities/marketplace.install.page_layout/invoke",
        json={"plugin_id": "irrelevant"},
        headers=headers,
    )
    assert layout_response.status_code == 403


# --- Phase 10, Tier 2 (Decision 2 Option A) ------------------------------


def _manifest_with_config(plugin_id: str, version: str = "1.0.0") -> dict:
    manifest = _manifest(plugin_id, version)
    manifest["config_fields"] = [
        {"key": "auto_purge", "type": "boolean", "label": "Auto-purge stale entries", "default_value": False}
    ]
    return manifest


async def _publish_with_config(client, plugin_id: str, version: str = "1.0.0"):
    return await client.post(
        "/api/v1/capabilities/marketplace.listing.publish/invoke",
        json={"zip_base64": _zip_base64(_manifest_with_config(plugin_id, version))},
        headers=ADMIN_HEADERS,
    )


@pytest.mark.asyncio
async def test_config_set_and_get_round_trip_through_real_rest_api(client):
    """Full stack, real HTTP invoke calls, not the handler in isolation —
    admin-key tier exercises the success path end to end."""
    plugin_id = "rest-config-demo"
    await _publish_with_config(client, plugin_id)
    await client.post(
        "/api/v1/capabilities/marketplace.install.install/invoke",
        json={"plugin_id": plugin_id, "version": "1.0.0"},
        headers=ADMIN_HEADERS,
    )

    set_response = await client.post(
        f"/api/v1/capabilities/plugin.{plugin_id}.config.set/invoke",
        json={"key": "auto_purge", "value": True},
        headers=ADMIN_HEADERS,
    )
    assert set_response.status_code == 200
    assert set_response.json()["value"] is True

    get_response = await client.post(
        f"/api/v1/capabilities/plugin.{plugin_id}.config.get/invoke",
        json={},
        headers=ADMIN_HEADERS,
    )
    assert get_response.status_code == 200
    values = get_response.json()["values"]
    assert values[0]["key"] == "auto_purge"
    assert values[0]["value"] is True

    await client.post(
        "/api/v1/capabilities/marketplace.install.uninstall/invoke",
        json={"plugin_id": plugin_id},
        headers=ADMIN_HEADERS,
    )


@pytest.mark.asyncio
async def test_config_set_denied_for_member_without_grant(client, db_session):
    """The actual point of Option A: a plain member role, which has no
    grant for this specific plugin's config.write permission, must be
    rejected — not merely 'not an admin', genuinely lacking this one
    per-plugin permission specifically."""
    plugin_id = "rest-config-denied-demo"
    await _publish_with_config(client, plugin_id)
    await client.post(
        "/api/v1/capabilities/marketplace.install.install/invoke",
        json={"plugin_id": plugin_id, "version": "1.0.0"},
        headers=ADMIN_HEADERS,
    )

    headers = await session_headers_for_role(db_session, "member")
    response = await client.post(
        f"/api/v1/capabilities/plugin.{plugin_id}.config.set/invoke",
        json={"key": "auto_purge", "value": True},
        headers=headers,
    )
    assert response.status_code == 403

    await client.post(
        "/api/v1/capabilities/marketplace.install.uninstall/invoke",
        json={"plugin_id": plugin_id},
        headers=ADMIN_HEADERS,
    )


@pytest.mark.asyncio
async def test_config_get_allowed_for_member_but_config_set_denied(client, db_session):
    """Read/write asymmetry, confirmed at the REST layer with the same
    member session for both calls: config.get uses marketplace.install.view
    (which 'member' does hold per DEFAULT_PERMISSIONS' appeals.view-only
    grant... — actually verified directly below rather than assumed), while
    config.set uses the narrow per-plugin permission nothing grants by
    default. This is the one concrete behavioral difference Option A's
    write-up promised over Option B."""
    plugin_id = "rest-config-asymmetry-demo"
    await _publish_with_config(client, plugin_id)
    await client.post(
        "/api/v1/capabilities/marketplace.install.install/invoke",
        json={"plugin_id": plugin_id, "version": "1.0.0"},
        headers=ADMIN_HEADERS,
    )

    headers = await session_headers_for_role(db_session, "member")
    get_response = await client.post(
        f"/api/v1/capabilities/plugin.{plugin_id}.config.get/invoke",
        json={},
        headers=headers,
    )
    set_response = await client.post(
        f"/api/v1/capabilities/plugin.{plugin_id}.config.set/invoke",
        json={"key": "auto_purge", "value": True},
        headers=headers,
    )
    # 'member' has no marketplace.install.view grant either per
    # DEFAULT_PERMISSIONS (roles_service.py) — so the real, honest
    # assertion here is that .set is *at least as restrictive* as .get,
    # not that .get specifically succeeds for a role with no marketplace
    # access at all. Both currently 403 for 'member'; the meaningful claim
    # is the permission keys differ (already proven at the CapabilitySpec
    # level in test_marketplace_service.py), and that a role granted only
    # marketplace.install.view (not this plugin's config.write) can read
    # but not write — exercised below with a purpose-built role grant.
    assert set_response.status_code == 403
    assert get_response.status_code in (200, 403)

    # Purpose-built check: grant only marketplace.install.view directly to
    # the member role and confirm .get now succeeds while .set still 403s.
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from models.permissions import Permission, Role

    async with db_session() as db:
        role = await db.scalar(
            select(Role).where(Role.name == "member").options(selectinload(Role.permissions))
        )
        perm = await db.scalar(
            select(Permission).where(Permission.permission_key == "marketplace.install.view")
        )
        role.permissions.append(perm)
        await db.commit()

    get_response_2 = await client.post(
        f"/api/v1/capabilities/plugin.{plugin_id}.config.get/invoke",
        json={},
        headers=headers,
    )
    set_response_2 = await client.post(
        f"/api/v1/capabilities/plugin.{plugin_id}.config.set/invoke",
        json={"key": "auto_purge", "value": True},
        headers=headers,
    )
    assert get_response_2.status_code == 200
    assert set_response_2.status_code == 403

    await client.post(
        "/api/v1/capabilities/marketplace.install.uninstall/invoke",
        json={"plugin_id": plugin_id},
        headers=ADMIN_HEADERS,
    )
