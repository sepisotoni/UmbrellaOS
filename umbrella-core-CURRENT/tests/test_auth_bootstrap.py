import pytest
from sqlalchemy import select

from models import Role, User
from services.auth_bootstrap import ensure_initial_admin


@pytest.mark.asyncio
async def test_initial_admin_bootstrap_creates_owner_once(db_session):
    async with db_session() as db:
        created = await ensure_initial_admin(db, " 123456789 ")
        await db.commit()
        assert created is True

        user = await db.scalar(select(User).where(User.discord_id == "123456789"))
        owner_role = await db.scalar(select(Role).where(Role.name == "owner"))
        assert user is not None
        assert owner_role is not None
        assert user.role_id == owner_role.id
        assert await ensure_initial_admin(db, "123456789") is False


@pytest.mark.asyncio
async def test_initial_admin_bootstrap_ignores_blank_discord_id(db_session):
    async with db_session() as db:
        assert await ensure_initial_admin(db, "  ") is False
        assert await db.scalar(select(User)) is None
