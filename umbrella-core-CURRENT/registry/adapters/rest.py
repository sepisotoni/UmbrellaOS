"""
registry/adapters/rest.py — Generic REST adapter over the Capability Registry.

Every registered capability is reachable at
`POST /api/v1/capabilities/{name}/invoke` with zero per-capability route
code — this is the concrete mechanism behind "a new capability is
automatically available over REST," not an aspiration.

Trade-off, stated plainly rather than glossed over: this is an RPC-style
invoke endpoint (`POST .../{name}/invoke`), not a resource-styled REST path
(`POST /servers/{id}/restart`). Resource-styled path aliases can be layered
on top later — a thin route that calls `registry.call("hosting.server.restart", ...)`
under a prettier URL — without changing the underlying contract. That
ergonomic layer is intentionally deferred rather than built speculatively
before there's a second adapter (Phase 5's AI Tool Registry) to validate the
schema-driven approach against.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.api_key_auth import require_capability_auth
from database import get_db
from models import User
from models.api_key import ApiKey
from registry.context import CallContext, Source
from registry.registry import registry

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])

# A scoped API key carrying this permission may act on behalf of a specific
# Discord user (via the X-Discord-User-Id header below), rather than only
# ever using its own blanket permission set for every caller. Deliberately
# NOT added to services/roles_service.py's DEFAULT_PERMISSIONS: that list
# seeds every human Role too (ALL_PERMISSION_KEYS makes "owner" inherit
# everything in it automatically), and this permission has no meaning for
# a session-authenticated staff member - it only matters for ApiKey.permissions,
# checked directly below, so it's declared here instead of polluting the
# staff role-permission list with an API-key-only concept.
DISCORD_DELEGATE_PERMISSION = "identity.discord_delegate"


class CapabilitySummary(BaseModel):
    name: str
    summary: str
    required_permission: str | None
    destructive: bool
    reversible: bool
    audited: bool
    params_schema: dict[str, Any]


@router.get("")
async def list_capabilities() -> list[CapabilitySummary]:
    """
    List every registered capability and its parameter schema. This is the
    same introspection the CLI adapter uses to build its command tree and
    that (Phase 5) the AI Tool Registry will use to build tool definitions —
    one source of truth for "what can UmbrellaOS do," not a hand-maintained
    list per adapter.
    """
    return [
        CapabilitySummary(
            name=spec.name,
            summary=spec.summary,
            required_permission=spec.required_permission,
            destructive=spec.destructive,
            reversible=spec.reversible,
            audited=spec.audited,
            params_schema=spec.params_model.model_json_schema(),
        )
        for spec in registry.list()
    ]


@router.post("/{name}/invoke")
async def invoke_capability(
    name: str,
    payload: dict[str, Any] | None = Body(default=None),
    auth: User | str | ApiKey = Depends(require_capability_auth),
    db: AsyncSession = Depends(get_db),
    x_discord_user_id: str | None = Header(default=None),
) -> Any:
    """
    Invoke any registered capability by name. This single route is the
    entire REST surface for every current and future capability — there is
    no separate route per domain to write or maintain.

    Accepts session auth, the admin-key bootstrap tier, or (Phase 3) a
    scoped API key via `X-Api-Key` — whichever the caller presents,
    `CallContext.from_web_auth` resolves it to the same permission-checked
    shape before `registry.call()` ever sees it.

    Phase 6 adds one more path: an API key that itself carries
    `identity.discord_delegate` may also send `X-Discord-User-Id`, the raw
    Discord snowflake of whoever is actually invoking the command (a fact
    only umbrella-discord's live gateway can observe — this endpoint never
    trusts a self-reported permission set, only a self-reported *identity*,
    which is then independently resolved server-side via
    `CallContext.from_discord_user` — see that method's own docstring for
    the full reasoning). A key without that permission sending the header
    anyway is simply ignored and falls back to the key's own blanket scope
    — exactly today's pre-Phase-6 behavior, so this is purely additive.

    The header's mere presence (regardless of whether the key qualifies
    for delegation) is still evidence the call originated from Discord, so
    `source` reflects that either way — more accurate than every prior
    API-key call being labeled generic "rest" in the audit log.

    Authorization and audit logging happen inside `registry.call()`, not
    here — this route's only job is translating an authenticated FastAPI
    request into a CallContext and a raw params dict.
    """
    source: Source = "discord" if x_discord_user_id else "rest"

    if (
        x_discord_user_id is not None
        and isinstance(auth, ApiKey)
        and DISCORD_DELEGATE_PERMISSION in auth.permissions
    ):
        ctx = await CallContext.from_discord_user(
            x_discord_user_id, db, base_permissions=set(auth.permissions), source=source
        )
    else:
        ctx = await CallContext.from_web_auth(auth, db, source=source)

    result = await registry.call(name, ctx, payload or {})
    return result.model_dump(mode="json") if isinstance(result, BaseModel) else result
