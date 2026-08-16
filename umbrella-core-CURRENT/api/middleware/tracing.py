"""
api/middleware/tracing.py — Establishes a trace/span context for every
request (Phase 9, item 2). See services/tracing_service.py for the real
OpenTelemetry SDK integration and the wire-format-compatibility
verification writeup.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from services.tracing_service import inject_traceparent, request_span


class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        with request_span(request.headers):
            response = await call_next(request)
            inject_traceparent(response.headers)
            return response
