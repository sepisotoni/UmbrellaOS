"""
capabilities/identity.py — Phase 3's identity domain: API key management
and MFA enrollment, exposed through the Capability Registry.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy import select

from models.user import User
from registry.context import CallContext
from registry.decorator import capability
from services.api_key_service import ApiKeyService
from services.mfa_service import MFAError, MFAService

# --------------------------------------------------------------------------
# identity.apikey.*
# --------------------------------------------------------------------------


class CreateApiKeyParams(BaseModel):
    name: str
    permissions: list[str] = Field(default_factory=list)
    expires_in_days: int | None = None


class ApiKeyResult(BaseModel):
    id: str
    name: str
    key_prefix: str
    permissions: list[str]
    revoked: bool
    plaintext_key: str | None = None  # only populated on creation — see create_api_key's docstring

    @classmethod
    def from_model(cls, key, plaintext: str | None = None) -> "ApiKeyResult":
        return cls(
            id=key.id, name=key.name, key_prefix=key.key_prefix,
            permissions=key.permissions, revoked=key.revoked, plaintext_key=plaintext,
        )


@capability(
    name="identity.apikey.create",
    summary="Create a new scoped API key for machine-to-machine access.",
    params_model=CreateApiKeyParams,
    result_model=ApiKeyResult,
    required_permission="identity.apikey.manage",
    destructive=False,
    audit_category="identity",
)
async def create_api_key(ctx: CallContext, params: CreateApiKeyParams) -> ApiKeyResult:
    """The returned `plaintext_key` is shown exactly once, here — it is not
    recoverable afterward. `identity.apikey.list` never includes it."""
    created_by = None
    if ctx.actor_type == "staff":
        result = await ctx.db.execute(select(User).where(User.discord_id == ctx.actor_id))
        user = result.scalar_one_or_none()
        created_by = user.id if user else None

    key, plaintext = await ApiKeyService.create_api_key(
        ctx.db, params.name, params.permissions, created_by=created_by, expires_in_days=params.expires_in_days
    )
    return ApiKeyResult.from_model(key, plaintext=plaintext)


class ListApiKeysParams(BaseModel):
    pass


@capability(
    name="identity.apikey.list",
    summary="List every API key (never includes the plaintext value).",
    params_model=ListApiKeysParams,
    result_model=list[ApiKeyResult],
    required_permission="identity.apikey.manage",
    destructive=False,
    audited=False,
)
async def list_api_keys(ctx: CallContext, params: ListApiKeysParams) -> list[ApiKeyResult]:
    keys = await ApiKeyService.list_api_keys(ctx.db)
    return [ApiKeyResult.from_model(k) for k in keys]


class RevokeApiKeyParams(BaseModel):
    api_key_id: str

    def audit_target(self) -> str:
        return self.api_key_id


class RevokeApiKeyResult(BaseModel):
    revoked: bool


@capability(
    name="identity.apikey.revoke",
    summary="Revoke an API key permanently.",
    params_model=RevokeApiKeyParams,
    result_model=RevokeApiKeyResult,
    required_permission="identity.apikey.manage",
    destructive=True,
    reversible=False,
    audit_category="identity",
)
async def revoke_api_key(ctx: CallContext, params: RevokeApiKeyParams) -> RevokeApiKeyResult:
    await ApiKeyService.revoke_api_key(ctx.db, params.api_key_id)
    return RevokeApiKeyResult(revoked=True)


# --------------------------------------------------------------------------
# identity.mfa.* — always acts on the calling staff member themselves, not
# an arbitrary target user. MFA is a personal security setting; there is no
# "enroll someone else's MFA on their behalf" capability.
# --------------------------------------------------------------------------


async def _current_staff_user(ctx: CallContext) -> User:
    if ctx.actor_type != "staff":
        raise MFAError("MFA applies to staff accounts only", 400)
    result = await ctx.db.execute(select(User).where(User.discord_id == ctx.actor_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise MFAError("no matching user account found for the current session", 404)
    return user


class BeginMFAEnrollmentParams(BaseModel):
    pass


class BeginMFAEnrollmentResult(BaseModel):
    secret: str
    provisioning_uri: str


@capability(
    name="identity.mfa.begin_enrollment",
    summary="Generate a new TOTP secret for the current user (not yet active until confirmed).",
    params_model=BeginMFAEnrollmentParams,
    result_model=BeginMFAEnrollmentResult,
    required_permission=None,
    destructive=False,
    audit_category="identity",
)
async def begin_mfa_enrollment(ctx: CallContext, params: BeginMFAEnrollmentParams) -> BeginMFAEnrollmentResult:
    user = await _current_staff_user(ctx)
    secret, uri = await MFAService.begin_enrollment(ctx.db, user)
    return BeginMFAEnrollmentResult(secret=secret, provisioning_uri=uri)


class ConfirmMFAEnrollmentParams(BaseModel):
    code: str


class ConfirmMFAEnrollmentResult(BaseModel):
    enabled: bool


@capability(
    name="identity.mfa.confirm_enrollment",
    summary="Confirm MFA enrollment with a code from the authenticator app, activating it.",
    params_model=ConfirmMFAEnrollmentParams,
    result_model=ConfirmMFAEnrollmentResult,
    required_permission=None,
    destructive=False,
    audit_category="identity",
)
async def confirm_mfa_enrollment(ctx: CallContext, params: ConfirmMFAEnrollmentParams) -> ConfirmMFAEnrollmentResult:
    user = await _current_staff_user(ctx)
    await MFAService.confirm_enrollment(ctx.db, user, params.code)
    return ConfirmMFAEnrollmentResult(enabled=True)


class DisableMFAParams(BaseModel):
    pass


class DisableMFAResult(BaseModel):
    disabled: bool


@capability(
    name="identity.mfa.disable",
    summary="Disable MFA for the current user.",
    params_model=DisableMFAParams,
    result_model=DisableMFAResult,
    required_permission=None,
    destructive=True,
    reversible=True,  # the user can always re-enroll
    audit_category="identity",
)
async def disable_mfa(ctx: CallContext, params: DisableMFAParams) -> DisableMFAResult:
    user = await _current_staff_user(ctx)
    await MFAService.disable(ctx.db, user)
    return DisableMFAResult(disabled=True)
