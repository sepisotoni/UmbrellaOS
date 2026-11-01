"""
api/middleware/auth.py — API key and session authentication.

Three auth tiers, in order of trust:

    X-Plugin-Key   — Minecraft plugin-facing endpoints only (matches SECRET_KEY)
    X-Admin-Key    — Full admin access (matches ADMIN_KEY). Dashboard and admin
                     tools use this; also accepted as Bearer session token from
                     the Discord OAuth flow.
    X-Auth-MAC +   — PBKDF2-HMAC-SHA256 bot auth (Phase 16B). The Discord bot
    X-Auth-Timestamp  exclusively uses this tier; the raw admin key is NOT
                     distributed to the bot. 30-second timestamp window.

All secret comparisons use hmac.compare_digest to prevent timing attacks.
"""

import hmac

from fastapi import Depends, HTTPException, Security, Header
from redis.asyncio import Redis
from starlette.requests import Request
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from config import get_settings
from database import get_db, get_redis
from api.middleware.bot_mac import verify_bot_mac

settings = get_settings()

plugin_key_header = APIKeyHeader(name="X-Plugin-Key", auto_error=False)
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def require_plugin_key(
    x_plugin_key: str | None = Security(plugin_key_header),
    x_admin_key: str | None = Security(admin_key_header),
) -> str:
    """Accept X-Plugin-Key or X-Admin-Key (plugin key matches SECRET_KEY or ADMIN_KEY).

    Uses hmac.compare_digest for all secret comparisons to prevent timing attacks.
    """
    key = x_plugin_key or x_admin_key
    if key and (
        hmac.compare_digest(key, settings.secret_key)
        or hmac.compare_digest(key, settings.admin_key)
    ):
        return key
    raise HTTPException(status_code=401, detail="Invalid or missing plugin key")


async def require_admin_key(
    x_admin_key: str | None = Security(admin_key_header),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Accept X-Admin-Key, or a Bearer session token belonging to an
    owner/admin-role user.

    CRITICAL BUG FIXED 2026-08-30 — this previously accepted ANY valid
    session token regardless of the user's role: the Bearer-token branch
    called get_current_user(token, db) purely to confirm the session was
    valid and the account active, then returned unconditionally, without
    ever inspecting who that user actually was. Since this dependency
    gates api/routers/auth.py's own POST/PATCH/DELETE /users/{id} — arbitrary
    staff account creation, role reassignment, and deactivation — plus
    admin tooling in replay.py, translation.py, verification.py,
    alt_detection.py, bridge.py, analytics.py, ai_tasks.py, and snapshot.py,
    this meant a `member`-role user (the lowest tier, appeals.view only) with
    nothing more than a normal dashboard login could PATCH their own (or
    anyone's) user row and set role_id directly to the owner role's ID —
    a complete privilege-escalation-to-owner with a single authenticated
    request, no `roles.manage` permission or any check whatsoever required.
    It also meant a Discord-linked account with NO staff role assigned at
    all (role_id=None) could reach every one of these endpoints, since
    get_current_user only checks is_active, never role_id.

    Fix: the Bearer-token branch now additionally resolves the user's role
    and requires it to be "owner" or "admin" — the two roles this codebase's
    own design already treats as full/near-full access (see
    models/permissions.py's role docstring: owner = all permissions,
    admin = all except roles.manage). Any other role, or no role at all,
    gets 403, not silently passing as if the check never happened.

    Uses hmac.compare_digest for all secret comparisons to prevent timing attacks.
    """
    if x_admin_key and hmac.compare_digest(x_admin_key, settings.admin_key):
        return x_admin_key
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token:
            from api.middleware.session import get_current_user

            user = await get_current_user(token, db)
            if user.role_id:
                from sqlalchemy import select as _select
                from models.permissions import Role as _Role

                role = await db.scalar(_select(_Role).where(_Role.id == user.role_id))
                if role is not None and role.name in ("owner", "admin"):
                    return "session"
            raise HTTPException(
                status_code=403,
                detail="Admin or owner role required for this endpoint",
            )
    raise HTTPException(status_code=401, detail="Invalid or missing admin key")


async def require_admin_hmac_or_session(
    request: Request,
    x_auth_mac: str | None = Header(default=None),
    x_auth_timestamp: str | None = Header(default=None),
    x_auth_version: str | None = Header(default=None),
    x_auth_nonce: str | None = Header(default=None),
    x_admin_key: str | None = Security(admin_key_header),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> str:
    if any((x_auth_mac, x_auth_timestamp, x_auth_version, x_auth_nonce)):
        await verify_bot_mac(
            request=request,
            mac=x_auth_mac,
            timestamp=x_auth_timestamp,
            version=x_auth_version,
            nonce=x_auth_nonce,
            secret=settings.admin_key,
            redis=redis,
        )
        return "hmac"
    # Only the admin key (or an owner/admin session) may authorize this tier.
    # A plugin credential is deliberately insufficient: treating SECRET_KEY
    # as an admin key permits any plugin to queue arbitrary console commands.
    return await require_admin_key(x_admin_key, authorization, db)


async def require_console_read_auth(
    request: Request,
    x_plugin_key: str | None = Security(plugin_key_header),
    x_admin_key: str | None = Security(admin_key_header),
    x_auth_mac: str | None = Header(default=None),
    x_auth_timestamp: str | None = Header(default=None),
    x_auth_version: str | None = Header(default=None),
    x_auth_nonce: str | None = Header(default=None),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> str:
    """Preserve legacy plugin read access to console history, not admin writes.

    This narrow exception must not be used by command enqueue or other
    mutation endpoints: the shared plugin key has no staff privileges.
    """
    if x_plugin_key is not None:
        if hmac.compare_digest(x_plugin_key, settings.secret_key):
            return "plugin-console-read"
        raise HTTPException(status_code=401, detail="Invalid plugin key")

    return await require_admin_hmac_or_session(
        request,
        x_auth_mac,
        x_auth_timestamp,
        x_auth_version,
        x_auth_nonce,
        x_admin_key,
        authorization,
        db,
        redis,
    )
