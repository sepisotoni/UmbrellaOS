"""
api/middleware/auth.py — API key and session authentication.

Phase 1 implements simple shared-secret auth for the plugin and
an X-Admin-Key header for dashboard/admin calls.
Full Discord OAuth + session tokens come in Phase 3.

Key tiers (Phase 1):
    X-Plugin-Key   — plugin-facing endpoints only
    X-Admin-Key    — full access (must match SECRET_KEY in .env for now)

Phase 3 will replace X-Admin-Key with proper session tokens.

Phase 16B (Task A) adds require_admin_hmac_or_session: bot-facing routes
accept X-Auth-MAC + X-Auth-Timestamp (PBKDF2-HMAC-SHA256 derived from the
shared secret) as an alternative to the raw admin key. The raw key path
(require_admin_key) is preserved unchanged — the dashboard and other
callers continue using it. Only the bot's capability-invoke path and the
new bot-registration endpoint use the HMAC tier.
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
    """Accept X-Plugin-Key or X-Admin-Key (same secret)."""
    key = x_plugin_key or x_admin_key
    if not key or key != settings.secret_key:
        raise HTTPException(status_code=401, detail="Invalid or missing plugin key")
    return key


async def require_admin_key(
    x_admin_key: str | None = Security(admin_key_header),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Accept X-Admin-Key or Bearer session token (dashboard OAuth)."""
    if x_admin_key and x_admin_key == settings.admin_key:
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
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> str:
    """
    Authentication dependency for bot-facing routes (Phase 16B Task A).

    Accepts either:
    1. PBKDF2-HMAC-SHA256 MAC (X-Auth-MAC + X-Auth-Timestamp) — the bot
       derives the MAC from the shared secret; core re-derives and compares
       with hmac.compare_digest(). Requests outside a ±30-second window are
       rejected to prevent replay attacks.
    2. Raw admin key or Bearer session token — falls through to the existing
       require_admin_key() path for non-bot callers that haven't migrated.

    The raw-key path (require_admin_key) is NOT removed — dashboard and
    other callers continue using it unmodified.
    """
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
    # Fall through to existing key/session logic
    return await require_admin_key(x_admin_key, authorization, db)


async def optional_auth(
    x_plugin_key: str | None = Security(plugin_key_header),
    x_admin_key: str | None = Security(admin_key_header),
) -> dict:
    """
    Returns auth context without raising. Useful for endpoints that
    behave differently based on auth level.
    """
    if x_admin_key and x_admin_key == settings.admin_key:
        return {"type": "admin", "actor": "dashboard"}
    if x_plugin_key and x_plugin_key == settings.secret_key:
        return {"type": "plugin", "actor": "plugin"}
    return {"type": "anonymous", "actor": "anonymous"}
