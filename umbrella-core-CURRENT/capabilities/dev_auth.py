"""capabilities/dev_auth.py — Phase 10 completion, Task B: a DEBUG-gated
dev-only capability that mints a valid session without a real Discord
OAuth round-trip.

Why this exists (state plainly, per the gating convention this mirrors):
the dashboard's session (umbrella-dashboard-CURRENT/lib/session.ts) is
established via real Discord OAuth (app/api/auth/start -> Discord's real
authorize URL -> app/api/auth/callback). A sandboxed test run — or any
environment without a reachable Discord app registration — cannot
complete that redirect. This capability creates a `Session` row directly,
returning a token the same shape `discord_callback` already produces
(api/routers/auth.py), so manual/browser testing has a real, valid
session to test against without a real Discord round-trip.

Gating — mirrors api/middleware/session.py's `X-Admin-Key` bypass, the
"explicit, off-by-default, clearly-documented bypass for exactly this
kind of need" this dispatch's handoff doc pointed at as the reference
pattern:
- Hard no-op unless `settings.debug` is explicitly True. `debug` (not a
  separate new flag) is this codebase's existing DEBUG/ENVIRONMENT=
  development-style setting (config/settings.py) — already wired to
  nothing else that would make turning it on for a real deployment an
  everyday accident (it currently only controls SQL echo in
  database/engine.py), but it is a real production setting a careless
  ops config could still leave on, so this capability treats it with the
  same seriousness X-Admin-Key gets, not as a free pass.
- MUST NEVER be reachable in production. If `settings.debug` is False,
  `mint_test_session` raises `ResourceNotFoundException` — a 404, not a
  403 — so a probe against this capability name in a real deployment
  looks identical to a capability that doesn't exist, rather than
  confirming a dev backdoor is present but locked.
- This is a new capability, not a modification of an existing one (the
  handoff doc was explicit about that distinction) — registered here in
  its own module, with its own tests (tests/test_dev_auth.py), including
  a test that it is unreachable when the gating flag is false.

Reaching this capability at all still goes through the normal
`POST /api/v1/capabilities/{name}/invoke` path (registry/adapters/rest.py)
and its normal auth (`require_capability_auth` — session, X-Admin-Key, or
a scoped API key), same as every other capability. In practice this means
the *first* session in a test pass is minted using the existing
X-Admin-Key bootstrap tier (already meant for exactly this "no session
yet" bootstrap case), and every session after that can be minted using a
previously-minted session's own bearer token if it carries
`auth.dev.mint_test_session`'s required permission — but this capability
deliberately has no `required_permission` at all (`None`, same convention
CallContext.has_permission documents: "None means any authenticated actor
may call this, not that no check is performed") — being DEBUG-gated
already IS the check; a fresh permission key here would just have to be
granted to a role and audited, real work with no real payoff for a
capability that's a hard no-op in every environment that check matters
for.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field
from sqlalchemy import select

from config import get_settings
from models import Role, Session, User
from models.permissions import Permission
from registry.context import CallContext
from registry.decorator import capability

from api.middleware.errors import ResourceNotFoundException, ValidationException

# Matches api/routers/auth.py's SESSION_EXPIRY_DAYS exactly — a dev-minted
# session should behave identically to a real one for however long a
# manual test pass runs, not expire on some shorter dev-only clock that
# would make it behave differently from what's actually being tested.
SESSION_EXPIRY_DAYS = 7

# The synthetic discord_id namespace dev-minted users live in. Prefixed so
# they're trivially distinguishable from a real Discord snowflake (all
# digits) in the users table or an audit log — never something a real
# discord_id could collide with.
_DEV_DISCORD_ID_PREFIX = "dev-test-"


class MintTestSessionParams(BaseModel):
    # Which existing role (services/roles_service.py DEFAULT_ROLES, or any
    # custom role Sepiso Toni has since added) the minted user gets. Not
    # optional and no default — a test session with an implicit role would
    # be exactly the kind of silent assumption rule 2.2 warns against.
    role: str
    # One-off permission grants beyond the role's own set, via the same
    # `User.extra_permissions` mechanism resolve_user_permissions already
    # honors — this is what makes "a role with marketplace.install.view
    # but not .manage" mintable even though no DEFAULT_ROLES entry has
    # exactly that combination (moderator/helper/member don't touch
    # marketplace permissions at all; admin/owner have both).
    extra_permissions: list[str] = Field(default_factory=list)
    # Distinguishes repeated test-pass users from each other (e.g.
    # "narrow", "broad") without minting a fresh dev user + session every
    # single call — re-invoking with the same label reuses the same
    # underlying User row (see mint_test_session's docstring) so a test
    # pass doesn't accumulate a new synthetic user on every session mint.
    label: str = "default"


class MintTestSessionResult(BaseModel):
    token: str
    role: str
    extra_permissions: list[str]
    expires_in: int


@capability(
    name="auth.dev.mint_test_session",
    summary=(
        "DEV/TEST ONLY, hard no-op unless settings.debug is true: mint a "
        "valid session for a given role without a real Discord OAuth "
        "round-trip."
    ),
    params_model=MintTestSessionParams,
    result_model=MintTestSessionResult,
    required_permission=None,
    destructive=True,
    reversible=True,
    audited=True,
    audit_category="identity",
)
async def mint_test_session(ctx: CallContext, params: MintTestSessionParams) -> MintTestSessionResult:
    settings = get_settings()
    if not settings.debug:
        # See module docstring — 404, not 403, so this looks like a
        # nonexistent capability in any environment where the gate
        # actually matters, not a locked door confirming it exists.
        raise ResourceNotFoundException("Capability", "auth.dev.mint_test_session")

    role_result = await ctx.db.execute(select(Role).where(Role.name == params.role))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise ValidationException(f"Unknown role: {params.role!r}")

    if params.extra_permissions:
        valid_keys_result = await ctx.db.execute(
            select(Permission.permission_key).where(
                Permission.permission_key.in_(params.extra_permissions)
            )
        )
        valid_keys = {row[0] for row in valid_keys_result.all()}
        unknown = set(params.extra_permissions) - valid_keys
        if unknown:
            raise ValidationException(f"Unknown permission key(s): {sorted(unknown)}")

    discord_id = f"{_DEV_DISCORD_ID_PREFIX}{params.label}"
    user_result = await ctx.db.execute(select(User).where(User.discord_id == discord_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        user = User(
            discord_id=discord_id,
            username=f"dev-test:{params.label}",
            email=None,
            role_id=role.id,
            extra_permissions=list(params.extra_permissions),
        )
        ctx.db.add(user)
        await ctx.db.flush()
    else:
        # Re-invoking with the same label updates the existing dev user's
        # role/extra_permissions in place rather than minting a duplicate
        # — a test pass switching a label between "narrow" and "broad"
        # scenarios across runs shouldn't accumulate stale synthetic
        # users the real roles/permissions table has to keep tolerating.
        user.role_id = role.id
        user.extra_permissions = list(params.extra_permissions)
        await ctx.db.flush()

    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)
    session_token = secrets.token_urlsafe(32)
    session = Session(user_id=user.id, token=session_token, expires_at=expires_at)
    ctx.db.add(session)
    await ctx.db.flush()

    return MintTestSessionResult(
        token=session_token,
        role=role.name,
        extra_permissions=list(params.extra_permissions),
        expires_in=SESSION_EXPIRY_DAYS * 24 * 3600,
    )
