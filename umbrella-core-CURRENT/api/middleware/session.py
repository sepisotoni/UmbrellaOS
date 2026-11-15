"""
api/middleware/session.py — Session token authentication.

Validates Supabase Auth Bearer tokens.
Used by dashboard users; plugin-to-core traffic continues to use X-Admin-Key.
"""

import hmac

from fastapi import Depends, Header, HTTPException, Security
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from models import User
from api.middleware.auth import admin_key_header, plugin_key_header
from services.supabase_auth import validate_access_token

settings = get_settings()


async def get_current_user(token: str, db: AsyncSession) -> User:
    """Validate a Supabase JWT and resolve its server-issued staff identity."""
    claims = await validate_access_token(token)
    app_metadata = claims["app_metadata"]
    user_id = app_metadata["umbrella_user_id"]

    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="Staff account not found")
    if user.supabase_auth_id and user.supabase_auth_id != claims["sub"]:
        raise HTTPException(status_code=401, detail="Access token identity mismatch")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    if user.authz_version != app_metadata["umbrella_authz_version"]:
        raise HTTPException(
            status_code=401, detail="Authorization changed; refresh your session"
        )

    if not user.supabase_auth_id:
        user.supabase_auth_id = claims["sub"]

    user._supabase_permissions = frozenset(app_metadata["umbrella_permissions"])
    user._supabase_role = app_metadata.get("umbrella_role")
    user._supabase_aal = claims.get("aal")
    return user


async def require_session(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: validates Bearer session token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing session token")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid or missing session token")

    return await get_current_user(token, db)


async def require_admin_key_or_session(
    x_admin_key: str | None = Security(admin_key_header),
    x_plugin_key: str | None = Security(plugin_key_header),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User | str:
    """
    Dependency: accepts X-Admin-Key, X-Plugin-Key, or Bearer session token.
    Admin/plugin keys are checked first and bypass role-permission checks (they
    return a str sentinel, which require_permission treats as pre-authorised).
    Session auth is used when no valid key is present.

    Uses hmac.compare_digest for all secret comparisons to prevent timing attacks.
    """
    if x_admin_key and hmac.compare_digest(x_admin_key, settings.admin_key):
        return x_admin_key

    # Plugin key (sent by the Minecraft plugin as X-Plugin-Key) gets the same
    # bypass as admin key so plugin-facing endpoints like /ai/copilot work without
    # a user session or role assignment.
    if x_plugin_key and hmac.compare_digest(x_plugin_key, settings.secret_key):
        return x_plugin_key

    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token:
            return await get_current_user(token, db)

    raise HTTPException(
        status_code=401,
        detail="Invalid or missing authentication",
    )
