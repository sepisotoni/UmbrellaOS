"""
services/permission_resolution.py — Single implementation of "what permission
keys does this user actually have."

Prior to Phase 0, this logic lived only inside
`api/dependencies/permissions.py` as a private, request-cached helper. The
Capability Registry needs the exact same resolution (a role's permission set
plus the user's `extra_permissions` overrides) when building a `CallContext`
for CLI/AI/Discord invocations, which have no `Request` to cache against.

Rather than re-deriving that logic a second time, it is extracted here once
and imported by both call sites:

    - api/dependencies/permissions.py  (REST dependency, adds request-scoped caching)
    - registry/context.py              (CallContext construction, no caching needed —
                                         built once per call, not reused across a request)

This is the only place a user's effective permission set is computed. If the
rule ever changes (e.g. permission inheritance, deny-overrides, group-based
grants), it changes here and both call sites pick it up automatically.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import User
from models.permissions import Role


async def resolve_user_permissions(user: User, db: AsyncSession) -> set[str]:
    """
    Return the full set of permission keys granted to `user`.

    A user's effective permissions are the union of:
    - the permission keys attached to their assigned role (if any)
    - their individual `extra_permissions` overrides (one-off grants that
      don't require moving the user to a different role)

    Returns an empty set for a user with no role and no extra permissions —
    callers should treat "no permissions" as "deny", not as "unauthenticated";
    authentication is a separate concern handled before this is ever called.
    """
    permissions: set[str] = set()

    if user.role_id:
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == user.role_id)
        )
        role = result.scalar_one_or_none()
        if role is not None:
            permissions.update(p.permission_key for p in role.permissions)

    if user.extra_permissions:
        permissions.update(user.extra_permissions)

    return permissions
