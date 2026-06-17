"""
api/middleware/session.py — Session token authentication.

Validates Bearer tokens issued by the Discord OAuth flow.
Used by dashboard users; plugin-to-core traffic continues to use X-Admin-Key.
"""
from fastapi import Depends, Header, HTTPException, Security
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import get_settings
from database import get_db
from models import Session, User
from api.middleware.auth import admin_key_header

settings = get_settings()


async def get_current_user(token: str, db: AsyncSession) -> User:
    """Look up a session by token and return the associated user."""
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.user))
        .where(Session.token == token)
    )
    session = result.scalar_one_or_none()

    if session is None or not session.is_valid():
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    if not session.user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    return session.user


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
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User | str:
    """
    Dependency: accepts X-Admin-Key (plugin/dashboard bootstrap) or Bearer session token.
    Admin key is checked first; session auth is used when no valid admin key is present.
    """
    if x_admin_key and x_admin_key == settings.secret_key:
        return x_admin_key

    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token:
            return await get_current_user(token, db)

    raise HTTPException(
        status_code=401,
        detail="Invalid or missing authentication",
    )
