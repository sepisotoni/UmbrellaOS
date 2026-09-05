"""
tests/test_roles_service.py — Tests for services/roles_service.py's
DEFAULT_ROLES seed data.

[AUTH audit] HEAD reported the "admin" role appeared to have identical
permissions to "owner" (56 permissions each on the staff page). Confirmed
real: DEFAULT_ROLES defined admin as "every permission except roles.manage"
— a single narrow exclusion, not the meaningfully-reduced tier the role's
own description ("Full access except role management") and HEAD's report
both implied was intended. Fixed to also exclude "server.control" and
"hosting.server.control" — an admin (one tier below owner) should not have
unchecked power to stop/restart the live Minecraft server or hosted
containers without owner-level trust.

The code fix alone only affects freshly-seeded databases —
RolesService.seed_defaults() never updates an already-existing role's
permissions (only creates roles that don't exist yet). Any database where
"admin" was already seeded before this fix — including real production,
per HEAD's report — needed a data migration too: see
alembic/versions/055_fix_admin_role_permissions.py.

This is the first dedicated test file for roles_service.py.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.permissions import Role
from services.roles_service import ALL_PERMISSION_KEYS, DEFAULT_ROLES, RolesService


def test_admin_role_excludes_roles_manage():
    """The original bug's exact exclusion — must still hold."""
    _, _, admin_perms = next(r for r in DEFAULT_ROLES if r[0] == "admin")
    assert "roles.manage" not in admin_perms


def test_admin_role_excludes_server_control():
    """The fix: admin must not have unchecked power to stop/restart the
    live Minecraft server without owner-level trust."""
    _, _, admin_perms = next(r for r in DEFAULT_ROLES if r[0] == "admin")
    assert "server.control" not in admin_perms
    assert "hosting.server.control" not in admin_perms


def test_admin_role_is_meaningfully_narrower_than_owner():
    """The actual bug: admin previously differed from owner by exactly one
    permission out of 56 — not a meaningful reduction. Must now differ by
    at least the three explicitly-excluded keys, and never be equal to
    owner's full set."""
    _, _, admin_perms = next(r for r in DEFAULT_ROLES if r[0] == "admin")
    _, _, owner_perms = next(r for r in DEFAULT_ROLES if r[0] == "owner")

    assert set(owner_perms) == set(ALL_PERMISSION_KEYS)
    assert set(admin_perms) != set(owner_perms)
    excluded = set(owner_perms) - set(admin_perms)
    assert excluded == {"roles.manage", "server.control", "hosting.server.control"}


def test_owner_role_has_every_permission():
    """Sanity check the fix didn't accidentally narrow owner too — owner
    must always have literally everything, unconditionally."""
    _, _, owner_perms = next(r for r in DEFAULT_ROLES if r[0] == "owner")
    assert set(owner_perms) == set(ALL_PERMISSION_KEYS)


@pytest.mark.asyncio
async def test_seed_defaults_applies_the_fix_to_a_fresh_database(db_session):
    """End-to-end: a freshly-seeded database (the normal startup path,
    already run once by the db_session fixture itself) must reflect the
    fix — this is the "new installation" half of the fix; the "existing
    database" half is covered by the 055 migration, not by seed_defaults
    at all (seed_defaults never updates an existing role)."""
    async with db_session() as db:
        admin = await db.scalar(
            select(Role).where(Role.name == "admin").options(selectinload(Role.permissions))
        )
        owner = await db.scalar(
            select(Role).where(Role.name == "owner").options(selectinload(Role.permissions))
        )
        admin_keys = {p.permission_key for p in admin.permissions}
        owner_keys = {p.permission_key for p in owner.permissions}

        assert "roles.manage" not in admin_keys
        assert "server.control" not in admin_keys
        assert "hosting.server.control" not in admin_keys
        assert "roles.manage" in owner_keys
        assert "server.control" in owner_keys
        assert admin_keys != owner_keys
