"""
api/middleware/metrics.py — Records per-request Prometheus metrics
(Phase 9, item 1).

Mirrors api/middleware/rate_limit.py's shape: a BaseHTTPMiddleware that
wraps every request. Deliberately fails open on the metrics recording
itself — a bug in metrics code must never turn into a 500 for real
traffic, the same fail-open principle rate_limit.py already documents for
its Redis dependency.

Path is normalized to the matched route template (e.g. `/api/v1/players/{id}`,
not `/api/v1/players/1234`) once FastAPI has resolved routing, via
`request.scope["route"].path`, falling back to the raw path only pre-routing
(e.g. a 404 for a path that matches no route) — otherwise every distinct
player id would create its own metric series and cardinality would grow
without bound, exactly the "known bad pattern" Prometheus's own best
practices call out.
"""
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from services.metrics_service import http_requests_total, http_request_duration_seconds

logger = logging.getLogger(__name__)

# Never labeled with per-user/per-id cardinality, and excluded from timing
# noise caused by scraping metrics about metrics.
_EXEMPT_PATHS = {"/metrics"}


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        try:
            route = request.scope.get("route")
            path_label = route.path if route is not None else request.url.path
            http_requests_total.inc(
                method=request.method,
                path=path_label,
                status=str(response.status_code),
            )
            http_request_duration_seconds.observe(
                duration,
                method=request.method,
                path=path_label,
            )
        except Exception:
            logger.exception("Failed to record request metrics (non-fatal)")

        return response
