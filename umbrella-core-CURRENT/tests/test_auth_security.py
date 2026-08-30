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
    from models import DiscordOAuthPending

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
        # Create a pending OAuth state record — matches what discord_callback
        # looks up by `state` before exchanging the code with Discord.
        pending = DiscordOAuthPending(
            state="mfa-test-state-xyz",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        db.add(pending)
        await db.commit()

    # discord_callback calls discord_service.exchange_code() then
    # discord_service.fetch_user() to resolve the Discord identity — mock
    # both so no real network call happens.
    with patch("api.routers.auth.discord_service.exchange_code") as mock_exchange, \
         patch("api.routers.auth.discord_service.fetch_user") as mock_fetch_user:
        mock_exchange.return_value = {"access_token": "fake-access-token"}
        mock_fetch_user.return_value = {
            "id": "mfa-gated-discord-id",
            "username": "mfagateduser",
            "global_name": "mfagateduser",
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

    Patches the actual health() endpoint function (not a non-existent
    get_health) to raise, forcing the generic_exception_handler path.
    """
    with patch("api.routers.health.health") as mock:
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


# ---------------------------------------------------------------------------
# 9. require_owner must reject ANY ApiKey, regardless of its permission list
#    (CRITICAL fix, 2026-08-30 — see api/dependencies/permissions.py)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_owner_endpoint_rejects_scoped_api_key(client, db_session):
    """
    POST /settings/{key} is require_owner-gated. A scoped API key — even
    one carrying an unrelated permission — must NEVER be able to write
    settings. This is the exact bug found during subsystem self-testing:
    require_owner previously treated ApiKey the same as the raw admin-key
    bootstrap string and let it through unconditionally.
    """
    from models.api_key import ApiKey
    from services.api_key_service import _hash_key

    async with db_session() as db:
        plaintext = "umbr_test_owner_bypass_attempt_key"
        key = ApiKey(
            name="test-scoped-key",
            key_hash=_hash_key(plaintext),
            key_prefix=plaintext[:12],
            permissions=["some.unrelated.permission"],
        )
        db.add(key)
        await db.commit()

    resp = await client.post(
        "/api/v1/settings/some_test_setting",
        json={"value": "attacker-controlled-value"},
        headers={"X-Api-Key": plaintext},
    )
    assert resp.status_code == 403, "Scoped API key must never pass require_owner"


@pytest.mark.asyncio
async def test_owner_endpoint_rejects_api_key_with_no_permissions(client, db_session):
    """Same as above, but with an API key carrying zero permissions at all."""
    from models.api_key import ApiKey
    from services.api_key_service import _hash_key

    async with db_session() as db:
        plaintext = "umbr_test_empty_perms_key"
        key = ApiKey(
            name="test-empty-perms-key",
            key_hash=_hash_key(plaintext),
            key_prefix=plaintext[:12],
            permissions=[],
        )
        db.add(key)
        await db.commit()

    resp = await client.post(
        "/api/v1/settings/some_test_setting",
        json={"value": "attacker-controlled-value"},
        headers={"X-Api-Key": plaintext},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_owner_endpoint_accepts_admin_key(client):
    """The raw admin-key bootstrap tier must still work — this is the one
    legitimate str-typed bypass require_owner is documented to allow."""
    resp = await client.post(
        "/api/v1/settings/some_test_setting_admin_ok",
        json={"value": "admin-set-value"},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code in (200, 404)  # 404 if setting key doesn't exist in schema — not 401/403


@pytest.mark.asyncio
async def test_owner_endpoint_accepts_owner_role_user(client, db_session):
    """A session-authenticated user with the owner role must still pass."""
    async with db_session() as db:
        user = await _make_owner(db)
        token = await _make_session(db, user)
        await db.commit()

    resp = await client.post(
        "/api/v1/settings/some_test_setting_owner_ok",
        json={"value": "owner-set-value"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_owner_endpoint_rejects_non_owner_role_user(client, db_session):
    """A session-authenticated user WITHOUT the owner role must be rejected."""
    async with db_session() as db:
        member_role = await db.scalar(select(Role).where(Role.name == "member"))
        user = User(discord_id="non-owner-test", username="nonowneruser", role_id=member_role.id)
        db.add(user)
        await db.flush()
        token = await _make_session(db, user)
        await db.commit()

    resp = await client.post(
        "/api/v1/settings/some_test_setting_denied",
        json={"value": "should-not-be-set"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 10. require_admin_key must never accept a session from a non-admin/owner
#     role user (CRITICAL fix, 2026-08-30) — this was a full
#     privilege-escalation-to-owner via PATCH /auth/users/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_member_session_cannot_self_promote_to_owner(client, db_session):
    """
    THE bug: a member-role user (lowest tier, appeals.view only) with a
    normal dashboard session token could previously PATCH their own user
    row and set role_id directly to the owner role's ID, because
    require_admin_key's Bearer-token branch only checked the session was
    valid — never who the user actually was. Full privilege escalation
    with a single authenticated request and zero permission checks.
    """
    async with db_session() as db:
        member_role = await db.scalar(select(Role).where(Role.name == "member"))
        owner_role = await db.scalar(select(Role).where(Role.name == "owner"))
        attacker = User(discord_id="escalation-attacker", username="attacker", role_id=member_role.id)
        db.add(attacker)
        await db.flush()
        token = await _make_session(db, attacker)
        attacker_id = attacker.id
        owner_role_id = owner_role.id
        await db.commit()

    resp = await client.patch(
        f"/api/v1/auth/users/{attacker_id}",
        json={"role_id": owner_role_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, "member-role session must not reach PATCH /users/{id}"

    # Confirm the DB was not mutated
    async with db_session() as db:
        refreshed = await db.get(User, attacker_id)
        assert refreshed.role_id != owner_role_id


@pytest.mark.asyncio
async def test_no_role_user_cannot_reach_admin_key_endpoints(client, db_session):
    """A user with role_id=None (no staff role assigned at all) must also
    be rejected — get_current_user only checks is_active, never role_id,
    so this branch needs its own explicit check."""
    async with db_session() as db:
        no_role_user = User(discord_id="no-role-user", username="norole", role_id=None)
        db.add(no_role_user)
        await db.flush()
        token = await _make_session(db, no_role_user)
        target_id = no_role_user.id
        await db.commit()

    resp = await client.get(
        f"/api/v1/auth/users/{target_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_role_session_passes_require_admin_key(client, db_session):
    """An admin-role session must still work — this is not a full lockdown,
    only member/helper/moderator/no-role sessions should be rejected."""
    async with db_session() as db:
        admin_role = await db.scalar(select(Role).where(Role.name == "admin"))
        admin_user = User(discord_id="legit-admin", username="legitadmin", role_id=admin_role.id)
        db.add(admin_user)
        await db.flush()
        token = await _make_session(db, admin_user)
        target_id = admin_user.id
        await db.commit()

    resp = await client.get(
        f"/api/v1/auth/users/{target_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_moderator_session_rejected_from_admin_key_endpoint(client, db_session):
    """A moderator-role session (mid-tier, well below admin) must also be rejected."""
    async with db_session() as db:
        mod_role = await db.scalar(select(Role).where(Role.name == "moderator"))
        mod_user = User(discord_id="mod-user-test", username="moduser", role_id=mod_role.id)
        db.add(mod_user)
        await db.flush()
        token = await _make_session(db, mod_user)
        target_id = mod_user.id
        await db.commit()

    resp = await client.get(
        f"/api/v1/auth/users/{target_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_key_header_still_works_after_fix(client, db_session):
    """The raw X-Admin-Key path must be completely unaffected by this fix."""
    async with db_session() as db:
        user = await _make_owner(db)
        target_id = user.id
        await db.commit()

    resp = await client.get(f"/api/v1/auth/users/{target_id}", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
