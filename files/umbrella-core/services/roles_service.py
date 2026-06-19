"""
services/roles_service.py — Role and permission management.

Seeds default roles and permissions on first boot.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from models.permissions import Role, Permission
from models import User

# Seed data: (permission_key, description)
DEFAULT_PERMISSIONS = [
    ("players.view",         "View player records"),
    ("players.manage",       "Create and edit player records"),
    ("punishments.view",     "View punishments"),
    ("punishments.create",   "Create punishments"),
    ("punishments.revoke",   "Revoke punishments"),
    ("appeals.view",         "View appeals"),
    ("appeals.manage",       "Review and manage appeals"),
    ("moderation.kick",      "Kick players from the server"),
    ("moderation.warn",      "Warn players"),
    ("moderation.ban",       "Ban and unban players"),
    ("moderation.ipban",     "IP ban and unban addresses"),
    ("settings.view",        "View server settings"),
    ("settings.manage",      "Edit server settings"),
    ("audit.view",           "View the audit log"),
    ("roles.manage",         "Manage roles and permissions"),
    ("server.control",       "Start, stop, restart servers and maintenance mode"),
]

ALL_PERMISSION_KEYS = [p[0] for p in DEFAULT_PERMISSIONS]

# Seed data: (role_name, description, [permission_keys])
DEFAULT_ROLES = [
    ("owner", "Full access to everything", ALL_PERMISSION_KEYS),
    ("admin", "Full access except role management",
     [p for p in ALL_PERMISSION_KEYS if p != "roles.manage"]),
    ("moderator", "Moderation access",
     ["players.view", "punishments.view", "punishments.create", "punishments.revoke",
      "moderation.kick", "moderation.warn", "moderation.ban", "moderation.ipban",
      "appeals.view", "appeals.manage"]),
    ("helper", "Basic helper access",
     ["players.view", "punishments.view", "appeals.view"]),
    ("member", "Regular member",
     ["appeals.view"]),
]


class RolesService:

    @staticmethod
    async def seed_defaults(db: AsyncSession) -> None:
        """Seed default permissions and roles if they don't exist. Idempotent."""
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
        counts = dict(
            (await db.execute(
                select(Role.name, func.count(User.id)).join(User, User.role_id == Role.id).group_by(Role.name)
            )).all()
        )
        result = await db.execute(
            select(Role).options(selectinload(Role.permissions)).order_by(Role.name)
        )
        return [
            {**RolesService._to_dict(r), "member_count": counts.get(r.name, 0)}
            for r in result.scalars().all()
        ]

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
