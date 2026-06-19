"""
api/middleware/auth.py — API key and session authentication.

Phase 1 implements simple shared-secret auth for the plugin and
an X-Admin-Key header for dashboard/admin calls.
Full Discord OAuth + session tokens come in Phase 3.

Key tiers (Phase 1):
    X-Plugin-Key   — plugin-facing endpoints only
    X-Admin-Key    — full access (must match SECRET_KEY in .env for now)

Phase 3 will replace X-Admin-Key with proper session tokens.
"""
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
    if x_admin_key and x_admin_key == settings.secret_key:
        return x_admin_key
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token:
            from api.middleware.session import get_current_user
            await get_current_user(token, db)
            return "session"
    raise HTTPException(status_code=401, detail="Invalid or missing admin key")


async def optional_auth(
    x_plugin_key: str | None = Security(plugin_key_header),
    x_admin_key: str | None = Security(admin_key_header),
) -> dict:
    """
    Returns auth context without raising. Useful for endpoints that
    behave differently based on auth level.
    """
    if x_admin_key and x_admin_key == settings.secret_key:
        return {"type": "admin", "actor": "dashboard"}
    if x_plugin_key and x_plugin_key == settings.secret_key:
        return {"type": "plugin", "actor": "plugin"}
    return {"type": "anonymous", "actor": "anonymous"}
