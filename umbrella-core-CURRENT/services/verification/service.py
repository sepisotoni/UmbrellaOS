"""
services/verification/service.py — Verification business logic, usable by
the Capability Registry (capabilities/verification.py).

This is new code, not a refactor of api/routers/verification.py's existing
confirm_verification()/verification_status() handlers, and that's a
deliberate risk-reduction choice, not an oversight: the router's endpoints
predate the AppException/@capability pattern entirely (they raise raw
FastAPI HTTPException, which api/middleware/errors.py's register_error_handlers
does NOT intercept - there is no @app.exception_handler(HTTPException)
override, only AppException and a catch-all Exception. So the router's
`/confirm` currently replies with FastAPI's default
`{"detail": "..."}` shape at whatever status code the HTTPException carries
(400/404/409), a different wire shape from every capability-driven
endpoint, which raises AppException subclasses caught by the AppException
handler into `{"success": false, "error": ..., "code": ..., ...}` - the
exact shape UmbrellaCoreClient (umbrella-discord's HTTP bridge) already
parses.

Refactoring the router to call this service would either (a) change the
router's existing wire behavior for whatever already depends on it, or (b)
require this service to speak two different error vocabularies depending
on caller, which is worse than a small amount of duplication. So: the
router is left completely untouched, and this service is a fresh,
independently-tested implementation of the same rules, built for the
capability system's error conventions from the start. Both read from/write
to the same tables (VerificationCode, DiscordAccount, AuditLog) - there is
one source of truth in the database, just two call paths into it for now.
Collapsing that duplication later, once it's clear nothing outside this
project still depends on the router's exact legacy response shape, is a
reasonable follow-up - not done here.

Business rules mirrored exactly from api/routers/verification.py's
confirm_verification()/verification_status(): code must exist, be
unexpired, be unused; a Discord account already verified+linked to a
different player cannot be relinked; a player already verified+linked to
a different Discord account blocks the new link; re-confirming the exact
same already-linked pair is treated as an idempotent success.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import (
    AppException,
    ConflictException,
    ValidationException,
)
from models import AuditLog, DiscordAccount, VerificationCode
from services.settings_service import SettingsService

_DEFAULT_MESSAGES = {
    "verification.success_message": (
        "\u2705 Your Minecraft account **$PLAYER** has been successfully linked!"
    ),
    "verification.error_already_linked": (
        "\u274c This Discord account is already linked to a Minecraft account."
    ),
    "verification.error_invalid_code": (
        "\u274c Invalid or expired code. Please run /verify in-game again."
    ),
}


async def _verification_message(
    db: AsyncSession, key: str, **values: str
) -> str:
    template = await SettingsService.get_value(db, key)
    if not template or not template.strip():
        template = _DEFAULT_MESSAGES[key]
    for name, value in values.items():
        template = template.replace(f"${name.upper()}", value)
    return template


@dataclass(frozen=True)
class ConfirmResult:
    player_uuid: str
    player_username: str
    already_linked: (
        bool  # True for the idempotent re-confirm case — no DB write happened
    )
    discord_message: str


@dataclass(frozen=True)
class StatusResult:
    verified: bool
    discord_id: str | None
    discord_username: str | None


async def confirm_verification(
    db: AsyncSession,
    *,
    discord_id: str,
    discord_username: str,
    code: str,
    actor: str,
) -> ConfirmResult:
    """Confirm a verification code, linking a Discord account to a
    Minecraft player. `actor` is written to the audit log exactly like the
    router's version does (there, `body.discord_username`) - for a
    capability call this is ctx's resolved identity, not a Discord-supplied
    field, which is a small correctness improvement: the router trusts
    whatever discord_username the caller sends for its own audit row,
    while a capability's audit row is written by CapabilityRegistry.call()
    from ctx.actor_id independently of this function - `actor` here is
    only for this function's own extra verification.completed audit row,
    kept for parity with the router's behavior.
    """
    enabled = await SettingsService.get_value(db, "verification.enabled")
    if enabled is not None and enabled.strip().lower() in ("false", "0", "no", "off"):
        raise AppException(
            "Verification is disabled.",
            "VERIFICATION_DISABLED",
            409,
        )

    result = await db.execute(
        select(VerificationCode).where(VerificationCode.code == code)
    )
    verification_code = result.scalar_one_or_none()

    if not verification_code:
        raise AppException(
            await _verification_message(db, "verification.error_invalid_code"),
            "NOT_FOUND",
            404,
        )

    # FIX: expires_at is DateTime(timezone=True) in Postgres, always tz-aware
    # on read there. SQLite (tests, local dev) drops tzinfo on write, coming
    # back naive. Normalize before comparing so this doesn't raise
    # 'can't compare offset-naive and offset-aware datetimes' depending on
    # which DB backend is in play. Same fix as api/routers/verification.py's
    # _aware() helper — this module has its own single call site so a local
    # inline normalize is clearer than importing across the router boundary.
    expires_at = verification_code.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        raise ValidationException(
            await _verification_message(db, "verification.error_invalid_code")
        )

    if verification_code.used:
        raise ValidationException(
            await _verification_message(db, "verification.error_invalid_code")
        )

    verification_code.used = True

    existing_account = await db.execute(
        select(DiscordAccount).where(DiscordAccount.discord_id == discord_id)
    )
    account = existing_account.scalar_one_or_none()

    if (
        account
        and account.verified
        and account.player_uuid
        and account.player_uuid != verification_code.player_uuid
    ):
        raise ConflictException(
            await _verification_message(db, "verification.error_already_linked")
        )

    existing_for_player = await db.execute(
        select(DiscordAccount).where(
            and_(
                DiscordAccount.player_uuid == verification_code.player_uuid,
                DiscordAccount.verified == True,  # noqa: E712 — matches the existing SQLAlchemy filter style in this codebase
                DiscordAccount.discord_id != discord_id,
            )
        )
    )
    if existing_for_player.scalar_one_or_none():
        raise ConflictException(
            await _verification_message(db, "verification.error_already_linked")
        )

    already_linked = False
    if account:
        if account.verified and account.player_uuid == verification_code.player_uuid:
            already_linked = True
        else:
            account.player_uuid = verification_code.player_uuid
            account.verified = True
            account.linked_at = datetime.now(timezone.utc)
            account.discord_username = discord_username
    else:
        account = DiscordAccount(
            discord_id=discord_id,
            player_uuid=verification_code.player_uuid,
            verified=True,
            linked_at=datetime.now(timezone.utc),
            discord_username=discord_username,
        )
        db.add(account)

    db.add(
        AuditLog(
            actor=actor,
            actor_type="bot",
            action="verification.completed",
            target=verification_code.player_username,
            details_json="{}",
        )
    )
    await db.flush()

    if already_linked:
        discord_message = (
            f"\u2705 You're already verified as **{verification_code.player_username}**."
        )
    else:
        discord_message = await _verification_message(
            db,
            "verification.success_message",
            player=verification_code.player_username,
        )

    return ConfirmResult(
        player_uuid=verification_code.player_uuid,
        player_username=verification_code.player_username,
        already_linked=already_linked,
        discord_message=discord_message,
    )


@dataclass(frozen=True)
class LinkByDiscordResult:
    linked: bool
    player_uuid: str | None
    player_username: str | None


async def get_link_by_discord(
    db: AsyncSession, *, discord_id: str
) -> LinkByDiscordResult:
    """Reverse of get_verification_status: given a Discord ID, resolve the
    linked player_uuid (if any). Added to close the gap flagged in
    umbrella-discord's player_risk_cog.py - the only prior path from a
    Discord user to a player_uuid was investigation's LinkedAccountTool,
    which returns a human-readable sentence, not a structured value.
    `discord_id` is unique+indexed on DiscordAccount (see models/discord.py),
    so this is a single indexed lookup, same cost as get_verification_status's
    reverse direction.

    Returns player_username by joining to Player - callers (a Discord
    command formatting a reply) generally want a display name, not just a
    UUID, and Player.username is the natural source for it rather than
    asking every caller to make a second query.
    """
    from models import Player

    result = await db.execute(
        select(DiscordAccount, Player)
        .join(Player, Player.uuid == DiscordAccount.player_uuid, isouter=True)
        .where(
            and_(
                DiscordAccount.discord_id == discord_id, DiscordAccount.verified == True
            )
        )  # noqa: E712
    )
    row = result.first()
    if not row:
        return LinkByDiscordResult(linked=False, player_uuid=None, player_username=None)

    account, player = row
    return LinkByDiscordResult(
        linked=True,
        player_uuid=account.player_uuid,
        player_username=player.username if player else None,
    )


async def get_verification_status(
    db: AsyncSession, *, player_uuid: str
) -> StatusResult:
    result = await db.execute(
        select(DiscordAccount).where(
            and_(
                DiscordAccount.player_uuid == player_uuid,
                DiscordAccount.verified == True,
            )  # noqa: E712
        )
    )
    account = result.scalar_one_or_none()
    if account:
        return StatusResult(
            verified=True,
            discord_id=account.discord_id,
            discord_username=account.discord_username,
        )
    return StatusResult(verified=False, discord_id=None, discord_username=None)
