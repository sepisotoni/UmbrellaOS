"""
tests/registry/test_capabilities_identity.py — REST integration tests for
Phase 3's identity capabilities (API keys, MFA), through the real FastAPI
app, registry, and database.
"""
import pyotp
import pytest

from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_create_api_key_returns_plaintext_once(client):
    response = await client.post(
        "/api/v1/capabilities/identity.apikey.create/invoke",
        json={"name": "bot-key", "permissions": ["hosting.server.view"]},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["plaintext_key"].startswith("umbr_")


@pytest.mark.asyncio
async def test_list_api_keys_never_includes_plaintext(client):
    await client.post(
        "/api/v1/capabilities/identity.apikey.create/invoke",
        json={"name": "bot-key-2", "permissions": []},
        headers=ADMIN_HEADERS,
    )
    response = await client.post(
        "/api/v1/capabilities/identity.apikey.list/invoke", json={}, headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    for key in response.json():
        assert key["plaintext_key"] is None


@pytest.mark.asyncio
async def test_created_api_key_actually_authenticates_on_the_real_invoke_endpoint(client):
    create_response = await client.post(
        "/api/v1/capabilities/identity.apikey.create/invoke",
        json={"name": "real-auth-check", "permissions": []},
        headers=ADMIN_HEADERS,
    )
    plaintext = create_response.json()["plaintext_key"]

    whoami_response = await client.post(
        "/api/v1/capabilities/platform.system.whoami/invoke",
        json={},
        headers={"X-Api-Key": plaintext},
    )
    assert whoami_response.status_code == 200
    body = whoami_response.json()
    assert body["actor_type"] == "plugin"
    assert body["is_superuser"] is False


@pytest.mark.asyncio
async def test_revoked_api_key_can_no_longer_authenticate(client):
    create_response = await client.post(
        "/api/v1/capabilities/identity.apikey.create/invoke",
        json={"name": "revoke-check", "permissions": []},
        headers=ADMIN_HEADERS,
    )
    key_id = create_response.json()["id"]
    plaintext = create_response.json()["plaintext_key"]

    await client.post(
        "/api/v1/capabilities/identity.apikey.revoke/invoke",
        json={"api_key_id": key_id},
        headers=ADMIN_HEADERS,
    )

    whoami_response = await client.post(
        "/api/v1/capabilities/platform.system.whoami/invoke",
        json={},
        headers={"X-Api-Key": plaintext},
    )
    assert whoami_response.status_code == 401


@pytest.mark.asyncio
async def test_apikey_capabilities_denied_without_permission(client, db_session):
    headers = await session_headers_for_role(db_session, "member")
    response = await client.post(
        "/api/v1/capabilities/identity.apikey.create/invoke",
        json={"name": "denied-key", "permissions": []},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_mfa_enrollment_full_round_trip_via_rest(client, db_session):
    headers = await session_headers_for_role(db_session, "owner", suffix="-mfa")

    begin_response = await client.post(
        "/api/v1/capabilities/identity.mfa.begin_enrollment/invoke", json={}, headers=headers
    )
    assert begin_response.status_code == 200
    secret = begin_response.json()["secret"]

    code = pyotp.TOTP(secret).now()
    confirm_response = await client.post(
        "/api/v1/capabilities/identity.mfa.confirm_enrollment/invoke",
        json={"code": code},
        headers=headers,
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["enabled"] is True

    disable_response = await client.post(
        "/api/v1/capabilities/identity.mfa.disable/invoke", json={}, headers=headers
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["disabled"] is True


@pytest.mark.asyncio
async def test_mfa_confirm_with_wrong_code_returns_error(client, db_session):
    headers = await session_headers_for_role(db_session, "owner", suffix="-mfa-wrong")

    await client.post("/api/v1/capabilities/identity.mfa.begin_enrollment/invoke", json={}, headers=headers)
    response = await client.post(
        "/api/v1/capabilities/identity.mfa.confirm_enrollment/invoke",
        json={"code": "000000"},
        headers=headers,
    )
    assert response.status_code == 401
    assert response.json()["code"] == "MFA_ERROR"


@pytest.mark.asyncio
async def test_mfa_denied_for_admin_key_actor(client):
    """MFA is a personal setting for a real staff account — the admin-key
    bootstrap tier has no underlying User row to attach one to."""
    response = await client.post(
        "/api/v1/capabilities/identity.mfa.begin_enrollment/invoke", json={}, headers=ADMIN_HEADERS
    )
    assert response.status_code == 400
    assert response.json()["code"] == "MFA_ERROR"
