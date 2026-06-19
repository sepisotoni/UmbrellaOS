"""Staff role promotion and demotion."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User
from models.permissions import Role

ROLE_LADDER = ["member", "helper", "moderator", "admin", "owner"]


class StaffManageError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def _role_by_name(db: AsyncSession, name: str) -> Role | None:
    return await db.scalar(select(Role).where(Role.name == name))


async def manage_staff_role(
    db: AsyncSession,
    user_id: str,
    action: str,
    *,
    actor_role_name: str | None = None,
) -> dict:
    if action not in ("promote", "demote"):
        raise StaffManageError("action must be 'promote' or 'demote'")

    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise StaffManageError(f"User '{user_id}' not found", 404)
    if not user.is_active:
        raise StaffManageError("Cannot change role for inactive user")

    current_role = await db.scalar(select(Role).where(Role.id == user.role_id)) if user.role_id else None
    current_name = current_role.name if current_role else "member"

    try:
        idx = ROLE_LADDER.index(current_name)
    except ValueError:
        idx = 0

    if action == "promote":
        if idx >= len(ROLE_LADDER) - 1:
            raise StaffManageError("User already has the highest role")
        if ROLE_LADDER[idx + 1] == "owner" and actor_role_name != "owner":
            raise StaffManageError("Only owners can promote to owner", 403)
        new_name = ROLE_LADDER[idx + 1]
    else:
        if idx <= 0:
            raise StaffManageError("User already has the lowest role")
        if current_name == "owner" and actor_role_name != "owner":
            raise StaffManageError("Only owners can demote an owner", 403)
        new_name = ROLE_LADDER[idx - 1]

    new_role = await _role_by_name(db, new_name)
    if new_role is None:
        raise StaffManageError(f"Role '{new_name}' not found", 500)

    user.role_id = new_role.id
    await db.flush()

    return {
        "user_id": user.id,
        "username": user.username,
        "previous_role": current_name,
        "new_role": new_name,
        "action": action,
    }


async def role_member_counts(db: AsyncSession) -> dict[str, int]:
    rows = await db.execute(
        select(Role.name, func.count(User.id))
        .join(User, User.role_id == Role.id, isouter=True)
        .group_by(Role.name)
    )
    return {name: count for name, count in rows.all()}
