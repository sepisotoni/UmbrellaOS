"""
api/dependencies/permissions.py — Role-based permission dependencies.

Checks permission keys against the authenticated user's role.
X-Admin-Key auth bypasses all permission checks (plugin god mode).

Permission *resolution* (role -> permission keys, plus extra_permissions)
lives in services/permission_resolution.py and is shared with the
Capability Registry's CallContext — this module only adds request-scoped
caching on top of that shared resolver, it does not compute permissions
itself.
"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from models.permissions import Role
from api.middleware.session import require_admin_key_or_session
from api.middleware.api_key_auth import require_capability_auth
from models.api_key import ApiKey
from services.permission_resolution import resolve_user_permissions


async def _load_role_permissions(
    user: User,
    db: AsyncSession,
    request: Request,
) -> set[str]:
    """Load and cache a user's effective permission keys for the current request."""
    cache: dict[str | None, set[str]] = getattr(
        request.state, "role_permissions_cache", None
    )
    if cache is None:
        cache = {}
        request.state.role_permissions_cache = cache

    if user.role_id in cache:
        return cache[user.role_id]

    permissions = await resolve_user_permissions(user, db)
    cache[user.role_id] = permissions
    return permissions


def require_permission(permission: str):
    """Return a FastAPI dependency that enforces a single permission key."""

    async def _checker(
        request: Request,
        auth: User | str | ApiKey = Depends(require_capability_auth),
        db: AsyncSession = Depends(get_db),
    ) -> User | str | ApiKey:
        if isinstance(auth, (str, ApiKey)):
            # admin key or hmac or api key — check api key permissions
            if isinstance(auth, ApiKey):
                if permission not in (auth.permissions or []):
                    raise HTTPException(
                        status_code=403,
                        detail=f"API key missing permission: {permission}",
                    )
            return auth

        permissions = await _load_role_permissions(auth, db, request)
        if permission not in permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Missing permission: {permission}",
            )
        return auth

    return _checker


class RoleChecker:
    """Class-based permission checker for routes needing multiple permission keys."""

    def __init__(self, permissions: list[str], require_all: bool = True):
        self.permissions = permissions
        self.require_all = require_all

    async def __call__(
        self,
        request: Request,
        auth: User | str | ApiKey = Depends(require_capability_auth),
        db: AsyncSession = Depends(get_db),
    ) -> User | str | ApiKey:
        if isinstance(auth, (str, ApiKey)):
            if isinstance(auth, ApiKey):
                if self.require_all:
                    missing = [p for p in self.permissions if p not in (auth.permissions or [])]
                    if missing:
                        raise HTTPException(status_code=403, detail=f"API key missing permissions: {', '.join(missing)}")
                elif not any(p in (auth.permissions or []) for p in self.permissions):
                    raise HTTPException(status_code=403, detail=f"API key missing one of: {', '.join(self.permissions)}")
            return auth

        user_permissions = await _load_role_permissions(auth, db, request)

        if self.require_all:
            missing = [p for p in self.permissions if p not in user_permissions]
            if missing:
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing permissions: {', '.join(missing)}",
                )
        elif not any(p in user_permissions for p in self.permissions):
            raise HTTPException(
                status_code=403,
                detail=f"Missing one of permissions: {', '.join(self.permissions)}",
            )

        return auth


async def require_owner(
    auth: User | str | ApiKey = Depends(require_capability_auth),
    db: AsyncSession = Depends(get_db),
) -> User | str | ApiKey:
    """Only the owner role (or admin key) may access settings."""
    if isinstance(auth, (str, ApiKey)):
        return auth
    if not auth.role_id:
        raise HTTPException(status_code=403, detail="Owner access required")
    role = await db.scalar(select(Role).where(Role.id == auth.role_id))
    if not role or role.name != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    return auth
