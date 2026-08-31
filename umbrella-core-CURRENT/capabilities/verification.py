"""
capabilities/verification.py — Exposes verification confirmation/status as
proper capabilities, closing the gap flagged during umbrella-discord's
Phase 6 buildout: api/routers/verification.py's endpoints predate the
Capability Registry entirely and require X-Admin-Key (full superuser
access, see api/middleware/auth.py's require_admin_key), which
UmbrellaCoreClient has no way to reach and should not be handed even if it
could - see services/verification/service.py's own module docstring for
the full reasoning on why this wraps NEW service code rather than
refactoring the router in place.

Originally just `confirm` and `status` - the two operations Discord
verification wiring needed at the time (a member DMs their code, the bot
confirms it; the bot or a staff command checks link status). `link_by_discord`
was added afterward to close a *different*, separately-flagged gap: a
reverse lookup (given a Discord user, find their linked player_uuid) that
umbrella-discord's player_risk_cog.py needed and had no structured path to
- see get_link_by_discord()'s own docstring in
services/verification/service.py. `request` and `resolve-pending` are
still Minecraft-plugin-only, and staff-only account management
(`pending`/`revoke`/`manual-link`/`unlink`) is still dashboard territory -
neither has needed capability wrapping yet.

Deliberately NOT gated behind "players.manage"/"players.view" (the
permissions the legacy router's sibling `pending`/`revoke` endpoints use):
those also gate the full /players CRUD API and are owner/admin-only in
DEFAULT_ROLES (see services/roles_service.py). confirm() is a routine,
high-frequency machine action - the bot calls it once per player who DMs
a code - and needs its own narrowly-scoped permission an API key can be
granted directly, without also handing that key player-record-editing
rights. Added "verification.link.manage"/"verification.link.view" to
DEFAULT_PERMISSIONS for this reason, granted to moderator (both) and
helper (view only) at the same risk tier as their existing view/action
permissions.

Nickname sync (the actual TODO in confirm_verification()) is deliberately
NOT implemented here, and can't be: this capability's handler runs inside
umbrella-core, which has no live Discord gateway connection (same
structural fact already noted in services/moderation_intelligence/service.py's
docstring re: maybe_auto_apply()). The fix is symmetric to that one: the
Discord-side caller (umbrella-discord's verification cog, once built) sets
the member's nickname itself, using its own live bot connection, right
after this capability returns success - not something core can do on its
own behalf.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from api.validators import validate_player_uuid
from registry.context import CallContext
from registry.decorator import capability
from services.verification.service import confirm_verification, get_link_by_discord, get_verification_status


class ConfirmVerificationParams(BaseModel):
    discord_id: str = Field(description="The Discord user's snowflake ID")
    discord_username: str = Field(description="The Discord user's current username, for the audit log and DiscordAccount record")
    code: str = Field(description="The 6-digit code the player received in-game")

    def audit_target(self) -> str:
        return self.discord_id


class ConfirmVerificationResult(BaseModel):
    player_uuid: str
    player_username: str
    already_linked: bool


@capability(
    name="verification.confirm",
    summary="Confirm a player's verification code, linking their Discord account to their Minecraft player.",
    params_model=ConfirmVerificationParams,
    result_model=ConfirmVerificationResult,
    required_permission="verification.link.manage",
    destructive=False,
)
async def confirm(ctx: CallContext, params: ConfirmVerificationParams) -> ConfirmVerificationResult:
    result = await confirm_verification(
        ctx.db,
        discord_id=params.discord_id,
        discord_username=params.discord_username,
        code=params.code,
        actor=ctx.actor_id,
    )
    return ConfirmVerificationResult(
        player_uuid=result.player_uuid,
        player_username=result.player_username,
        already_linked=result.already_linked,
    )


class VerificationStatusParams(BaseModel):
    player_uuid: str = Field(description="The Minecraft player's UUID")

    # FIX (master bug report #17): same validation as
    # api/routers/verification.py's request models — see
    # api/validators.py::validate_player_uuid for the full rationale.
    _validate_uuid = field_validator("player_uuid")(validate_player_uuid)


class VerificationStatusResult(BaseModel):
    verified: bool
    discord_id: str | None
    discord_username: str | None


class LinkByDiscordParams(BaseModel):
    discord_id: str = Field(description="The Discord user's snowflake ID")


class LinkByDiscordResult(BaseModel):
    linked: bool
    player_uuid: str | None
    player_username: str | None


@capability(
    name="verification.link.by_discord",
    summary="Resolve a Discord user to their linked Minecraft player, if any.",
    params_model=LinkByDiscordParams,
    result_model=LinkByDiscordResult,
    required_permission="verification.link.view",
    destructive=False,
    audited=False,
)
async def link_by_discord(ctx: CallContext, params: LinkByDiscordParams) -> LinkByDiscordResult:
    """Closes the gap flagged in umbrella-discord's player_risk_cog.py:
    the only prior Discord-id -> player_uuid path was investigation's
    LinkedAccountTool, which returns a human sentence, not a structured
    value safe to chain into another capability call. This is the
    structured equivalent - see services/verification/service.py's
    get_link_by_discord() docstring for the query itself."""
    result = await get_link_by_discord(ctx.db, discord_id=params.discord_id)
    return LinkByDiscordResult(
        linked=result.linked,
        player_uuid=result.player_uuid,
        player_username=result.player_username,
    )


@capability(
    name="verification.status",
    summary="Check whether a player is verified, and if so, which Discord account they're linked to.",
    params_model=VerificationStatusParams,
    result_model=VerificationStatusResult,
    required_permission="verification.link.view",
    destructive=False,
    audited=False,
)
async def status(ctx: CallContext, params: VerificationStatusParams) -> VerificationStatusResult:
    result = await get_verification_status(ctx.db, player_uuid=params.player_uuid)
    return VerificationStatusResult(
        verified=result.verified,
        discord_id=result.discord_id,
        discord_username=result.discord_username,
    )
