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
