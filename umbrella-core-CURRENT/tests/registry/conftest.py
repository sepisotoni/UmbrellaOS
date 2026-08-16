"""
tests/registry/conftest.py — Shared helpers for Capability Registry tests.

Reuses the project's existing `db_session`/`client` fixtures from
tests/conftest.py (in-memory SQLite, seeded roles/permissions) rather than
building a second test-database setup — the registry test suite exercises
the same seeded `owner`/`admin`/`moderator`/`helper`/`member` roles every
other router's tests already assume exist.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from models import Session, User
from models.permissions import Role


async def session_headers_for_role(db_session, role_name: str, suffix: str = "") -> dict:
    """
    Create a User with the given seeded role plus a valid Session token,
    returning the Bearer header a REST test can use. Mirrors the identical
    helper already used in tests/test_permissions.py — kept local to this
    package rather than imported cross-file, matching the existing
    per-test-file convention in this codebase.
    """
    discord_id = f"discord-{role_name}{suffix}"
    token = f"token-{role_name}{suffix}"
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == role_name))
        user = User(discord_id=discord_id, username=f"user_{role_name}{suffix}", role_id=role.id)
        db.add(user)
        await db.flush()
        db.add(
            Session(
                user_id=user.id,
                token=token,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
        )
        await db.commit()
    return {"Authorization": f"Bearer {token}"}
