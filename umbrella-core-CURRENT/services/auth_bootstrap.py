"""Bootstrap the explicitly configured first staff account."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Role, User


async def ensure_initial_admin(db: AsyncSession, discord_id: str) -> bool:
    """Create the configured initial owner if no Core account exists for it."""
    initial_admin_id = discord_id.strip()
    if not initial_admin_id:
        return False

    existing_user = await db.scalar(
        select(User).where(User.discord_id == initial_admin_id)
    )
    if existing_user is not None:
        return False

    owner_role = await db.scalar(select(Role).where(Role.name == "owner"))
    if owner_role is None:
        raise RuntimeError("Cannot bootstrap initial admin: owner role missing")

    db.add(
        User(
            discord_id=initial_admin_id,
            username=f"Discord {initial_admin_id}",
            role_id=owner_role.id,
        )
    )
    await db.flush()
    return True
