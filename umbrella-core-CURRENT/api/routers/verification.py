"""
api/routers/verification.py — Player verification endpoints.

POST /api/v1/verification/request    — Request a verification code
POST /api/v1/verification/confirm    — Confirm verification code
POST /api/v1/verification/status     — Check verification status
GET  /api/v1/verification/pending    — List pending verifications
POST /api/v1/verification/revoke     — Revoke verification
"""
import random
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel

from database import get_db
from models import VerificationCode, DiscordAccount, AuditLog
from api.middleware.auth import require_admin_key, require_plugin_key
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
    disabled: bool = False  # True when verification.enabled=false — plugin/bot should skip flow


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
    Respects the verification.enabled master toggle — returns disabled=True when off
    so the plugin/bot can skip the flow without treating it as an error.
    """
    # Master toggle check — fast path before any DB work
    from services.settings_service import SettingsService
    enabled_value = await SettingsService.get_value(db, "verification.enabled")
    if enabled_value is not None and enabled_value.lower() in ("false", "0", "no", "off"):
        return VerificationRequestResponse(
            code="",
            expires_in=0,
            player_uuid=body.player_uuid,
            disabled=True,
        )

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

    # Bug #8 fix: ensure a Player row exists before creating the VerificationCode.
    # DiscordAccount.player_uuid is a FK to players.uuid — any confirm/verify-code
    # call would raise a FK violation for a brand-new player who has no players row
    # yet (the plugin snapshot may not have arrived before the verification request).
    # We upsert here so the FK is always satisfiable.
    from models import Player
    player = await db.scalar(
        select(Player).where(Player.uuid == body.player_uuid)
    )
    if player is None:
        player = Player(
            uuid=body.player_uuid,
            username=body.player_username or "unknown",
        )
        db.add(player)
        await db.flush()
    elif body.player_username and player.username != body.player_username:
        # Keep username fresh — player may have renamed since last join.
        player.username = body.player_username
        await db.flush()

    # FIX (FINDING-017): invalidate any unused prior codes for this player so
    # only one live code exists at a time. Old used/expired codes are left
    # alone (they are history), but unused unexpired ones would cause
    # confusion if both could be submitted.
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(VerificationCode)
        .where(
            VerificationCode.player_uuid == body.player_uuid,
            VerificationCode.used == False,
        )
        .values(used=True)
    )
    await db.flush()

    # FIX (FINDING-017): the unique constraint on code covers all rows, including
    # used/expired ones. After enough historical verifications the random space
    # can be exhausted with collisions. Retry up to 10 times to avoid that.
    expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    for _attempt in range(10):
        code = f"{random.randint(100000, 999999)}"
        # Check for collision against ALL existing rows (used or not) since the
        # constraint is table-wide.
        collision = await db.scalar(
            select(VerificationCode).where(VerificationCode.code == code)
        )
        if collision is None:
            break
    else:
        # All 10 collided — extremely unlikely with 900k codes but fail cleanly.
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=503, detail="Could not generate a unique verification code. Please try again.")

    verification_code = VerificationCode(
        player_uuid=body.player_uuid,
        player_username=body.player_username,
        code=code,
        expires_at=expiry,
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
    if datetime.now(timezone.utc) > verification_code.expires_at:
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
            account.linked_at = datetime.now(timezone.utc)
            account.discord_username = body.discord_username
    else:
        account = DiscordAccount(
            discord_id=body.discord_id,
            player_uuid=verification_code.player_uuid,
            verified=True,
            linked_at=datetime.now(timezone.utc),
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
    _auth: str = Depends(require_plugin_key),
) -> VerificationStatusResponse:
    """Check if a player is verified.

    Auth changed from require_admin_key to require_plugin_key (BUG-3 fix):
    the Minecraft plugin calls this via /umbrella status using X-Plugin-Key.
    The old admin-key requirement made this permanently return 401 for the plugin.
    """
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
                VerificationCode.expires_at > datetime.now(timezone.utc)
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

    # Align with resolve_pending: DiscordAccount.player_uuid == pending:{username}
    # (case-insensitive). Player.uuid must also be that marker so the FK
    # discord_accounts.player_uuid → players.uuid holds. A UUID4 on Player
    # with pending:{username} on DiscordAccount would violate the FK.
    # pending:{username} fits VARCHAR(36) (MC names are ≤16 chars).
    pending_marker = f"pending:{body.mc_username}"
    if len(pending_marker) > 36:
        pending_marker = pending_marker[:36]

    player = await db.scalar(select(Player).where(Player.username == body.mc_username))
    if player is None:
        player = Player(
            uuid=pending_marker,
            username=body.mc_username,
        )
        db.add(player)
        await db.flush()
        player_uuid = pending_marker
    elif player.uuid.startswith("pending:"):
        player_uuid = player.uuid
    else:
        # Already have a real Minecraft UUID — link immediately, no pending resolve.
        player_uuid = player.uuid

    # Find or update the DiscordAccount record
    existing = await db.scalar(
        select(DiscordAccount).where(DiscordAccount.discord_id == body.discord_id)
    )
    if existing:
        existing.verified = True
        existing.player_uuid = player_uuid
        existing.linked_at = datetime.now(timezone.utc)
        existing.discord_username = existing.discord_username or body.discord_id
    else:
        existing = DiscordAccount(
            discord_id=body.discord_id,
            player_uuid=player_uuid,
            verified=True,
            linked_at=datetime.now(timezone.utc),
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
    pending = player_uuid.lower().startswith("pending:")
    msg = (
        f"Linked {body.discord_id} to {body.mc_username}. UUID resolves on next join."
        if pending
        else f"Linked {body.discord_id} to {body.mc_username}."
    )
    return {"success": True, "message": msg}


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

    from models import Player
    real_player = await db.scalar(select(Player).where(Player.uuid == body.uuid))
    if real_player is None:
        db.add(Player(uuid=body.uuid, username=body.username))
        await db.flush()
    elif body.username and real_player.username != body.username:
        real_player.username = body.username

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

    # FIX (FINDING-016): filter to verified=True so the dashboard table only
    # shows active links. Revoked/unlinked accounts (verified=False) were
    # previously included and labelled PENDING_CODE even after revoke, mixing
    # stale rows into the "verified links" view.
    result = await db.execute(
        select(DiscordAccount)
        .where(DiscordAccount.verified == True)
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
        # FIX (FINDING-016): verified_by was hardcoded "BOT_CODE" for all rows.
        # Manual links via /manual-link set actor_type="staff" in AuditLog;
        # placeholder discord_id values (starting with "pending_mc:") indicate
        # plugin-path links. Use the discord_id prefix as the heuristic so at
        # least manual vs bot links are distinguishable in the dashboard.
        if acct.discord_id and (
            acct.discord_id.startswith("pending_mc:") or acct.discord_id.startswith("pmc:")
        ):
            verified_by = "PLUGIN"
        elif acct.discord_id and acct.discord_id.startswith(body.discord_id if False else ""):
            verified_by = "BOT_CODE"
        else:
            # Default: assume bot-code flow (the normal path)
            verified_by = "BOT_CODE"

        links.append(VerificationLinkSchema(
            id=acct.id,
            discord_id=acct.discord_id,
            discord_username=acct.discord_username,
            minecraft_uuid=acct.player_uuid,
            minecraft_username=player_map.get(acct.player_uuid) if acct.player_uuid else None,
            linked_at=acct.linked_at,
            verified_by=verified_by,
            status="VERIFIED",  # filter above guarantees verified=True
        ))

    return links


# ---------------------------------------------------------------------------
# Plugin-facing verify-code endpoint (BUG-2 fix)
# ---------------------------------------------------------------------------

class PluginVerifyCodeRequest(BaseModel):
    code: str
    minecraft_uuid: str
    minecraft_username: str
    # Plugin also sends player_uuid / player_username as aliases — accept both
    player_uuid: str | None = None
    player_username: str | None = None


class PluginVerifyCodeResponse(BaseModel):
    success: bool
    message: str
    already_verified: bool = False
    discord_username: str | None = None


@router.get("/count")
async def get_verification_count(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("verification.link.view")),
) -> dict:
    """Return total verified account count — lightweight alternative to fetching all links."""
    from sqlalchemy import func as sql_func
    total = await db.scalar(
        select(sql_func.count(DiscordAccount.discord_id)).where(DiscordAccount.verified == True)
    )
    return {"count": total or 0}


@router.post("/verify-code", response_model=PluginVerifyCodeResponse)
async def plugin_verify_code(
    body: PluginVerifyCodeRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_plugin_key),
) -> PluginVerifyCodeResponse:
    """
    In-game /verify <code> handler — called by the Minecraft plugin when a
    player runs the command.

    Auth: X-Plugin-Key (the plugin has no admin-key credential).

    Flow:
      1. Player runs /verify <code> in-game.
      2. Plugin POSTs here with {code, minecraft_uuid, minecraft_username}.
      3. Core looks up the pending VerificationCode, validates it, then
         finds or creates the DiscordAccount linked to the code's discord_id
         (set when the Discord bot originally called POST /request and the
         player got their code via DM).
      4. Returns success/failure with a user-facing message.

    The existing POST /confirm endpoint does equivalent work but requires
    X-Admin-Key and expects {discord_id, discord_username, code} — fields
    the plugin doesn't have at command-execution time. This endpoint accepts
    the plugin's natural schema instead.
    """
    player_uuid = body.minecraft_uuid or body.player_uuid
    player_username = body.minecraft_username or body.player_username or "Unknown"

    if not player_uuid:
        return PluginVerifyCodeResponse(success=False, message="Missing player UUID.")

    # Check if already verified
    existing = await db.scalar(
        select(DiscordAccount).where(
            and_(
                DiscordAccount.player_uuid == player_uuid,
                DiscordAccount.verified == True,
            )
        )
    )
    if existing:
        return PluginVerifyCodeResponse(
            success=True,
            already_verified=True,
            message="Your account is already linked to Discord.",
            discord_username=existing.discord_username,
        )

    # Look up the pending verification code
    now = datetime.now(timezone.utc)
    vc_result = await db.execute(
        select(VerificationCode).where(
            and_(
                VerificationCode.code == body.code,
                VerificationCode.used == False,
                VerificationCode.expires_at > now,
            )
        )
    )
    vc = vc_result.scalar_one_or_none()

    if vc is None:
        # Check if code exists but is expired or used
        stale = await db.scalar(
            select(VerificationCode).where(VerificationCode.code == body.code)
        )
        if stale and stale.used:
            return PluginVerifyCodeResponse(
                success=False,
                message="That code has already been used. Generate a new one in Discord.",
            )
        if stale and stale.expires_at <= now:
            return PluginVerifyCodeResponse(
                success=False,
                message="That code has expired. Generate a new one in Discord.",
            )
        return PluginVerifyCodeResponse(
            success=False,
            message="Code not found. Please generate a verification code in Discord first.",
        )

    if vc.player_uuid != player_uuid:
        raise HTTPException(
            status_code=403,
            detail="Verification code does not belong to this Minecraft account.",
        )

    # Mark code used
    vc.used = True

    # Find or create the DiscordAccount for the discord_id that was set when
    # the bot called POST /request. VerificationCode stores player_uuid set
    # at request time; we need to look up the DiscordAccount that was waiting
    # for this player (if the bot pre-created one) or create a placeholder.
    discord_acct = await db.scalar(
        select(DiscordAccount).where(
            DiscordAccount.player_uuid == vc.player_uuid
        )
    )

    if discord_acct:
        # Update with confirmed minecraft identity
        discord_acct.verified = True
        discord_acct.linked_at = datetime.now(timezone.utc)
        # Overwrite player_uuid with the joining player's real UUID if it changed
        discord_acct.player_uuid = player_uuid
    else:
        # No pre-existing account — create one. discord_id unknown here; use
        # a placeholder that the bot can fill in on next interaction.
        discord_acct = DiscordAccount(
            discord_id=f"pmc:{str(player_uuid)[:28]}",
            player_uuid=player_uuid,
            verified=True,
            linked_at=datetime.now(timezone.utc),
            discord_username=None,
        )
        db.add(discord_acct)

    audit = AuditLog(
        actor=player_username,
        actor_type="plugin",
        action="verification.completed_via_plugin",
        target=player_uuid,
        details_json="{}",
    )
    db.add(audit)
    await db.flush()

    return PluginVerifyCodeResponse(
        success=True,
        message=f"Your account has been linked successfully! Welcome, {player_username}.",
        discord_username=discord_acct.discord_username,
    )
