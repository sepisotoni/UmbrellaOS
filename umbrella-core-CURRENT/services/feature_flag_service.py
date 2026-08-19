"""
services/feature_flag_service.py — Plain Postgres CRUD for feature flags.

No caching — callers get a fresh DB read every time. Flags are
administrative config that changes infrequently; the simplicity of a
direct read is worth more than the marginal latency saving from a cache
that could go stale or require invalidation logic.

Public surface:
    get_flag(db, name)              -> bool    (False if not found, never raises)
    set_flag(db, name, enabled, description) -> FeatureFlag  (upsert)
    list_flags(db)                  -> list[FeatureFlag]
    delete_flag(db, name)           -> bool    (True if existed)
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.feature_flag import FeatureFlag


async def get_flag(db: AsyncSession, name: str) -> bool:
    """Return the enabled state of a flag.

    Returns False if the flag doesn't exist rather than raising — callers
    should be able to gate on a flag name without first inserting a row.
    """
    flag = await db.scalar(select(FeatureFlag).where(FeatureFlag.name == name))
    if flag is None:
        return False
    return flag.enabled


async def set_flag(
    db: AsyncSession,
    name: str,
    enabled: bool,
    description: str = "",
) -> FeatureFlag:
    """Create or update a feature flag (upsert by name).

    If a row already exists it is updated in place; created_at is
    preserved so callers can see when the flag was first introduced.
    """
    flag = await db.scalar(select(FeatureFlag).where(FeatureFlag.name == name))
    if flag is None:
        flag = FeatureFlag(name=name, enabled=enabled, description=description)
        db.add(flag)
    else:
        flag.enabled = enabled
        if description:
            flag.description = description
        # updated_at is handled by the ORM onupdate hook on the model;
        # we also set it explicitly here so the in-session object reflects
        # the new value without needing a refresh round-trip.
        from datetime import datetime, timezone
        flag.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(flag)
    return flag


async def list_flags(db: AsyncSession) -> list[FeatureFlag]:
    """Return all feature flags, ordered by name."""
    result = await db.execute(select(FeatureFlag).order_by(FeatureFlag.name))
    return list(result.scalars().all())


async def delete_flag(db: AsyncSession, name: str) -> bool:
    """Delete a flag by name. Returns True if the row existed, False otherwise."""
    flag = await db.scalar(select(FeatureFlag).where(FeatureFlag.name == name))
    if flag is None:
        return False
    await db.delete(flag)
    await db.flush()
    return True
