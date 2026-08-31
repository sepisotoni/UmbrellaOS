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
from api.middleware.auth import require_admin_hmac_or_session
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


class CopilotResponse(BaseModel):
    response: str
    model_used: str
    latency_ms: int


@router.post("/copilot", response_model=CopilotResponse)
async def copilot_chat(
    body: CopilotRequest,
    db: AsyncSession = Depends(get_db),
    # Accept PBKDF2 MAC (bot), raw admin key, or dashboard session token.
    # require_permission() only accepts admin key or session — bot calls
    # would 401. require_admin_hmac_or_session covers all three callers.
    _auth=Depends(require_admin_hmac_or_session),
) -> CopilotResponse:
    """Route a copilot prompt through the real AI orchestrator.

    Replaces the dashboard's local simulation. Returns the model's response
    with provider/model metadata and measured latency.
    Fails with 503 if no AI provider is available — never fakes a response.
    """
    # Bug fix (AUDIT-VERIFICATION-2026-08-29 #8 — prompt injection): body.message
    # and body.context are untrusted user input. Delimiting them clearly reduces
    # the chance the model treats injected text as new instructions. Copilot has
    # no direct write path of its own — any capability it invokes (investigation.run,
    # knowledge.*) still goes through action_guard's hard, code-level restrictions —
    # but this is cheap defense in depth on the most user-facing AI surface.
    prompt = f"<user_question>\n{body.message}\n</user_question>"
    if body.context:
        prompt = f"<context>\n{body.context}\n</context>\n\n{prompt}"

    t0 = time.monotonic()
    try:
        result = await Orchestrator.run(
            db=db,
            task_type="copilot",
            task_prompt=prompt,
            requested_by="dashboard_copilot",
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
