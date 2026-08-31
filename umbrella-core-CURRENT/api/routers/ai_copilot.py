"""
api/routers/ai_copilot.py — Copilot chat, provider test, and crash-risk endpoints.

POST /api/v1/ai/copilot              — Route a copilot prompt through the AI orchestrator
POST /api/v1/ai/providers/test       — Test an AI provider (live key test with latency)
GET  /api/v1/ai/crash-risk/{server_id} — Expose crash risk assessment via REST
"""
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from api.dependencies.permissions import require_permission
from api.middleware.api_key_auth import require_capability_auth
from models import User
from models.api_key import ApiKey
from registry.context import CallContext
from sqlalchemy import select as sa_select
from models.hosting import Server
from services.ai.orchestrator import Orchestrator
from services.ai.provider_factory import ProviderFactory
from services.ai.base import ProviderError
from services.operational_intelligence.crash_prevention import (
    assess_crash_risk,
    CrashRiskLevel,
)

router = APIRouter(prefix="/api/v1/ai", tags=["ai-copilot"])

COPILOT_SYSTEM_PROMPT = (
    "You are UmbrellaOS Copilot, an assistant for Minecraft server network administration. "
    "You help staff with player moderation, server health, and operational decisions. "
    "Be concise and actionable."
)


# ---------------------------------------------------------------------------
# Task 4 — POST /api/v1/ai/copilot
# ---------------------------------------------------------------------------

class CopilotRequest(BaseModel):
    message: str
    context: Optional[str] = None
    # [HEAD gap #2 — fleet awareness, 2026-08-31] Optional: which server(s)
    # the question is about. None means "network-wide" — the copilot gets a
    # list of every server it's allowed to see rather than being scoped to
    # whatever single server_id happened to be in the dashboard's local
    # state when the request was made.
    server_ids: Optional[list[str]] = None


class CopilotResponse(BaseModel):
    response: str
    model_used: str
    latency_ms: int


@router.post("/copilot", response_model=CopilotResponse)
async def copilot_chat(
    body: CopilotRequest,
    db: AsyncSession = Depends(get_db),
    # [HEAD gap #1 — caller identity, 2026-08-31] Was require_admin_hmac_or_session,
    # which returns a bare string ("hmac" | "plugin" | "session") with no
    # actual identity, role, or permission set attached — the copilot had no
    # way to know WHO was asking or scope its behavior to what they can do.
    # require_capability_auth returns the real User/ApiKey/admin-key-string,
    # the same identity primitive every capability invocation already uses
    # (see registry/context.py::CallContext.from_web_auth) — this makes the
    # copilot's identity handling consistent with the rest of the AI
    # subsystem instead of being its own special case.
    auth: User | str | ApiKey = Depends(require_capability_auth),
) -> CopilotResponse:
    """Route a copilot prompt through the real AI orchestrator.

    Replaces the dashboard's local simulation. Returns the model's response
    with provider/model metadata and measured latency.
    Fails with 503 if no AI provider is available — never fakes a response.

    Caller identity and permissions are resolved into a CallContext (the
    same identity primitive every capability invocation uses) and passed to
    the model so it knows who it's talking to and what they're allowed to
    do — see [HEAD → AI, 2026-08-31]'s 3-gap finding this addresses.
    """
    ctx = await CallContext.from_web_auth(auth, db, source="ai")

    # [HEAD gap #3 — permission scoping, 2026-08-31] The copilot itself is
    # read/advice-only — it has no direct write path (see the prompt-injection
    # fix's comment below), so it doesn't need a permission gate to be
    # INVOKED. What it needs is for the MODEL to know the caller's actual
    # scope, so it doesn't advise or imply actions the caller isn't
    # authorized to take (e.g. telling a moderator "just ban them" when
    # only players.punish permission-holders can). Any actual capability
    # the model's advice leads a human to invoke afterward is separately,
    # independently gated by that capability's own required_permission via
    # action_guard — this is advisory context for the model's phrasing, not
    # the security boundary itself.
    permission_summary = (
        "full access (admin key / superuser)" if ctx.is_superuser
        else (", ".join(sorted(ctx.permissions)) if ctx.permissions else "no granted permissions")
    )

    # [HEAD gap #2 — fleet awareness, 2026-08-31] Previously only knew
    # whatever server_id string happened to be in the dashboard's local
    # component state and passed as free-text `context` — the copilot had
    # no way to answer "which of my servers..." questions or know a second
    # server existed. Queries the same `servers` table (models/hosting.py)
    # that backs the actual fleet — not a fabricated or cached list.
    server_rows = (await db.execute(sa_select(Server.id, Server.name))).all()
    server_by_id = {row.id: row.name for row in server_rows}
    known_server_ids = list(server_by_id.keys())

    if body.server_ids:
        unknown = [s for s in body.server_ids if s not in server_by_id]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown server_id(s): {unknown}. Known servers: {known_server_ids}",
            )
        scoped_ids = body.server_ids
    else:
        scoped_ids = known_server_ids

    fleet_lines = [f"{sid} ({server_by_id[sid]})" for sid in scoped_ids] or ["(no servers registered)"]

    identity_block = (
        f"<caller>\n"
        f"actor_id: {ctx.actor_id}\n"
        f"actor_type: {ctx.actor_type}\n"
        f"permissions: {permission_summary}\n"
        f"</caller>\n"
        f"<fleet>\n"
        f"servers_in_scope: {', '.join(fleet_lines)}\n"
        f"</fleet>"
    )

    # Bug fix (AUDIT-VERIFICATION-2026-08-29 #8 — prompt injection): body.message
    # and body.context are untrusted user input. Delimiting them clearly reduces
    # the chance the model treats injected text as new instructions. Copilot has
    # no direct write path of its own — any capability it invokes (investigation.run,
    # knowledge.*) still goes through action_guard's hard, code-level restrictions —
    # but this is cheap defense in depth on the most user-facing AI surface.
    prompt = f"{identity_block}\n\n<user_question>\n{body.message}\n</user_question>"
    if body.context:
        prompt = f"<context>\n{body.context}\n</context>\n\n{prompt}"

    t0 = time.monotonic()
    try:
        result = await Orchestrator.run(
            db=db,
            task_type="copilot",
            task_prompt=prompt,
            requested_by=ctx.actor_id,
            require_dual_review=False,  # copilot is low-stakes; skip dual review
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"AI orchestrator unavailable: {exc}",
        ) from exc

    latency_ms = int((time.monotonic() - t0) * 1000)
    model_label = result.primary_provider
    if result.primary_model:
        model_label = f"{result.primary_provider}/{result.primary_model}"

    return CopilotResponse(
        response=result.text,
        model_used=model_label,
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# Task 5 — POST /api/v1/ai/providers/test
# ---------------------------------------------------------------------------

class ProviderTestRequest(BaseModel):
    provider: str  # "gemini" | "anthropic" | "openrouter"
    api_key: Optional[str] = None


class ProviderTestResponse(BaseModel):
    success: bool
    latency_ms: int
    message: str
    model: str


_PROVIDER_DEFAULT_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    # gemini-1.5-flash was retired by Google before 2026-08-31 (confirmed via
    # ai.google.dev/gemini-api/docs/changelog: "All Gemini 1.0 models and
    # Gemini 1.5 are already shutdown, and all requests to these models
    # return a 404 error") — every call using it fails at the provider,
    # surfacing to users as a confusing "no available model" error with no
    # indication the model itself no longer exists.
    "gemini": "gemini-2.5-flash",
    "openrouter": "openai/gpt-3.5-turbo",
}


@router.post("/providers/test", response_model=ProviderTestResponse)
async def test_provider(
    body: ProviderTestRequest,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("operational_intelligence.view")),
) -> ProviderTestResponse:
    """Test an AI provider with a minimal prompt and return latency.

    If api_key is supplied in the request body, it is used for this test
    only (so the dashboard can validate a new key before saving it to
    settings). Otherwise the key configured in the DB settings is used.
    """
    provider_name = body.provider.lower()
    known = {"anthropic", "gemini", "openrouter"}
    if provider_name not in known:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider {provider_name!r}. Valid providers: {sorted(known)}",
        )

    try:
        if body.api_key:
            # Inline provider with the supplied key — don't touch DB settings
            from services.ai.provider_factory import _PROVIDER_REGISTRY
            entry = _PROVIDER_REGISTRY.get(provider_name)
            if entry is None:
                raise HTTPException(status_code=400, detail=f"Provider {provider_name!r} not registered")
            _, _, provider_cls = entry
            provider = provider_cls(api_key=body.api_key)
        else:
            provider = await ProviderFactory.build(db, provider_name)
    except ProviderError as exc:
        return ProviderTestResponse(
            success=False,
            latency_ms=0,
            message=str(exc),
            model=_PROVIDER_DEFAULT_MODELS.get(provider_name, ""),
        )

    model = _PROVIDER_DEFAULT_MODELS.get(provider_name, "")
    t0 = time.monotonic()
    try:
        result = await provider.generate(
            model=model,
            system_prompt="You are a test assistant.",
            user_prompt="Hello",
            max_tokens=16,
            temperature=0.0,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        return ProviderTestResponse(
            success=True,
            latency_ms=latency_ms,
            message=f"Provider responded in {latency_ms}ms",
            model=result.model_name or model,
        )
    except ProviderError as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return ProviderTestResponse(
            success=False,
            latency_ms=latency_ms,
            message=str(exc),
            model=model,
        )


# ---------------------------------------------------------------------------
# Task 6 — GET /api/v1/ai/crash-risk/{server_id}
# ---------------------------------------------------------------------------

class CrashRiskResponse(BaseModel):
    server_id: str
    risk_level: str
    tps_trend: Optional[float]
    mspt_avg: Optional[float]  # not tracked in current schema; always null
    recommendation: str
    assessed_at: str  # ISO8601


_RISK_RECOMMENDATIONS: dict[str, str] = {
    CrashRiskLevel.INSUFFICIENT_DATA.value: "Not enough data to assess risk. Continue monitoring.",
    CrashRiskLevel.LOW.value: "Server is healthy. No action required.",
    CrashRiskLevel.MEDIUM.value: "TPS is declining. Consider investigating chunk loading, entities, or player activity.",
    CrashRiskLevel.CRITICAL.value: "Server is at risk of becoming unresponsive. Immediate action recommended.",
}


@router.get("/crash-risk/{server_id}", response_model=CrashRiskResponse)
async def get_crash_risk(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("operational_intelligence.view")),
) -> CrashRiskResponse:
    """Expose the crash-risk assessment for a server via REST.

    Delegates to services.operational_intelligence.crash_prevention.assess_crash_risk()
    (the same function the operational_intelligence.crash_risk.assess capability calls).
    The dashboard AI Intelligence page can use this instead of the capabilities invoke path.
    """
    result = await assess_crash_risk(db, server_id)

    recommendation = _RISK_RECOMMENDATIONS.get(result.risk_level.value, result.reasoning)

    return CrashRiskResponse(
        server_id=result.server_id,
        risk_level=result.risk_level.value.upper(),
        tps_trend=result.trend_delta,
        mspt_avg=None,  # MSPT is not tracked in ServerMetricSnapshot (see crash_prevention.py docs)
        recommendation=recommendation,
        assessed_at=datetime.now(timezone.utc).isoformat(),
    )
