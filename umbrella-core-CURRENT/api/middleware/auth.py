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
import hashlib
import hmac
import time

from fastapi import Depends, HTTPException, Security, Header
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from config import get_settings
from database import get_db

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
    """Accept X-Admin-Key or Bearer session token (dashboard OAuth).

    Uses hmac.compare_digest for all secret comparisons to prevent timing attacks.
    """
    if x_admin_key and hmac.compare_digest(x_admin_key, settings.admin_key):
        return x_admin_key
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token:
            from api.middleware.session import get_current_user
            await get_current_user(token, db)
            return "session"
    raise HTTPException(status_code=401, detail="Invalid or missing admin key")


async def require_admin_hmac_or_session(
    x_auth_mac: str | None = Header(default=None),
    x_auth_timestamp: str | None = Header(default=None),
    x_admin_key: str | None = Security(admin_key_header),
    x_plugin_key: str | None = Security(plugin_key_header),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> str:
    if x_auth_mac and x_auth_timestamp:
        try:
            ts = int(x_auth_timestamp)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid timestamp")
        if abs(time.time() - ts) > 30:
            raise HTTPException(status_code=401, detail="Timestamp out of window")
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            settings.admin_key.encode(),
            str(ts).encode(),
            100_000,
            dklen=32,
        ).hex()
        if not hmac.compare_digest(expected, x_auth_mac):
            raise HTTPException(status_code=401, detail="Invalid MAC")
        return "hmac"
    # Accept plugin key or admin key — both use compare_digest
    key = x_plugin_key or x_admin_key
    if key and (
        hmac.compare_digest(key, settings.secret_key)
        or hmac.compare_digest(key, settings.admin_key)
    ):
        return "plugin"
    # Fall through to session token
    return await require_admin_key(x_admin_key, authorization, db)
