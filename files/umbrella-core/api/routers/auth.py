"""
api/routers/auth.py — Authentication and user management endpoints.

GET    /api/v1/auth/users         — List all staff users
GET    /api/v1/auth/users/{id}    — Get user details
POST   /api/v1/auth/users         — Create staff user
PATCH  /api/v1/auth/users/{id}    — Update user
DELETE /api/v1/auth/users/{id}    — Deactivate user

POST   /api/v1/auth/discord/authorize  — Start Discord OAuth flow
POST   /api/v1/auth/discord/callback   — Handle OAuth callback
POST   /api/v1/auth/logout             — Logout (revoke session)
GET    /api/v1/auth/me                 — Get current user (from session token)

All responses require admin key authentication (except OAuth flow).
"""
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, EmailStr

from config import get_settings
from database import get_db
from models import User, Session, DiscordOAuthPending
from models.permissions import Role
from api.middleware.auth import require_admin_key
from services import discord_service
from services.discord_service import DiscordOAuthError
from services.settings_service import SettingsService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

SESSION_EXPIRY_DAYS = 7


class UserSchema(BaseModel):
    id: str
    discord_id: str
    username: str
    email: str | None
    role_id: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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


class SessionSchema(BaseModel):
    token: str
    expires_at: datetime
    user_id: str

    class Config:
        from_attributes = True


class DiscordOAuthStartRequest(BaseModel):
    redirect_uri: str


class DiscordOAuthCallbackRequest(BaseModel):
    state: str
    code: str
    redirect_uri: str


class DiscordOAuthCallbackResponse(BaseModel):
    token: str
    user: UserSchema
    expires_in: int


# Staff User Management

@router.get("", response_model=list[UserSchema])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> list[UserSchema]:
    """List all staff users."""
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return [UserSchema.model_validate(u) for u in users]


@router.get("/users/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> UserSchema:
    """Get a user by ID."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    return UserSchema.model_validate(user)


@router.post("/users", response_model=UserSchema, status_code=201)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> UserSchema:
    """Create a new staff user account."""
    # Check if Discord ID already exists
    existing = await db.execute(
        select(User).where(User.discord_id == body.discord_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail=f"User with Discord ID '{body.discord_id}' already exists"
        )

    user = User(
        discord_id=body.discord_id,
        username=body.username,
        email=body.email,
        role_id=body.role_id,
    )
    db.add(user)
    await db.flush()

    return UserSchema.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> UserSchema:
    """Update user details."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    if body.username is not None:
        user.username = body.username
    if body.email is not None:
        user.email = body.email
    if body.role_id is not None:
        user.role_id = body.role_id
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.flush()

    return UserSchema.model_validate(user)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> None:
    """Deactivate a user account."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    user.is_active = False
    await db.flush()


# Discord OAuth Flow (Phase 5 Prep)

@router.post("/discord/authorize", response_model=dict)
async def discord_authorize(
    body: DiscordOAuthStartRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Start Discord OAuth2 flow.
    Returns authorization URL for frontend redirect.
    """
    client_id = await SettingsService.get_value(db, "discord.client_id")
    client_secret = await SettingsService.get_value(db, "discord.client_secret")
    if not client_id:
        raise HTTPException(status_code=503, detail="Discord client_id not set — configure it in Settings")

    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(128)[:128]

    pending = DiscordOAuthPending(
        state=state,
        code_verifier=code_verifier,
    )
    db.add(pending)
    await db.flush()

    discord_authorize_url = (
        f"https://discord.com/api/oauth2/authorize?"
        f"client_id={client_id}&"
        f"response_type=code&"
        f"scope=identify%20email&"
        f"redirect_uri={body.redirect_uri}&"
        f"state={state}"
    )

    return {
        "authorize_url": discord_authorize_url,
        "state": state,
    }


@router.post("/discord/callback", response_model=DiscordOAuthCallbackResponse)
async def discord_callback(
    body: DiscordOAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> DiscordOAuthCallbackResponse:
    """
    Handle Discord OAuth callback.
    Exchanges code for token, fetches profile, creates or matches user, issues session.
    """
    pending_result = await db.execute(
        select(DiscordOAuthPending).where(
            (DiscordOAuthPending.state == body.state)
            & (DiscordOAuthPending.expires_at > datetime.now(timezone.utc))
        )
    )
    pending = pending_result.scalar_one_or_none()

    if pending is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        token_data = await discord_service.exchange_code(body.code, body.redirect_uri)
        discord_user = await discord_service.fetch_user(token_data["access_token"])
    except DiscordOAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    discord_id = discord_user["id"]
    username = discord_user.get("global_name") or discord_user.get("username", "unknown")
    email = discord_user.get("email")

    user_result = await db.execute(select(User).where(User.discord_id == discord_id))
    user = user_result.scalar_one_or_none()

    if user is None:
        role_id = None
        settings = get_settings()

        # Check if this is the first user (assign owner role automatically)
        user_count_result = await db.execute(select(func.count(User.id)))
        user_count = user_count_result.scalar()

        if user_count == 0:
            # First user gets owner role
            owner_role = await db.scalar(select(Role).where(Role.name == "owner"))
            if owner_role:
                role_id = owner_role.id
        elif settings.initial_admin_discord_id and discord_id == settings.initial_admin_discord_id:
            # If INITIAL_ADMIN_DISCORD_ID matches, assign owner role
            owner_role = await db.scalar(select(Role).where(Role.name == "owner"))
            if owner_role:
                role_id = owner_role.id

        user = User(
            discord_id=discord_id,
            username=username,
            email=email,
            role_id=role_id,
        )
        db.add(user)
        await db.flush()
    else:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated")

        user.username = username
        if email:
            user.email = email
        await db.flush()

    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)
    session_token = secrets.token_urlsafe(32)
    session = Session(
        user_id=user.id,
        token=session_token,
        expires_at=expires_at,
    )
    db.add(session)
    await db.delete(pending)
    await db.flush()

    return DiscordOAuthCallbackResponse(
        token=session_token,
        user=UserSchema.model_validate(user),
        expires_in=SESSION_EXPIRY_DAYS * 24 * 3600,
    )


@router.post("/logout")
async def logout(
    session_token: str = Query(..., description="Session token to revoke"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Logout: Revoke session token.
    Phase 5: Accept session token from Authorization header or query.
    """
    result = await db.execute(
        select(Session).options(selectinload(Session.user)).where(Session.token == session_token)
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session.revoked = True
    await db.flush()

    return {"success": True, "message": "Logged out successfully"}


@router.get("/me", response_model=UserSchema)
async def get_current_user(
    session_token: str = Query(..., description="Session token"),
    db: AsyncSession = Depends(get_db),
) -> UserSchema:
    """
    Get current authenticated user.
    Phase 5: Extract user from valid session token.
    """
    result = await db.execute(
        select(Session).options(selectinload(Session.user)).where(Session.token == session_token)
    )
    session = result.scalar_one_or_none()

    if session is None or not session.is_valid():
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return UserSchema.model_validate(session.user)
