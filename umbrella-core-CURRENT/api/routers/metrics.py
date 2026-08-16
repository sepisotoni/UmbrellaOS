"""
api/routers/metrics.py — GET /metrics, Prometheus scrape endpoint
(Phase 9, item 1).

Gated behind the same X-Admin-Key / session auth every other admin-facing
endpoint in this codebase uses (api/middleware/session.py), not left open
like /health. Prometheus's own `scrape_configs` supports a static header
via `authorization` / `http_headers` config, so this doesn't require the
Prometheus server to do anything unusual — but it does mean an operator
must configure that header, which is the trade-off for not leaking
internal request-volume/error-rate data (a real information-disclosure
surface for an internet-exposed single-operator platform, per this
project's stated threat model) to an unauthenticated caller.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from api.middleware.session import require_admin_key_or_session
from services.metrics_service import render_exposition

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics(_=Depends(require_admin_key_or_session)) -> PlainTextResponse:
    return PlainTextResponse(
        render_exposition(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
