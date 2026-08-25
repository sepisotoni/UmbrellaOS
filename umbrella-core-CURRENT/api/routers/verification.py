"""
api/routers/verification.py — Player verification endpoints.

POST /api/v1/verification/request    — Request a verification code
POST /api/v1/verification/confirm    — Confirm verification code
POST /api/v1/verification/status     — Check verification status
GET  /api/v1/verification/pending    — List pending verifications
POST /api/v1/verification/revoke     — Revoke verification
"""
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel

from database import get_db
from models import VerificationCode, DiscordAccount, AuditLog
from api.middleware.auth import require_admin_key
from api.dependencies.permissions import require_permission

router = APIRouter(prefix="/api/v1/verification", tags=["verification"])


class VerificationRequestRequest(BaseModel):
    player_uuid: str
    player_username: str
    ip_address: str | None = None


class VerificationRequestResponse(BaseModel):
    code: str
    expires_in: int
    player_uuid: str
    already_verified: bool = False


class VerificationConfirmRequest(BaseModel):
    discord_id: str
    discord_username: str
    code: str


class VerificationConfirmResponse(BaseModel):
    success: bool
    player_uuid: str
    player_username: str


class VerificationStatusRequest(BaseModel):
    player_uuid: str


class VerificationStatusResponse(BaseModel):
    verified: bool
    discord_id: str | None = None
    discord_username: str | None = None


class VerificationCodeSchema(BaseModel):
    id: int
    player_uuid: str
    player_username: str
    code: str
    created_at: datetime
    expires_at: datetime
    used: bool
    ip_address: str | None

    class Config:
        from_attributes = True


class VerificationRevokeRequest(BaseModel):
    player_uuid: str


@router.post("/request", response_model=VerificationRequestResponse)
async def request_verification(
    body: VerificationRequestRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> VerificationRequestResponse:
    """
    Request a verification code for a player.
    Called by MC plugin when unverified player joins.
    """
    # Check if player is already verified
    existing_account = await db.execute(
        select(DiscordAccount).where(
            and_(
                DiscordAccount.player_uuid == body.player_uuid,
                DiscordAccount.verified == True
            )
        )
    )
    if existing_account.scalar_one_or_none():
        return VerificationRequestResponse(
            code="",
            expires_in=0,
            player_uuid=body.player_uuid,
            already_verified=True
        )
    
    # Generate random 6-digit code
    code = f"{random.randint(100000, 999999)}"
    
    # Create verification code with 10 minute expiry
    verification_code = VerificationCode(
        player_uuid=body.player_uuid,
        player_username=body.player_username,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        ip_address=body.ip_address,
    )
    db.add(verification_code)
    await db.flush()
    
    return VerificationRequestResponse(
        code=code,
        expires_in=600,
        player_uuid=body.player_uuid,
    )


@router.post("/confirm", response_model=VerificationConfirmResponse)
async def confirm_verification(
    body: VerificationConfirmRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> VerificationConfirmResponse:
    """
    Confirm a verification code.
    Called by Discord bot when player DMs their code.
    """
    # Find verification code
    result = await db.execute(
        select(VerificationCode).where(VerificationCode.code == body.code)
    )
    verification_code = result.scalar_one_or_none()
    
    if not verification_code:
        raise HTTPException(status_code=404, detail="Code not found")
    
    # Check if expired
    if datetime.utcnow() > verification_code.expires_at.replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="Code expired")
    
    # Check if already used
    if verification_code.used:
        raise HTTPException(status_code=400, detail="Code already used")
    
    # Mark code as used
    verification_code.used = True

    # Is this Discord account already verified and linked to a DIFFERENT player?
    existing_account = await db.execute(
        select(DiscordAccount).where(DiscordAccount.discord_id == body.discord_id)
    )
    account = existing_account.scalar_one_or_none()

    if account and account.verified and account.player_uuid and account.player_uuid != verification_code.player_uuid:
        raise HTTPException(
            status_code=409,
            detail="This Discord account is already linked to a different Minecraft account and cannot be relinked."
        )

    # Is this Minecraft account already verified and linked to a DIFFERENT Discord account?
    existing_for_player = await db.execute(
        select(DiscordAccount).where(
            and_(
                DiscordAccount.player_uuid == verification_code.player_uuid,
                DiscordAccount.verified == True,
                DiscordAccount.discord_id != body.discord_id,
            )
        )
    )
    if existing_for_player.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="This Minecraft account is already linked to a different Discord account."
        )

    if account:
        if account.verified and account.player_uuid == verification_code.player_uuid:
            # Already linked to this exact pair — treat as idempotent success, no changes needed
            pass
        else:
            account.player_uuid = verification_code.player_uuid
            account.verified = True
            account.linked_at = datetime.utcnow()
            account.discord_username = body.discord_username
    else:
        account = DiscordAccount(
            discord_id=body.discord_id,
            player_uuid=verification_code.player_uuid,
            verified=True,
            linked_at=datetime.utcnow(),
            discord_username=body.discord_username,
        )
        db.add(account)

    # Nickname sync: done, but not here - see bot/cogs/verification_cog.py's
    # _sync_nickname() in umbrella-discord. This router predates the
    # Capability Registry (raw HTTPException, X-Admin-Key - see
    # services/verification/service.py's module docstring) and was left
    # untouched deliberately when Phase 6 built the real fix on
    # capabilities/verification.py's verification.confirm instead. That
    # capability's handler still can't do the nickname edit itself either
    # (no live Discord gateway in umbrella-core's process, same reason
    # this TODO originally gave) - the caller (umbrella-discord's
    # verification_cog.py, after a successful verification.confirm call)
    # does it, using its own bot connection: guild.get_member(discord_id)
    # .edit(nick=player_username), wrapped in its own try/except so a
    # nickname-permission failure never blocks verification itself.

    
    # Create audit log entry
    audit_log = AuditLog(
        actor=body.discord_username,
        actor_type="bot",
        action="verification.completed",
        target=verification_code.player_username,
        details_json='{}',
    )
    db.add(audit_log)
    
    await db.flush()
    
    return VerificationConfirmResponse(
        success=True,
        player_uuid=verification_code.player_uuid,
        player_username=verification_code.player_username,
    )


@router.post("/status", response_model=VerificationStatusResponse)
async def verification_status(
    body: VerificationStatusRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
) -> VerificationStatusResponse:
    """Check if a player is verified."""
    result = await db.execute(
        select(DiscordAccount).where(
            and_(
                DiscordAccount.player_uuid == body.player_uuid,
                DiscordAccount.verified == True
            )
        )
    )
    account = result.scalar_one_or_none()
    
    if account:
        return VerificationStatusResponse(
            verified=True,
            discord_id=account.discord_id,
            discord_username=account.discord_username,
        )
    
    return VerificationStatusResponse(verified=False)


@router.get("/pending", response_model=list[VerificationCodeSchema])
async def list_pending_verifications(
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.view")),
) -> list[VerificationCodeSchema]:
    """List players waiting for verification."""
    result = await db.execute(
        select(VerificationCode).where(
            and_(
                VerificationCode.used == False,
                VerificationCode.expires_at > datetime.utcnow()
            )
        )
    )
    codes = result.scalars().all()
    
    return [VerificationCodeSchema.model_validate(c) for c in codes]


@router.post("/revoke")
async def revoke_verification(
    body: VerificationRevokeRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_permission("players.manage")),
):
    """Revoke a player's verification."""
    result = await db.execute(
        select(DiscordAccount).where(DiscordAccount.player_uuid == body.player_uuid)
    )
    account = result.scalar_one_or_none()
    
    if account:
        account.verified = False
        
        # Create audit log entry
        audit_log = AuditLog(
            actor="system",
            actor_type="system",
            action="verification.revoked",
            target=account.player_uuid,
            details_json='{}',
        )
        db.add(audit_log)
        await db.flush()
    
    return {"success": True}


class ManualLinkRequest(BaseModel):
    discord_id: str
    mc_username: str


@router.post("/manual-link")
async def manual_link(
    body: ManualLinkRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """Manually link a Discord ID to a Minecraft username.
    Creates a placeholder player record if one doesn't exist yet.
    UUID gets updated to the real value on the player's next join.
    """
    from models import Player
    import uuid as uuid_lib

    # Find or create a Player record for this username
    player = await db.scalar(select(Player).where(Player.username == body.mc_username))
    if player is None:
        # Create a placeholder — the plugin will overwrite the UUID on first join
        placeholder_uuid = f"manual-{uuid_lib.uuid4()}"
        player = Player(
            uuid=placeholder_uuid,
            username=body.mc_username,
        )
        db.add(player)
        await db.flush()
    
    player_uuid = player.uuid

    # Find or update the DiscordAccount record
    existing = await db.scalar(
        select(DiscordAccount).where(DiscordAccount.discord_id == body.discord_id)
    )
    if existing:
        existing.verified = True
        existing.player_uuid = player_uuid
        existing.linked_at = datetime.utcnow()
        existing.discord_username = existing.discord_username or body.discord_id
    else:
        existing = DiscordAccount(
            discord_id=body.discord_id,
            player_uuid=player_uuid,
            verified=True,
            linked_at=datetime.utcnow(),
            discord_username=body.discord_id,
        )
        db.add(existing)

    audit = AuditLog(
        actor="staff",
        actor_type="staff",
        action="verification.manual_link",
        target=body.mc_username,
        details_json=f'{{"discord_id": "{body.discord_id}", "player_uuid": "{player_uuid}"}}',
    )
    db.add(audit)
    await db.flush()
    return {"success": True, "message": f"Linked {body.discord_id} to {body.mc_username}. UUID resolves on next join."}


@router.delete("/unlink/{discord_id}")
async def unlink_account(
    discord_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """Remove the Discord<->Minecraft link for a Discord user."""
    account = await db.scalar(
        select(DiscordAccount).where(DiscordAccount.discord_id == discord_id)
    )
    if not account:
        raise HTTPException(status_code=404, detail="No linked account found for that Discord ID")

    account.verified = False
    account.player_uuid = None
    account.linked_at = None

    audit = AuditLog(
        actor="staff",
        actor_type="staff",
        action="verification.manual_unlink",
        target=discord_id,
        details_json="{}",
    )
    db.add(audit)
    await db.flush()
    return {"success": True}


class ResolvePendingRequest(BaseModel):
    uuid: str
    username: str


@router.post("/resolve-pending")
async def resolve_pending(
    body: ResolvePendingRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_admin_key),
):
    """Called by the plugin on every join. If a DiscordAccount is sitting at
    player_uuid == 'pending:<username>' (case-insensitive) and this player's
    username matches, swap the placeholder for their real UUID."""
    from sqlalchemy import func as sqlfunc

    pending_marker = f"pending:{body.username}"
    account = await db.scalar(
        select(DiscordAccount).where(
            sqlfunc.lower(DiscordAccount.player_uuid) == sqlfunc.lower(pending_marker)
        )
    )
    if not account:
        return {"resolved": False}

    account.player_uuid = body.uuid
    audit = AuditLog(
        actor="system",
        actor_type="plugin",
        action="verification.pending_resolved",
        target=body.username,
        details_json=f'{{"discord_id": "{account.discord_id}", "uuid": "{body.uuid}"}}',
    )
    db.add(audit)
    await db.flush()
    return {"resolved": True, "discord_id": account.discord_id}


class VerificationLinkSchema(BaseModel):
    id: int
    discord_id: str
    discord_username: str | None
    minecraft_uuid: str | None
    minecraft_username: str | None
    linked_at: datetime | None
    verified_by: str
    status: str

    class Config:
        from_attributes = True


@router.get("/links", response_model=list[VerificationLinkSchema])
async def list_verification_links(
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("players.view")),
) -> list[VerificationLinkSchema]:
    """List all verified Discord<->Minecraft account links.

    The dashboard's VerificationView calls this to populate the verified
    links table. Queries DiscordAccount rows and enriches with player usernames.
    """
    from models import Player

    result = await db.execute(
        select(DiscordAccount)
        .order_by(DiscordAccount.linked_at.desc().nulls_last())
        .offset(offset)
        .limit(limit)
    )
    accounts = result.scalars().all()

    if not accounts:
        return []

    # Bulk-load player usernames
    uuids = [a.player_uuid for a in accounts if a.player_uuid]
    player_map: dict[str, str] = {}
    if uuids:
        pr = await db.execute(select(Player).where(Player.uuid.in_(uuids)))
        for p in pr.scalars().all():
            player_map[p.uuid] = p.username

    links = []
    for acct in accounts:
        if acct.verified:
            status = "VERIFIED"
        else:
            status = "PENDING_CODE"

        links.append(VerificationLinkSchema(
            id=acct.id,
            discord_id=acct.discord_id,
            discord_username=acct.discord_username,
            minecraft_uuid=acct.player_uuid,
            minecraft_username=player_map.get(acct.player_uuid) if acct.player_uuid else None,
            linked_at=acct.linked_at,
            verified_by="BOT_CODE",  # all current links are bot-code verified; manual adds via /manual-link
            status=status,
        ))

    return links
