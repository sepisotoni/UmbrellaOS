"""
services/roles_service.py — Role and permission management.

Seeds the four default roles on first boot.
Future phases will add staff_members table with role assignments.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models.permissions import Role, Permission

# Seed data: (role_name, description, [permission_keys])
DEFAULT_PERMISSIONS = [
    ("kick_players",        "Kick players from the server"),
    ("warn_players",        "Warn players"),
    ("lookup_players",      "View player history and records"),
    ("mute_players",        "Mute/unmute players"),
    ("ban_players",         "Ban/unban players"),
    ("tempban_players",     "Temporarily ban players"),
    ("manage_appeals",      "Review and action ban appeals"),
    ("manage_announcements","Send server-wide announcements"),
    ("ipban",               "IP-ban addresses"),
    ("view_audit_log",      "View the audit log"),
    ("manage_settings",     "Edit Core settings from dashboard"),
    ("manage_roles",        "Create and edit staff roles"),
    ("manage_api_keys",     "Issue and revoke API keys"),
    ("manage_secrets",      "View unmasked sensitive settings"),
]

DEFAULT_ROLES = [
    ("owner",     "Full access to everything",
     [p[0] for p in DEFAULT_PERMISSIONS]),
    ("admin",     "Full access except role management and API keys",
     [p[0] for p in DEFAULT_PERMISSIONS
      if p[0] not in ("manage_roles", "manage_api_keys", "manage_secrets")]),
    ("moderator", "Moderation access",
     ["kick_players","warn_players","lookup_players","mute_players",
      "ban_players","tempban_players","manage_appeals","manage_announcements"]),
    ("helper",    "Basic helper access",
     ["kick_players","warn_players","lookup_players"]),
]


class RolesService:

    @staticmethod
    async def seed_defaults(db: AsyncSession) -> None:
        """Seed default permissions and roles if they don't exist. Idempotent."""
        # Seed permissions first
        perm_map: dict[str, Permission] = {}
        for key, desc in DEFAULT_PERMISSIONS:
            perm = await db.scalar(
                select(Permission).where(Permission.permission_key == key)
            )
            if perm is None:
                perm = Permission(permission_key=key, description=desc)
                db.add(perm)
                await db.flush()
            perm_map[key] = perm

        # Seed roles
        for role_name, role_desc, perm_keys in DEFAULT_ROLES:
            role = await db.scalar(
                select(Role).where(Role.name == role_name).options(selectinload(Role.permissions))
            )
            if role is None:
                role = Role(name=role_name, description=role_desc)
                role.permissions = [perm_map[k] for k in perm_keys if k in perm_map]
                db.add(role)

        await db.commit()

    @staticmethod
    async def get_all(db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(Role).options(selectinload(Role.permissions)).order_by(Role.name)
        )
        return [RolesService._to_dict(r) for r in result.scalars().all()]

    @staticmethod
    async def get_all_permissions(db: AsyncSession) -> list[dict]:
        result = await db.execute(select(Permission).order_by(Permission.permission_key))
        return [{"id": p.id, "key": p.permission_key, "description": p.description}
                for p in result.scalars().all()]

    @staticmethod
    def _to_dict(role: Role) -> dict:
        return {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "permissions": [p.permission_key for p in role.permissions],
            "created_at": role.created_at.isoformat() if role.created_at else None,
        }
