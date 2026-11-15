"""Staff profile endpoints and scoped API-key management.

Dashboard identity and MFA are provided by Supabase Auth. Legacy Core-managed
Discord OAuth, sessions, and TOTP endpoints return 410 and cannot issue tokens.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies.permissions import RoleChecker, require_permission
from api.middleware.auth import require_admin_key
from api.middleware.session import require_session
from config import get_settings
from database import get_db
from models import Session, User
from models.api_key import ApiKey
from models.permissions import Role
from services.api_key_service import ApiKeyService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class UserSchema(BaseModel):
    id: str
    discord_id: str
    username: str
    email: str | None
    role_id: str | None
    role: str | None = None
    permissions: list[str] = Field(default_factory=list)
    avatar_url: str | None = None
    is_active: bool
    mfa_enabled: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PublicAuthConfig(BaseModel):
    supabase_url: str
    supabase_publishable_key: str


@router.get("/public-config", response_model=PublicAuthConfig)
async def get_public_auth_config(response: Response) -> PublicAuthConfig:
    """Return only the public Supabase client settings needed by the dashboard."""
    settings = get_settings()
    if not settings.supabase_url.strip() or not settings.supabase_publishable_key.strip():
        raise HTTPException(
            status_code=503, detail="Supabase Auth client configuration is not set"
        )

    response.headers["Cache-Control"] = "public, max-age=300"
    return PublicAuthConfig(
        supabase_url=settings.supabase_url,
        supabase_publishable_key=settings.supabase_publishable_key,
    )


def _compute_avatar_url(discord_id: str, avatar_hash: str | None) -> str:
    if avatar_hash:
        return f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png?size=128"
    try:
        discriminator = int(discord_id) % 5
    except (ValueError, TypeError):
        discriminator = 0
    return f"https://cdn.discordapp.com/embed/avatars/{discriminator}.png"


async def _user_to_schema(user: User, db: AsyncSession) -> UserSchema:
    role_name: str | None = None
    permissions = set(user.extra_permissions or [])
    if user.role_id:
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == user.role_id)
        )
        role = result.scalar_one_or_none()
        if role:
            role_name = role.name
            permissions.update(permission.permission_key for permission in role.permissions)

    return UserSchema(
        id=user.id,
        discord_id=user.discord_id,
        username=user.username,
        email=user.email,
        role_id=user.role_id,
        role=role_name,
        permissions=sorted(permissions),
        avatar_url=_compute_avatar_url(
            user.discord_id, getattr(user, "discord_avatar_hash", None)
        ),
        is_active=user.is_active,
        mfa_enabled=user.mfa_enabled,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


class CreateUserRequest(BaseModel):
    discord_id: str
    username: str
    email: str | None = None
    role_id: str | None = None


class UpdateUserRequest(BaseModel):
    username: str | None = None
    email: str | None = None
    role_id: str | None = None
    is_active: bool | None = None


@router.get("", response_model=list[UserSchema])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _auth=Depends(RoleChecker(["roles.manage", "players.view"], require_all=False)),
) -> list[UserSchema]:
    result = await db.execute(select(User).offset(skip).limit(limit))
    return [await _user_to_schema(user, db) for user in result.scalars().all()]


@router.get("/users/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_admin_key),
) -> UserSchema:
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return await _user_to_schema(user, db)


@router.post("/users", response_model=UserSchema, status_code=201)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_admin_key),
) -> UserSchema:
    existing = await db.scalar(select(User).where(User.discord_id == body.discord_id))
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"User with Discord ID '{body.discord_id}' already exists",
        )
    user = User(
        discord_id=body.discord_id,
        username=body.username,
        email=body.email,
        role_id=body.role_id,
    )
    db.add(user)
    await db.flush()
    return await _user_to_schema(user, db)


@router.patch("/users/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_admin_key),
) -> UserSchema:
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    authorization_changed = False
    if body.username is not None:
        user.username = body.username
    if body.email is not None:
        user.email = body.email
    if body.role_id is not None and body.role_id != user.role_id:
        user.role_id = body.role_id
        authorization_changed = True
    if body.is_active is not None and body.is_active != user.is_active:
        user.is_active = body.is_active
        authorization_changed = True
    if authorization_changed:
        user.authz_version += 1

    await db.flush()
    return await _user_to_schema(user, db)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_admin_key),
) -> None:
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    user.is_active = False
    user.authz_version += 1
    now = datetime.now(timezone.utc)
    sessions = await db.scalars(
        select(Session).where(
            Session.user_id == user_id,
            Session.revoked.is_(False),
            Session.expires_at > now,
        )
    )
    for session in sessions:
        session.revoked = True
    await db.flush()


@router.post("/discord/authorize", status_code=410)
async def legacy_discord_authorize() -> None:
    raise HTTPException(status_code=410, detail="Dashboard sign-in is handled by Supabase Auth")


@router.post("/discord/callback", status_code=410)
async def legacy_discord_callback() -> None:
    raise HTTPException(status_code=410, detail="Dashboard sign-in is handled by Supabase Auth")


@router.post("/logout", status_code=410)
async def legacy_logout() -> None:
    raise HTTPException(status_code=410, detail="Sign out through Supabase Auth")


@router.get("/me", response_model=UserSchema)
async def get_current_user_endpoint(
    current_user: User = Depends(require_session),
    db: AsyncSession = Depends(get_db),
) -> UserSchema:
    return await _user_to_schema(current_user, db)


@router.post("/mfa/verify", status_code=410)
async def legacy_mfa_verify() -> None:
    raise HTTPException(status_code=410, detail="MFA is managed by Supabase Auth")


@router.post("/mfa/enable", status_code=410)
async def legacy_mfa_enable() -> None:
    raise HTTPException(status_code=410, detail="MFA is managed by Supabase Auth")


@router.post("/mfa/confirm", status_code=410)
async def legacy_mfa_confirm() -> None:
    raise HTTPException(status_code=410, detail="MFA is managed by Supabase Auth")


@router.post("/mfa/disable", status_code=410)
async def legacy_mfa_disable() -> None:
    raise HTTPException(status_code=410, detail="MFA is managed by Supabase Auth")


class ApiKeySchema(BaseModel):
    id: str
    name: str
    key_prefix: str
    permissions: list[str]
    revoked: bool
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    plaintext_key: str | None = None


class CreateApiKeyRequest(BaseModel):
    name: str
    permissions: list[str] = Field(default_factory=list)
    expires_in_days: int | None = None


keys_router = APIRouter(prefix="/api/v1/auth/keys", tags=["auth"])


@keys_router.get("", response_model=list[ApiKeySchema])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("identity.apikey.manage")),
) -> list[ApiKeySchema]:
    keys = await ApiKeyService.list_api_keys(db)
    return [
        ApiKeySchema(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            permissions=key.permissions,
            revoked=key.revoked,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at,
        )
        for key in keys
    ]


@keys_router.post("", response_model=ApiKeySchema, status_code=201)
async def create_api_key(
    body: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_permission("identity.apikey.manage")),
) -> ApiKeySchema:
    key, plaintext = await ApiKeyService.create_api_key(
        db,
        body.name,
        body.permissions,
        created_by=auth.username if hasattr(auth, "username") else "admin",
        expires_in_days=body.expires_in_days,
    )
    await db.commit()
    return ApiKeySchema(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        permissions=key.permissions,
        revoked=key.revoked,
        created_at=key.created_at,
        last_used_at=key.last_used_at,
        expires_at=key.expires_at,
        plaintext_key=plaintext,
    )


@keys_router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("identity.apikey.manage")),
) -> None:
    success = await ApiKeyService.revoke_api_key(db, key_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"API key '{key_id}' not found")
    await db.commit()
