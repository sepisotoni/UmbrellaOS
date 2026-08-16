"""tests/test_dev_auth.py — tests for the DEBUG-gated dev session-mint
capability (capabilities/dev_auth.py). Same shape as
tests/registry/test_capabilities_dashboard_layout.py: REST integration
tests through the real FastAPI app, registry, and database, using the
project's shared `client`/`db_session` fixtures (in-memory SQLite,
seeded roles/permissions).

The one test that matters most here is the gating test — everything else
is normal behavioral coverage.
"""
import pytest

from config import get_settings
from tests.conftest import ADMIN_HEADERS


@pytest.mark.asyncio
async def test_unreachable_when_debug_is_false(client, monkeypatch):
    """The core safety property this capability exists to guarantee: with
    settings.debug at its real-world default (False), this capability
    must be a hard no-op — a 404, indistinguishable from a capability
    that doesn't exist, not a 403 that would confirm a dev backdoor is
    present but locked. This is the single most important test in this
    file."""
    settings = get_settings()
    monkeypatch.setattr(settings, "debug", False)

    response = await client.post(
        "/api/v1/capabilities/auth.dev.mint_test_session/invoke",
        json={"role": "owner"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mints_a_usable_session_when_debug_is_true(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "debug", True)

    mint_response = await client.post(
        "/api/v1/capabilities/auth.dev.mint_test_session/invoke",
        json={"role": "owner", "label": "broad"},
        headers=ADMIN_HEADERS,
    )
    assert mint_response.status_code == 200
    body = mint_response.json()
    assert body["role"] == "owner"
    assert body["extra_permissions"] == []
    assert body["expires_in"] > 0
    token = body["token"]
    assert token

    # The minted token must actually work as a real session — the whole
    # point of this capability is producing something /auth/me and every
    # other session-authenticated route accepts, not just a database row.
    me_response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "dev-test:broad"


@pytest.mark.asyncio
async def test_narrow_role_grants_only_its_extra_permission(client, monkeypatch):
    """The exact scenario Task B's test pass needs: a role with
    marketplace.install.view but not .manage. No DEFAULT_ROLES entry has
    that combination (services/roles_service.py) — this is only mintable
    via extra_permissions on top of a role that has neither."""
    settings = get_settings()
    monkeypatch.setattr(settings, "debug", True)

    mint_response = await client.post(
        "/api/v1/capabilities/auth.dev.mint_test_session/invoke",
        json={
            "role": "member",
            "extra_permissions": ["marketplace.install.view"],
            "label": "narrow",
        },
        headers=ADMIN_HEADERS,
    )
    assert mint_response.status_code == 200
    token = mint_response.json()["token"]

    me_response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    permissions = me_response.json()["permissions"]
    assert "marketplace.install.view" in permissions
    assert "marketplace.install.manage" not in permissions


@pytest.mark.asyncio
async def test_unknown_role_is_rejected(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "debug", True)

    response = await client.post(
        "/api/v1/capabilities/auth.dev.mint_test_session/invoke",
        json={"role": "not-a-real-role"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unknown_extra_permission_is_rejected(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "debug", True)

    response = await client.post(
        "/api/v1/capabilities/auth.dev.mint_test_session/invoke",
        json={"role": "owner", "extra_permissions": ["not.a.real.permission"]},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reinvoking_same_label_reuses_the_dev_user_not_duplicates(client, monkeypatch):
    """Re-invoking with the same label should update the existing
    synthetic dev user's role/extra_permissions in place, not accumulate
    a fresh dev user per call — see mint_test_session's docstring."""
    settings = get_settings()
    monkeypatch.setattr(settings, "debug", True)

    first = await client.post(
        "/api/v1/capabilities/auth.dev.mint_test_session/invoke",
        json={"role": "helper", "label": "reused"},
        headers=ADMIN_HEADERS,
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/capabilities/auth.dev.mint_test_session/invoke",
        json={"role": "owner", "label": "reused"},
        headers=ADMIN_HEADERS,
    )
    assert second.status_code == 200

    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {second.json()['token']}"},
    )
    assert me_response.json()["role"] == "owner"

    users_response = await client.get("/api/v1/auth", headers=ADMIN_HEADERS)
    dev_users = [u for u in users_response.json() if u["username"] == "dev-test:reused"]
    assert len(dev_users) == 1
