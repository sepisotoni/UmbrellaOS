"""
api/routers/auth.py — Authentication and user management endpoints.

GET    /api/v1/auth/users         — List all staff users
GET    /api/v1/auth/users/{id}    — Get user details
POST   /api/v1/auth/users         — Create staff user
PATCH  /api/v1/auth/users/{id}    — Update user
DELETE /api/v1/auth/users/{id}    — Deactivate user

POST   /api/v1/auth/discord/authorize  — Start Discord OAuth flow
POST   /api/v1/auth/discord/callback   — Handle OAuth callback
POST   /api/v1/auth/logout             — Logout (revoke session)
GET    /api/v1/auth/me                 — Get current user (from session token)

All responses require admin key authentication (except OAuth flow).
"""
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, EmailStr

from config import get_settings
from database import get_db
from models import User, Session, DiscordOAuthPending
from models.permissions import Role
from api.middleware.auth import require_admin_key
from api.middleware.session import require_session
from api.dependencies.permissions import RoleChecker, require_permission
from services import discord_service
from services.discord_service import DiscordOAuthError
from services.settings_service import SettingsService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

SESSION_EXPIRY_DAYS = 7


class UserSchema(BaseModel):
    id: str
    discord_id: str
    username: str
    email: str | None
    role_id: str | None
    role: str | None = None
    permissions: list[str] = []
    avatar_url: str | None = None
    is_active: bool
    mfa_enabled: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


def _compute_avatar_url(discord_id: str, avatar_hash: str | None) -> str:
    """Compute Discord CDN avatar URL from avatar hash or discriminator/ID fallback."""
    if avatar_hash:
        return f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png?size=128"
    try:
        disc_num = int(discord_id) % 5
    except (ValueError, TypeError):
        disc_num = 0
    return f"https://cdn.discordapp.com/embed/avatars/{disc_num}.png"


async def _user_to_schema(user: User, db: AsyncSession) -> UserSchema:
    """Build UserSchema with resolved role name and permission keys."""
    role_name: str | None = None
    permissions: list[str] = list(user.extra_permissions or [])
    if user.role_id:
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == user.role_id)
        )
        role = result.scalar_one_or_none()
        if role:
            role_name = role.name
            permissions = sorted(
                {p.permission_key for p in role.permissions} | set(user.extra_permissions or [])
            )
    return UserSchema(
        id=user.id,
        discord_id=user.discord_id,
        username=user.username,
        email=user.email,
        role_id=user.role_id,
        role=role_name,
        permissions=permissions,
        avatar_url=_compute_avatar_url(user.discord_id, getattr(user, "discord_avatar_hash", None)),
        is_active=user.is_active,
        mfa_enabled=user.mfa_enabled,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


class CreateUserRequest(BaseModel):
    discord_id: str
    username: str
    email: str | None = None
    role_id: str | None = None


class UpdateUserRequest(BaseModel):
    username: str | None = None
    email: str | None = None
    role_id: str | None = None
    is_active: bool | None = None


class SessionSchema(BaseModel):
    token: str
    expires_at: datetime
    user_id: str

    class Config:
        from_attributes = True


class DiscordOAuthStartRequest(BaseModel):
    redirect_uri: str


class DiscordOAuthCallbackRequest(BaseModel):
    state: str
    code: str
    redirect_uri: str


class DiscordOAuthCallbackResponse(BaseModel):
    token: str
    user: UserSchema
    expires_in: int


# Staff User Management

@router.get("", response_model=list[UserSchema])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _auth=Depends(RoleChecker(["roles.manage", "players.view"], require_all=False)),
) -> list[UserSchema]:
    """List all staff users."""
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return [await _user_to_schema(u, db) for u in users]


@router.get("/users/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> UserSchema:
    """Get a user by ID."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    return await _user_to_schema(user, db)


@router.post("/users", response_model=UserSchema, status_code=201)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> UserSchema:
    """Create a new staff user account."""
    # Check if Discord ID already exists
    existing = await db.execute(
        select(User).where(User.discord_id == body.discord_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail=f"User with Discord ID '{body.discord_id}' already exists"
        )

    user = User(
        discord_id=body.discord_id,
        username=body.username,
        email=body.email,
        role_id=body.role_id,
    )
    db.add(user)
    await db.flush()

    return await _user_to_schema(user, db)


@router.patch("/users/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> UserSchema:
    """Update user details."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    if body.username is not None:
        user.username = body.username
    if body.email is not None:
        user.email = body.email
    if body.role_id is not None:
        user.role_id = body.role_id
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.flush()

    return await _user_to_schema(user, db)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> None:
    """Deactivate a user account."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    user.is_active = False

    # FIX: revoke all active sessions for the deactivated user so they
    # cannot continue using a valid session token after deactivation.
    # Without this, a deactivated user stays logged in until their
    # session naturally expires (up to 7 days).
    sessions_result = await db.execute(
        select(Session).where(
            Session.user_id == user_id,
            Session.revoked.is_(False),
            Session.expires_at > datetime.now(timezone.utc),
        )
    )
    for session in sessions_result.scalars().all():
        session.revoked = True

    await db.flush()


# Discord OAuth Flow (Phase 5 Prep)

@router.post("/discord/authorize", response_model=dict)
async def discord_authorize(
    body: DiscordOAuthStartRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Start Discord OAuth2 flow.
    Returns authorization URL for frontend redirect.
    """
    client_id = await SettingsService.get_value(db, "discord.client_id")
    # The OAuth2 authorization-request URL below never needs client_secret —
    # per spec, only client_id/response_type/scope/redirect_uri/state go on
    # it, and discord_callback below is correctly the only place that
    # actually sends client_secret (in the code-for-token exchange). But
    # fetching it here and never checking it meant a server missing
    # client_secret would let a user go through the entire Discord redirect
    # only to fail at the callback step — checking it now fails fast with a
    # clear error instead, which is the fetch's real purpose here.
    client_secret = await SettingsService.get_value(db, "discord.client_secret")
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail="Discord client_id/client_secret not set — configure them in Settings",
        )

    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(128)[:128]

    pending = DiscordOAuthPending(
        state=state,
        code_verifier=code_verifier,
    )
    db.add(pending)
    await db.flush()

    discord_authorize_url = (
        f"https://discord.com/api/oauth2/authorize?"
        f"client_id={client_id}&"
        f"response_type=code&"
        f"scope=identify%20email&"
        f"redirect_uri={quote(body.redirect_uri, safe='')}&"
        f"state={state}"
    )

    return {
        "authorize_url": discord_authorize_url,
        "state": state,
    }


@router.post("/discord/callback", response_model=DiscordOAuthCallbackResponse)
async def discord_callback(
    body: DiscordOAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> DiscordOAuthCallbackResponse:
    """
    Handle Discord OAuth callback.
    Exchanges code for token, fetches profile, creates or matches user, issues session.
    """
    pending_result = await db.execute(
        select(DiscordOAuthPending).where(
            (DiscordOAuthPending.state == body.state)
            & (DiscordOAuthPending.expires_at > datetime.now(timezone.utc))
        )
    )
    pending = pending_result.scalar_one_or_none()

    if pending is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    client_id = await SettingsService.get_value(db, "discord.client_id") or get_settings().discord_client_id
    client_secret = await SettingsService.get_value(db, "discord.client_secret") or get_settings().discord_client_secret

    try:
        token_data = await discord_service.exchange_code(
            body.code, body.redirect_uri, client_id, client_secret
        )
        discord_user = await discord_service.fetch_user(token_data["access_token"])
    except DiscordOAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    discord_id = discord_user["id"]
    username = discord_user.get("global_name") or discord_user.get("username", "unknown")
    email = discord_user.get("email")
    avatar_hash = discord_user.get("avatar")

    user_result = await db.execute(select(User).where(User.discord_id == discord_id))
    user = user_result.scalar_one_or_none()

    if user is None:
        role_id = None
        settings = get_settings()

        # Check if this is the first user (assign owner role automatically)
        user_count_result = await db.execute(select(func.count(User.id)))
        user_count = user_count_result.scalar()

        if user_count == 0:
            # First user gets owner role
            owner_role = await db.scalar(select(Role).where(Role.name == "owner"))
            if owner_role:
                role_id = owner_role.id
        elif settings.initial_admin_discord_id and discord_id == settings.initial_admin_discord_id:
            # If INITIAL_ADMIN_DISCORD_ID matches, assign owner role
            owner_role = await db.scalar(select(Role).where(Role.name == "owner"))
            if owner_role:
                role_id = owner_role.id

        user = User(
            discord_id=discord_id,
            username=username,
            email=email,
            role_id=role_id,
            discord_avatar_hash=avatar_hash,
        )
        db.add(user)
        await db.flush()
    else:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated")

        user.username = username
        user.discord_avatar_hash = avatar_hash
        if email:
            user.email = email
        await db.flush()

    # MFA gate: if the user has TOTP enabled, refuse to issue a full session
    # token until they supply a valid code. The dashboard must POST to
    # /api/v1/auth/mfa/verify with the pre-session token to complete login.
    # This prevents MFA from being silently bypassed at the OAuth callback step.
    from services.mfa_service import MFAService
    if user.mfa_enabled:
        # Issue a short-lived (5-minute) pre-session token scoped only to MFA
        # verification — it cannot be used for any other authenticated endpoint.
        mfa_token = secrets.token_urlsafe(32)
        mfa_pending_expires = datetime.now(timezone.utc) + timedelta(minutes=5)
        mfa_session = Session(
            user_id=user.id,
            token=f"mfa:{mfa_token}",
            expires_at=mfa_pending_expires,
        )
        db.add(mfa_session)
        await db.delete(pending)
        await db.flush()
        raise HTTPException(
            status_code=403,
            detail={
                "mfa_required": True,
                "mfa_token": mfa_token,
                "message": "MFA verification required — POST to /api/v1/auth/mfa/verify",
            },
        )

    # Session rotation: revoke any existing valid sessions for this user
    # before issuing a new one. Prevents session fixation (attacker plants a
    # known token, waits for the victim to authenticate — the old token would
    # then be valid). We mark revoked=True rather than deleting so that audit
    # trails are preserved. The new session is issued below.
    existing_sessions_result = await db.execute(
        select(Session).where(
            Session.user_id == user.id,
            Session.revoked.is_(False),
        )
    )
    for old_session in existing_sessions_result.scalars().all():
        old_session.revoked = True
    await db.flush()

    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)
    session_token = secrets.token_urlsafe(32)
    session = Session(
        user_id=user.id,
        token=session_token,
        expires_at=expires_at,
    )
    db.add(session)
    await db.delete(pending)
    await db.flush()

    # Explicitly refresh user so attributes aren't expired when _user_to_schema reads them
    await db.refresh(user)

    return DiscordOAuthCallbackResponse(
        token=session_token,
        user=await _user_to_schema(user, db),
        expires_in=SESSION_EXPIRY_DAYS * 24 * 3600,
    )


@router.post("/logout")
async def logout(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Logout: Revoke session token.
    Accepts session token from Authorization: Bearer <token> header only.
    Token must NOT be passed as a query parameter to avoid it appearing in
    access logs, browser history, and referrer headers.
    """
    token: str | None = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip() or None
    if not token:
        raise HTTPException(status_code=401, detail="Missing session token in Authorization header")

    result = await db.execute(
        select(Session).options(selectinload(Session.user)).where(Session.token == token)
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session.revoked = True
    await db.flush()

    return {"success": True, "message": "Logged out successfully"}


@router.get("/me", response_model=UserSchema)
async def get_current_user_endpoint(
    current_user: User = Depends(require_session),
    db: AsyncSession = Depends(get_db),
) -> UserSchema:
    """Get current authenticated user via Authorization: Bearer <token> header.

    Token must be sent in the Authorization header only, never as a query
    parameter, to avoid appearing in access logs and browser history.

    Delegates to require_session (api/middleware/session.py) rather than
    duplicating the session lookup inline — that shared path is what rejects
    "mfa:"-prefixed pre-session tokens, so any endpoint doing its own ad-hoc
    Session.token lookup silently reopens the MFA-bypass hole those tokens
    exist to prevent.
    """
    return await _user_to_schema(current_user, db)



# ---------------------------------------------------------------------------
# MFA verification — exchanges a short-lived mfa: pre-session token + TOTP
# code for a full session token. Called after /discord/callback returns 403
# with mfa_required=True.
# ---------------------------------------------------------------------------

class MFAVerifyRequest(BaseModel):
    mfa_token: str
    code: str


class MFAVerifyResponse(BaseModel):
    token: str
    user: UserSchema
    expires_in: int


@router.post("/mfa/verify", response_model=MFAVerifyResponse)
async def mfa_verify(
    body: MFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> MFAVerifyResponse:
    """
    Complete MFA login: exchange an mfa: pre-session token + TOTP code
    for a full session token.

    Flow:
      1. /discord/callback returns HTTP 403 with mfa_required=True and a
         short-lived mfa_token (valid 5 minutes, stored as "mfa:<token>").
      2. The dashboard collects the TOTP code from the user and POSTs here.
      3. We validate the TOTP, revoke the mfa: pre-session, and issue a
         full SESSION_EXPIRY_DAYS session token.
    """
    from services.mfa_service import MFAService

    # Look up the pending MFA session
    mfa_session_result = await db.execute(
        select(Session)
        .options(selectinload(Session.user))
        .where(Session.token == f"mfa:{body.mfa_token}")
    )
    mfa_session = mfa_session_result.scalar_one_or_none()

    if mfa_session is None or not mfa_session.is_valid():
        raise HTTPException(status_code=401, detail="Invalid or expired MFA token")

    user = mfa_session.user
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Verify the TOTP code
    if not await MFAService.verify_code(user, body.code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    # Revoke the pre-session token and issue a full session
    mfa_session.revoked = True
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)
    session_token = secrets.token_urlsafe(32)
    session = Session(
        user_id=user.id,
        token=session_token,
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()
    await db.refresh(user)

    return MFAVerifyResponse(
        token=session_token,
        user=await _user_to_schema(user, db),
        expires_in=SESSION_EXPIRY_DAYS * 24 * 3600,
    )


# ---------------------------------------------------------------------------
# MFA enrollment — enable / confirm / disable TOTP for authenticated users.
# All three endpoints require a valid session token (not admin key) because
# they operate on the caller's own account and we need a real user identity.
# ---------------------------------------------------------------------------

class MFABeginResponse(BaseModel):
    provisioning_uri: str
    """otpauth:// URI — render as a QR code in the dashboard."""
    secret: str
    """Base32 secret — shown as fallback for manual entry."""


class MFAConfirmRequest(BaseModel):
    code: str
    """6-digit TOTP code from the authenticator app."""


class MFADisableRequest(BaseModel):
    code: str
    """Current valid TOTP code — required to confirm intent before disabling."""


@router.post("/mfa/enable", response_model=MFABeginResponse, status_code=200)
async def mfa_enable(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_session),
) -> MFABeginResponse:
    """
    Begin MFA enrollment: generate a TOTP secret and return the provisioning
    URI (render as QR) and raw secret (for manual entry).
    MFA is NOT active until the user calls /mfa/confirm with a valid code.
    """
    from services.mfa_service import MFAService
    secret, uri = await MFAService.begin_enrollment(db, current_user)
    await db.commit()
    return MFABeginResponse(provisioning_uri=uri, secret=secret)


@router.post("/mfa/confirm", status_code=200)
async def mfa_confirm(
    body: MFAConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_session),
) -> dict:
    """
    Confirm MFA enrollment: validate the first TOTP code from the user's
    authenticator app and mark MFA as active on their account.
    """
    from services.mfa_service import MFAService, MFAError
    try:
        await MFAService.confirm_enrollment(db, current_user, body.code)
        await db.commit()
    except MFAError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return {"success": True, "message": "MFA enabled successfully"}


@router.post("/mfa/disable", status_code=200)
async def mfa_disable(
    body: MFADisableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_session),
) -> dict:
    """
    Disable MFA: require the user to supply a current valid TOTP code before
    removing MFA from their account, preventing social-engineering attacks
    where an attacker with a stolen session token disables MFA silently.
    """
    from services.mfa_service import MFAService
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled on this account")
    if not await MFAService.verify_code(current_user, body.code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
    await MFAService.disable(db, current_user)
    await db.commit()
    return {"success": True, "message": "MFA disabled"}

# ---------------------------------------------------------------------------
# API Key management — REST facades over the identity.apikey.* capabilities
# (Task 7, P14 backend fixes). Dashboard APIHub calls GET/POST/DELETE
# /api/v1/auth/keys; the actual CRUD lives in ApiKeyService.
# ---------------------------------------------------------------------------

from models.api_key import ApiKey
from services.api_key_service import ApiKeyService


class ApiKeySchema(BaseModel):
    id: str
    name: str
    key_prefix: str
    permissions: list[str]
    revoked: bool
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    plaintext_key: str | None = None  # only on creation


class CreateApiKeyRequest(BaseModel):
    name: str
    permissions: list[str] = []
    expires_in_days: int | None = None


keys_router = APIRouter(prefix="/api/v1/auth/keys", tags=["auth"])


@keys_router.get("", response_model=list[ApiKeySchema])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("identity.apikey.manage")),
) -> list[ApiKeySchema]:
    """List all API keys (never includes the plaintext value)."""
    keys = await ApiKeyService.list_api_keys(db)
    return [
        ApiKeySchema(
            id=k.id, name=k.name, key_prefix=k.key_prefix,
            permissions=k.permissions, revoked=k.revoked,
            created_at=k.created_at, last_used_at=k.last_used_at,
            expires_at=k.expires_at,
        )
        for k in keys
    ]


@keys_router.post("", response_model=ApiKeySchema, status_code=201)
async def create_api_key(
    body: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("identity.apikey.manage")),
) -> ApiKeySchema:
    """Create a new scoped API key. The plaintext key is shown once."""
    key, plaintext = await ApiKeyService.create_api_key(
        db, body.name, body.permissions,
        # FIX: pass real creator identity instead of None
        created_by=_auth.username if hasattr(_auth, "username") else "admin",
        expires_in_days=body.expires_in_days,
    )
    await db.commit()
    return ApiKeySchema(
        id=key.id, name=key.name, key_prefix=key.key_prefix,
        permissions=key.permissions, revoked=key.revoked,
        created_at=key.created_at, last_used_at=key.last_used_at,
        expires_at=key.expires_at, plaintext_key=plaintext,
    )


@keys_router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("identity.apikey.manage")),
) -> dict:
    """Revoke an API key by ID."""
    # FIX: catch only ResourceNotFoundException (404); let other errors
    # propagate as 500 — same pattern as webhooks_rest F009 fix.
    from api.middleware.errors import ResourceNotFoundException
    try:
        await ApiKeyService.revoke_api_key(db, key_id)
    except ResourceNotFoundException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return {"revoked": True, "id": key_id}
