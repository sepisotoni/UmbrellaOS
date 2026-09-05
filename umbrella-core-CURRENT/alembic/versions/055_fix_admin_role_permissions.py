"""fix_admin_role_missing_permission_restrictions

[AUTH audit, 2026-08-30] HEAD reported that the "admin" role's permissions
appeared identical to "owner" (56 permissions each shown on the staff
page) — confirmed real by [CURSOR] while independently auditing a
different subsystem: services/roles_service.py's DEFAULT_ROLES defined
admin as "every permission except roles.manage", when the intent (per
this codebase's own model docstrings elsewhere, and HEAD's explicit
report) is that admin should have meaningfully less than owner, not
"everything except one narrow key".

Fixed the seed-data definition itself in the same commit as this
migration (services/roles_service.py) to also exclude "server.control"
and "hosting.server.control" — an admin (one tier below owner) should not
have unchecked power to stop/restart the live Minecraft server or hosted
containers without owner-level trust.

That code fix alone is NOT sufficient for any database where the "admin"
role row already exists: RolesService.seed_defaults() only creates roles
that don't exist yet ("if role is None: ..."), it never updates an
existing role's permission set. Any already-seeded database — including
the real production database HEAD's report describes — keeps the old,
over-broad permission set forever unless explicitly corrected here.

This migration removes exactly the three permission associations
(roles.manage, server.control, hosting.server.control) from whatever
role is currently named "admin", if that role and those permissions
exist. Idempotent and safe to run on:
  - The real production database (has the bug, permissions get removed)
  - Any fresh database seeded after the code fix (never had those
    associations on admin's row to begin with, so DELETE affects 0 rows)
  - A database where the admin role doesn't exist at all yet (guarded,
    no-op)

Revision ID: 055_fix_admin_role_permissions
Revises:     054_drop_redundant_console_lines_index
Create Date: 2026-09-04
"""
import sqlalchemy as sa
from alembic import op

revision = "055_fix_admin_role_permissions"
down_revision = "054_drop_redundant_console_lines_index"
branch_labels = None
depends_on = None

# Kept in sync with services/roles_service.py's DEFAULT_ROLES admin
# exclusion list — if that list changes, this migration's own historical
# record should NOT be edited retroactively; add a new migration instead.
PERMISSIONS_TO_REMOVE_FROM_ADMIN = (
    "roles.manage",
    "server.control",
    "hosting.server.control",
)


def upgrade() -> None:
    bind = op.get_bind()
    meta = sa.MetaData()
    roles = sa.Table("roles", meta, autoload_with=bind)
    permissions = sa.Table("permissions", meta, autoload_with=bind)
    role_permissions = sa.Table("role_permissions", meta, autoload_with=bind)

    admin_role_id = bind.execute(
        sa.select(roles.c.id).where(roles.c.name == "admin")
    ).scalar()
    if admin_role_id is None:
        # No admin role exists yet on this database — nothing to fix;
        # seed_defaults() will create it correctly from here on.
        return

    permission_ids = bind.execute(
        sa.select(permissions.c.id).where(
            permissions.c.permission_key.in_(PERMISSIONS_TO_REMOVE_FROM_ADMIN)
        )
    ).scalars().all()
    if not permission_ids:
        return

    op.execute(
        role_permissions.delete().where(
            sa.and_(
                role_permissions.c.role_id == admin_role_id,
                role_permissions.c.permission_id.in_(permission_ids),
            )
        )
    )


def downgrade() -> None:
    # Deliberately not restored — the removed associations were the bug,
    # not an intentional grant. Downgrading past this point does not
    # re-widen the admin role's permissions.
    pass
