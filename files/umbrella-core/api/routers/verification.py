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
from fastapi import APIRouter, Depends, HTTPException
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
    
    # Create or update DiscordAccount
    existing_account = await db.execute(
        select(DiscordAccount).where(DiscordAccount.discord_id == body.discord_id)
    )
    account = existing_account.scalar_one_or_none()
    
    if account:
        # Update existing account
        account.player_uuid = verification_code.player_uuid
        account.verified = True
        account.linked_at = datetime.utcnow()
        account.discord_username = body.discord_username
    else:
        # Create new account
        account = DiscordAccount(
            discord_id=body.discord_id,
            player_uuid=verification_code.player_uuid,
            verified=True,
            linked_at=datetime.utcnow(),
            discord_username=body.discord_username,
        )
        db.add(account)
    
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
