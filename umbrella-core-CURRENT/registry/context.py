"""
registry/context.py — CallContext: identity of whoever is invoking a capability.

Every adapter (REST, CLI, Discord, AI) builds exactly one CallContext before
calling `CapabilityRegistry.call()`. It is the single object that answers
"who is calling, what can they do, and where did this call originate" —
capability handlers receive one instead of each re-deriving identity from a
FastAPI `Request`, a Discord interaction, or a CLI invocation differently.

Design invariant: an AI-initiated call (Phase 5) builds its CallContext from
the *user the AI is acting on behalf of*, never from a separate elevated
identity. This is what makes "the AI cannot exceed the permissions of the
human it's acting for" true by construction — there is no code path that
grants a CallContext more access than the underlying actor actually has.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from models import User
from models.api_key import ApiKey
from services.permission_resolution import resolve_user_permissions

# Where the call originated. Extended in later phases as more adapters land
# (Phase 5 adds "ai", Phase 6 formalizes "discord" beyond this placeholder).
Source = Literal["rest", "cli", "discord", "ai", "system"]


@dataclass
class CallContext:
    # Stable identifier for the actor. For a staff user this is their
    # Discord ID (matches models.user.User.discord_id); for the admin-key
    # bootstrap tier it's the literal string "admin-key".
    actor_id: str

    # Matches the AuditLog.actor_type convention exactly (staff | plugin |
    # bot | system | ai) so capability audit rows are queryable the same way
    # as every audit row written before Phase 0 existed.
    actor_type: str

    # Which adapter is making this call.
    source: Source

    # The actor's resolved permission keys. Empty for a superuser context —
    # is_superuser is checked first, so an empty set here never means
    # "denied" for the admin-key tier.
    permissions: set[str]

    # True only for the X-Admin-Key / plugin-bootstrap tier. Mirrors the
    # existing "admin key bypasses all permission checks" behavior in
    # api/dependencies/permissions.py — the registry does not introduce a
    # second, different notion of "superuser".
    is_superuser: bool

    # Request-scoped DB session. The registry's audit write and the
    # capability handler's own queries share this session/transaction —
    # a capability's side effects and its audit row commit together.
    db: AsyncSession

    # Correlation ID for this specific call, useful for tracing a single
    # invocation across logs once Phase 9's OpenTelemetry integration lands.
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def has_permission(self, permission: str | None) -> bool:
        """
        A permission requirement of None means "any authenticated actor may
        call this" — not "no check is performed." Authentication itself
        already happened before a CallContext could be constructed at all.
        """
        if self.is_superuser:
            return True
        if permission is None:
            return True
        return permission in self.permissions

    @classmethod
    async def from_web_auth(
        cls,
        auth: User | str | ApiKey,
        db: AsyncSession,
        source: Source = "rest",
    ) -> "CallContext":
        """
        Build a CallContext from the existing `require_admin_key_or_session`
        dependency's return value — a `User` for a session-authenticated
        staff member, or the raw admin-key string for the bootstrap tier —
        or, as of Phase 3, an `ApiKey` for a machine-to-machine caller
        authenticated via `require_capability_auth`
        (api/middleware/api_key_auth.py).

        Deliberately reuses these exact authentication outcomes rather than
        introducing a second authentication concept: this method decides
        how an already-authenticated caller is subsequently routed to
        business logic, not who is allowed to authenticate.
        """
        if isinstance(auth, str):
            return cls(
                actor_id="admin-key",
                actor_type="system",
                source=source,
                permissions=set(),
                is_superuser=True,
                db=db,
            )

        if isinstance(auth, ApiKey):
            return cls(
                actor_id=f"apikey:{auth.id}",
                actor_type="plugin",
                source=source,
                # An API key's permissions are an explicit, finite list —
                # never "*" (see services/api_key_service.py's own
                # validation at creation time), so is_superuser is always
                # False here; there is no code path that lets an API key
                # become a superuser context.
                permissions=set(auth.permissions),
                is_superuser=False,
                db=db,
            )

        permissions = await resolve_user_permissions(auth, db)
        return cls(
            actor_id=auth.discord_id,
            actor_type="staff",
            source=source,
            permissions=permissions,
            is_superuser=False,
            db=db,
        )

    @classmethod
    async def from_discord_user(
        cls,
        discord_id: str,
        db: AsyncSession,
        *,
        base_permissions: set[str],
        source: Source = "discord",
    ) -> "CallContext":
        """
        Closes Phase 6's slash-command -> REST-permission mapping gap.
        `discord_id` is a raw fact the bot's own live gateway observed
        (interaction.user.id) - not a self-reported permission set, which
        would be an insecure shortcut (see registry/adapters/rest.py's own
        reasoning for why only a specifically-scoped API key can even
        reach this path at all).

        This resolves identity the SAME way session auth already does for
        a Discord-linked staff member, rather than inventing a second,
        parallel notion: capabilities/identity.py's `_current_staff_user`
        and `create_api_key` already do
        `select(User).where(User.discord_id == ctx.actor_id)` for
        actor_type == "staff" - meaning "a staff member's actor_id is
        their discord_id" is already this codebase's established meaning,
        just previously only reachable via a dashboard session. This
        reuses that exact convention and resolve_user_permissions (the
        same function from_web_auth's session branch calls) rather than a
        second permission-computation path that could drift out of sync.

        `base_permissions` (the calling API key's own scope) is always
        included, unioned with whatever the linked User's role adds -
        additive, never subtractive, so this can never take away what
        already worked via the bot's blanket key today. A Discord user
        with no matching User row (a regular player, not staff) - or one
        that exists but is deactivated (user.is_active is False, a check
        this path makes explicitly, since unlike the session branch there
        is no upstream login/session-validity gate before this runs) -
        gets exactly `base_permissions` and nothing more, actor_type
        "discord_user" rather than "staff", so anything that specifically
        branches on actor_type == "staff" (MFA enrollment, api-key-creation
        audit attribution) correctly treats them as non-staff.
        """
        from sqlalchemy import select

        result = await db.execute(select(User).where(User.discord_id == discord_id))
        user = result.scalar_one_or_none()

        if user is not None and user.is_active:
            permissions = base_permissions | await resolve_user_permissions(user, db)
            return cls(
                actor_id=discord_id,
                actor_type="staff",
                source=source,
                permissions=permissions,
                is_superuser=False,
                db=db,
            )

        return cls(
            actor_id=discord_id,
            actor_type="discord_user",
            source=source,
            permissions=set(base_permissions),
            is_superuser=False,
            db=db,
        )

    @classmethod
    def from_system(cls, db: AsyncSession, source: Source = "system") -> "CallContext":
        """
        A context for calls UmbrellaOS's own automation initiates — the
        scheduler firing a due job, a future self-healing reconciliation
        loop — rather than any external caller. Superuser, since a
        Schedule's own creation already required whatever permission the
        capability it invokes needs (see capabilities/automation.py); this
        does not grant anything beyond what was already authorized at
        schedule-creation time, it just avoids re-deriving "who created
        this schedule and do they still have permission" on every single
        tick, which the scheduler has no natural way to check anyway once
        a schedule outlives its creator's session.
        """
        return cls(
            actor_id="scheduler",
            actor_type="system",
            source=source,
            permissions=set(),
            is_superuser=True,
            db=db,
        )
