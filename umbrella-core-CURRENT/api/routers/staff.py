"""Staff management — promote and demote."""
from typing import Literal
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from api.dependencies.permissions import require_permission
from api.middleware.auth import require_plugin_key
from models import User
from models.discord import DiscordAccount
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
    is_active: bool

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
        # Build Discord CDN avatar URL if we have it stored; fall back to default avatar
        avatar_hash = getattr(da, 'avatar_hash', None) if da else None
        if avatar_hash:
            avatar_url = f"https://cdn.discordapp.com/avatars/{user.discord_id}/{avatar_hash}.png?size=64"
        else:
            try:
                avatar_index = int(user.discord_id) % 5
            except (ValueError, TypeError):
                avatar_index = 0
            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{avatar_index}.png"
        staff_members.append(StaffMemberSchema(
            id=user.id,
            discord_id=user.discord_id,
            username=user.username,
            discriminator="0",
            avatar_url=avatar_url,
            role=role_name,
            permissions=permissions,
            email=user.email,
            linked_minecraft_uuid=da.player_uuid if da and da.verified else None,
            linked_minecraft_username=None,  # would need Player lookup; skip for performance
            # AUDIT-2026-08-30 fix: this field was entirely missing from
            # StaffMemberSchema — the dashboard's status badge read
            # member.is_active on a response that never included it,
            # so it was always undefined -> always falsy -> every staff
            # member showed DISABLED regardless of their real status.
            # This list_staff query only ever selects is_active==True
            # rows (see the WHERE clause above), so today this is always
            # True in practice — populated from the real column rather
            # than hardcoded, so it stays correct if that WHERE clause
            # is ever relaxed (e.g. to support showing disabled staff).
            is_active=user.is_active,
        ))

    return staff_members


class StaffLookupResponse(BaseModel):
    is_staff: bool
    discord_id: str | None = None
    role: str | None = None
    permissions: list[str] = []


def _looks_like_uuid(s: str) -> bool:
    """True if s is a canonically-formatted UUID (matches the same strict
    check as api/validators.py::validate_player_uuid, duplicated here as a
    plain bool test rather than a Pydantic validator since this needs to
    pick a lookup strategy, not reject input)."""
    try:
        return str(uuid_lib.UUID(s)) == s
    except (ValueError, AttributeError, TypeError):
        return False


@router.get("/{identifier}", response_model=StaffLookupResponse)
async def staff_lookup(
    identifier: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_plugin_key),
) -> StaffLookupResponse:
    """Look up whether a player is staff, by Discord ID or Minecraft UUID.

    Plugin-extensibility requirement ([HEAD] notice, subsystem sweep): the
    Minecraft plugin needs to check a connecting/online player's staff
    status and role so it can grant matching in-game permissions (e.g. a
    Minecraft permission node per staff role) without staff having to be
    configured twice — once in the dashboard, once in the server's own
    permission plugin.

    Placed as the LAST route in this router (after every literal-path route:
    /manage, /add, /discord-members, and the bare list at "") since a
    path-param route this general (`/{identifier}`) would otherwise shadow
    any literal segment registered after it — FastAPI matches routes in
    registration order.

    Accepts either a Discord snowflake ID or a canonical Minecraft UUID
    (36-char lowercase hyphenated — same strict format validators.py
    enforces elsewhere) and resolves whichever was given to the same
    is_staff/role/permissions shape, so the plugin doesn't need to know or
    care which identifier type it has on hand.

    Auth: X-Plugin-Key, matching /verify-code and /status's convention —
    the plugin has no admin-key or staff-session credential, and this
    endpoint only returns role/permission metadata, not anything sensitive
    (no email, no discord username, no MC username).
    """
    discord_id: str | None = None

    if _looks_like_uuid(identifier):
        # Resolve UUID -> discord_id via the verified DiscordAccount link.
        # An unverified or nonexistent link means "not staff" (a UUID with
        # no verified Discord link can't be a staff member, since staff
        # accounts always exist as Users keyed by discord_id).
        discord_account = await db.scalar(
            select(DiscordAccount).where(
                DiscordAccount.player_uuid == identifier,
                DiscordAccount.verified == True,
            )
        )
        if discord_account is not None:
            discord_id = discord_account.discord_id
    else:
        # Treat as a Discord snowflake directly.
        discord_id = identifier

    if discord_id is None:
        return StaffLookupResponse(is_staff=False)

    user = await db.scalar(
        select(User).where(User.discord_id == discord_id, User.is_active == True)
    )
    if user is None or user.role_id is None:
        return StaffLookupResponse(is_staff=False, discord_id=discord_id)

    role = await db.scalar(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == user.role_id)
    )
    role_name = role.name if role else None

    # Same "player role isn't really staff" exclusion list_staff() already
    # applies, kept consistent so a plugin and the dashboard never disagree
    # about who counts as staff.
    if role_name and role_name.lower() == "player":
        return StaffLookupResponse(is_staff=False, discord_id=discord_id)

    permissions: list[str] = list(user.extra_permissions or [])
    if role and hasattr(role, "permissions"):
        permissions = sorted(
            {p.permission_key for p in role.permissions} | set(user.extra_permissions or [])
        )

    return StaffLookupResponse(
        is_staff=True,
        discord_id=discord_id,
        role=role_name,
        permissions=permissions,
    )
