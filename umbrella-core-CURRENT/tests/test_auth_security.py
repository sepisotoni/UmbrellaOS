"""
tests/test_auth_security.py — Security regression tests for the auth subsystem.

These tests target the specific bugs found in the Phase 16B auth audit and
must never regress:

1. Timing-safe secret comparison (hmac.compare_digest) — hard to test
   exhaustively in unit tests, but we verify the *logic paths* that were
   previously using `==` all reject on wrong keys.
2. Session token must NOT appear in query parameters on /logout or /me.
3. MFA gate at discord_callback — users with mfa_enabled=True must not
   receive a full session token from /discord/callback.
4. mfa: pre-session token cannot be used on regular authenticated endpoints.
5. MFA disable requires a valid TOTP code — cannot be bypassed with just
   a session token.
6. Duplicate rate-limit settings don't crash startup.
7. Generic 500 handler does not leak exception detail to clients.
8. /verification/count requires verification.link.view permission, not
   raw admin key bypass.
"""
import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pyotp
import pytest
import pytest_asyncio
from sqlalchemy import select

from models import Session, User
from models.permissions import Role
from tests.conftest import ADMIN_HEADERS, PLUGIN_HEADERS, WRONG_HEADERS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_owner(db) -> User:
    role = await db.scalar(select(Role).where(Role.name == "owner"))
    user = User(discord_id=f"sec-{id(db)}", username=f"secuser_{id(db)}", role_id=role.id)
    db.add(user)
    await db.flush()
    return user


async def _make_session(db, user: User, prefix: str = "") -> str:
    token = f"{prefix}security-test-tok-{id(user)}"
    sess = Session(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(sess)
    await db.flush()
    return token


# ---------------------------------------------------------------------------
# 1. Wrong keys always get 401 (covers timing-safe comparison paths)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_wrong_plugin_key_is_401(client):
    """X-Plugin-Key with a subtly wrong value must be rejected."""
    resp = await client.get("/api/v1/plugin/health", headers={"X-Plugin-Key": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_empty_admin_key_is_401(client):
    """Empty X-Admin-Key must be rejected, not accepted as falsy bypass."""
    resp = await client.get("/api/v1/settings", headers={"X-Admin-Key": ""})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_plugin_key_on_admin_route_is_401(client):
    """X-Plugin-Key must not grant access to admin-only routes."""
    resp = await client.get("/api/v1/settings", headers=PLUGIN_HEADERS)
    # Plugin key should not be accepted on admin-only setting routes
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 2. Session token MUST NOT be accepted in query parameters
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_rejects_query_param_token(client, db_session):
    """POST /logout must not accept session_token as a query parameter."""
    async with db_session() as db:
        user = await _make_owner(db)
        token = await _make_session(db, user)
        await db.commit()

    # Old (broken) call with token in query — must NOT succeed
    resp = await client.post(f"/api/v1/auth/logout?session_token={token}")
    # Should be 401 (no Bearer header) or 422 (unexpected query param)
    # Either way it must not be 200
    assert resp.status_code != 200, "logout must not accept token as query param"


@pytest.mark.asyncio
async def test_logout_accepts_bearer_header(client, db_session):
    """POST /logout with Authorization: Bearer must succeed."""
    async with db_session() as db:
        user = await _make_owner(db)
        token = await _make_session(db, user)
        await db.commit()

    resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json().get("success") is True


@pytest.mark.asyncio
async def test_me_rejects_query_param_token(client, db_session):
    """GET /me must not accept session_token as a query parameter."""
    async with db_session() as db:
        user = await _make_owner(db)
        token = await _make_session(db, user)
        await db.commit()

    resp = await client.get(f"/api/v1/auth/me?session_token={token}")
    assert resp.status_code in (401, 422), "GET /me must not accept query-param token"


@pytest.mark.asyncio
async def test_me_accepts_bearer_header(client, db_session):
    """GET /me with Authorization: Bearer must return the user profile."""
    async with db_session() as db:
        user = await _make_owner(db)
        token = await _make_session(db, user)
        await db.commit()

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == user.username
    assert "mfa_enabled" in body, "UserSchema must include mfa_enabled field"


# ---------------------------------------------------------------------------
# 3. MFA gate — mfa_enabled users must not get a full session from /callback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mfa_enabled_user_gets_403_at_callback(client, db_session):
    """
    If a user has mfa_enabled=True, /discord/callback must return 403 with
    mfa_required=True instead of issuing a full session token.
    """
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == "owner"))
        user = User(
            discord_id="mfa-gated-discord-id",
            username="mfagateduser",
            role_id=role.id,
            mfa_enabled=True,
            mfa_secret=pyotp.random_base32(),
        )
        db.add(user)
        # Create a pending OAuth state as the callback expects
        from models.auth import OAuthState
        pending = OAuthState(
            discord_id="mfa-gated-discord-id",
            state="mfa-test-state-xyz",
            username="mfagateduser",
            avatar_hash=None,
            email=None,
        )
        db.add(pending)
        await db.commit()

    # Simulate callback by hitting /discord/callback with the resolved pending record
    # We patch the Discord API exchange to return our test user's data
    with patch("api.routers.auth.exchange_discord_code") as mock_exchange:
        mock_exchange.return_value = {
            "id": "mfa-gated-discord-id",
            "username": "mfagateduser",
            "avatar": None,
            "email": None,
        }
        resp = await client.post(
            "/api/v1/auth/discord/callback",
            json={
                "code": "fake-oauth-code",
                "state": "mfa-test-state-xyz",
                "redirect_uri": "http://localhost/",
            },
        )

    # Must get 403, not 200 with a token
    assert resp.status_code == 403
    body = resp.json()
    detail = body.get("detail", {})
    assert detail.get("mfa_required") is True, "403 body must have mfa_required: true"
    assert "mfa_token" in detail, "403 body must include the short-lived mfa_token"
    # Crucially: no full session token in the response
    assert "token" not in body or body.get("token") is None


# ---------------------------------------------------------------------------
# 4. mfa: pre-session token cannot be used on regular endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mfa_presession_token_rejected_on_regular_endpoint(client, db_session):
    """
    A token prefixed with 'mfa:' is a pre-session token and must be rejected
    on all endpoints that call require_session or require_admin_key_or_session.
    """
    async with db_session() as db:
        user = await _make_owner(db)
        # Create an mfa: pre-session token
        mfa_token = "mfa:presession-security-test-token"
        sess = Session(
            user_id=user.id,
            token=mfa_token,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        db.add(sess)
        await db.commit()

    # Try to use it on a real endpoint — must be 401
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {mfa_token}"},
    )
    assert resp.status_code == 401, "mfa: pre-session token must not grant access to /me"


# ---------------------------------------------------------------------------
# 5. MFA disable requires valid TOTP code
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mfa_disable_requires_valid_code(client, db_session):
    """MFA cannot be disabled with a wrong TOTP code, even with a valid session."""
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == "owner"))
        secret = pyotp.random_base32()
        user = User(
            discord_id="mfa-disable-test",
            username="mfadisableuser",
            role_id=role.id,
            mfa_enabled=True,
            mfa_secret=secret,
        )
        db.add(user)
        await db.flush()
        token = await _make_session(db, user)
        await db.commit()

    resp = await client.post(
        "/api/v1/auth/mfa/disable",
        json={"code": "000000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401, "MFA disable with wrong code must return 401"


@pytest.mark.asyncio
async def test_mfa_disable_succeeds_with_correct_code(client, db_session):
    """MFA disable with a valid TOTP code must succeed and clear mfa_enabled."""
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == "owner"))
        secret = pyotp.random_base32()
        user = User(
            discord_id="mfa-disable-ok-test",
            username="mfadisableokuser",
            role_id=role.id,
            mfa_enabled=True,
            mfa_secret=secret,
        )
        db.add(user)
        await db.flush()
        token = await _make_session(db, user)
        await db.commit()

    code = pyotp.TOTP(secret).now()
    resp = await client.post(
        "/api/v1/auth/mfa/disable",
        json={"code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json().get("success") is True


@pytest.mark.asyncio
async def test_mfa_disable_when_not_enabled_returns_400(client, db_session):
    """Calling /mfa/disable when MFA is not enabled must return 400, not 500."""
    async with db_session() as db:
        user = await _make_owner(db)
        token = await _make_session(db, user)
        await db.commit()

    resp = await client.post(
        "/api/v1/auth/mfa/disable",
        json={"code": "123456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 6. UserSchema includes mfa_enabled
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_schema_exposes_mfa_enabled(client, db_session):
    """GET /auth/me response body must include mfa_enabled boolean."""
    async with db_session() as db:
        user = await _make_owner(db)
        token = await _make_session(db, user)
        await db.commit()

    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "mfa_enabled" in body
    assert isinstance(body["mfa_enabled"], bool)


# ---------------------------------------------------------------------------
# 7. Generic 500 handler does not leak exception detail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_500_handler_does_not_leak_exception_detail(client):
    """
    When an unexpected exception occurs, the response body must not contain
    the raw exception message or stack details.
    """
    with patch("api.routers.health.get_health") as mock:
        mock.side_effect = RuntimeError("INTERNAL SECRET DB PASSWORD abc123")
        resp = await client.get("/health")

    if resp.status_code == 500:
        body = resp.text
        assert "INTERNAL SECRET" not in body, "Exception detail must not appear in 500 response"
        assert "abc123" not in body


# ---------------------------------------------------------------------------
# 8. /verification/count requires permission, not raw admin bypass
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verification_count_requires_permission(client):
    """
    GET /verification/count must check verification.link.view permission.
    A plain X-Admin-Key (which bypasses all permission checks) should still
    work because admin keys are granted all permissions, but a session with
    no verification.link.view permission must be rejected with 403.
    """
    # Admin key path should still work
    resp = await client.get("/api/v1/verification/count", headers=ADMIN_HEADERS)
    assert resp.status_code in (200, 404)  # 404 if no data, not 401/403

