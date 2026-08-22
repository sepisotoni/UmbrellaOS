"""Staff management — promote and demote."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from api.dependencies.permissions import require_permission
from models import User
from models.permissions import Role
from services.staff_service import StaffManageError, manage_staff_role, find_or_add_staff, ROLE_LADDER

router = APIRouter(prefix="/api/v1/staff", tags=["staff"])


class StaffAddRequest(BaseModel):
    discord_id: str
    role: str
    username: str | None = None


class StaffManageRequest(BaseModel):
    user_id: str
    action: Literal["promote", "demote"]


class StaffManageResponse(BaseModel):
    user_id: str
    username: str
    previous_role: str
    new_role: str
    action: str


@router.post("/manage", response_model=StaffManageResponse)
async def staff_manage(
    body: StaffManageRequest,
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_permission("roles.manage")),
) -> StaffManageResponse:
    actor_role_name = None
    if isinstance(auth, User) and auth.role_id:
        role = await db.scalar(select(Role).where(Role.id == auth.role_id))
        actor_role_name = role.name if role else None

    try:
        result = await manage_staff_role(
            db, body.user_id, body.action, actor_role_name=actor_role_name,
        )
        return StaffManageResponse(**result)
    except StaffManageError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/add", response_model=StaffManageResponse)
async def staff_add(
    body: StaffAddRequest,
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_permission("roles.manage")),
) -> StaffManageResponse:
    if body.role == "owner":
        raise HTTPException(status_code=403, detail="Cannot add staff directly as owner")
    try:
        result = await find_or_add_staff(db, body.discord_id, body.role, username=body.username)
        return StaffManageResponse(**result)
    except StaffManageError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/discord-members")
async def discord_members(
    db: AsyncSession = Depends(get_db),
    auth: User | str = Depends(require_permission("roles.manage")),
) -> list[dict]:
    import httpx
    from config import get_settings
    from models.setting import Setting

    settings = get_settings()
    guild_id_setting = await db.scalar(select(Setting).where(Setting.key == "discord.guild_id"))
    guild_id = guild_id_setting.value if guild_id_setting else ""
    bot_token_setting = await db.scalar(select(Setting).where(Setting.key == "discord.bot_token"))
    bot_token = bot_token_setting.value if bot_token_setting else settings.discord_bot_token

    if not guild_id or not bot_token:
        raise HTTPException(status_code=503, detail="Discord guild ID or bot token not configured")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://discord.com/api/v10/guilds/{guild_id}/members?limit=1000",
            headers={"Authorization": f"Bot {bot_token}"},
        )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Discord API error: {response.text}")
        members = response.json()

    existing_result = await db.execute(select(User.discord_id))
    existing_ids = {row[0] for row in existing_result.all()}

    return [
        {
            "discord_id": m["user"]["id"],
            "username": m["user"]["username"],
            "is_staff": m["user"]["id"] in existing_ids,
        }
        for m in members
        if not m["user"].get("bot")
    ]


class StaffMemberSchema(BaseModel):
    id: str
    discord_id: str
    username: str
    discriminator: str
    avatar_url: str | None
    role: str | None
    permissions: list[str]
    email: str | None
    linked_minecraft_uuid: str | None
    linked_minecraft_username: str | None

    class Config:
        from_attributes = True


@router.get("", response_model=list[StaffMemberSchema])
async def list_staff(
    db: AsyncSession = Depends(get_db),
    _auth: User | str = Depends(require_permission("roles.manage")),
) -> list[StaffMemberSchema]:
    """List all staff users (users with a non-player role).

    The dashboard calls GET /api/v1/staff to populate the staff directory.
    Queries User rows with a role assigned, excluding the player role.
    """
    from models.discord import DiscordAccount

    # Load users that have a role_id (unassigned users = players without a role)
    result = await db.execute(
        select(User)
        .where(User.is_active == True, User.role_id.is_not(None))
        .order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    if not users:
        return []

    # Bulk-load role data
    role_ids = list({u.role_id for u in users if u.role_id})
    roles_result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.id.in_(role_ids))
    )
    role_map: dict[str, Role] = {r.id: r for r in roles_result.scalars().all()}

    # Bulk-load Discord accounts for MC uuid lookup
    discord_ids = [u.discord_id for u in users]
    da_result = await db.execute(
        select(DiscordAccount).where(DiscordAccount.discord_id.in_(discord_ids))
    )
    discord_map: dict[str, DiscordAccount] = {
        da.discord_id: da for da in da_result.scalars().all()
    }

    staff_members = []
    for user in users:
        role_obj = role_map.get(user.role_id) if user.role_id else None
        role_name = role_obj.name if role_obj else None

        # Exclude explicit player roles
        if role_name and role_name.lower() == "player":
            continue

        # Merge role permissions + user's extra_permissions
        permissions: list[str] = list(user.extra_permissions or [])
        if role_obj and hasattr(role_obj, "permissions"):
            permissions = sorted(
                {p.permission_key for p in role_obj.permissions} | set(user.extra_permissions or [])
            )

        da = discord_map.get(user.discord_id)
        staff_members.append(StaffMemberSchema(
            id=user.id,
            discord_id=user.discord_id,
            username=user.username,
            discriminator="0",  # Modern Discord accounts have no discriminator
            avatar_url=None,
            role=role_name,
            permissions=permissions,
            email=user.email,
            linked_minecraft_uuid=da.player_uuid if da and da.verified else None,
            linked_minecraft_username=None,  # would need Player lookup; skip for performance
        ))

    return staff_members
