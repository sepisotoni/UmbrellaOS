"""
api/middleware/waf.py — WAF-style API hardening (Phase 9, item 7).

Scope, stated the same way the other Phase 9 modules do: this is a small,
targeted set of checks appropriate for a single-operator, internet-exposed
admin API — not a general-purpose WAF product (no ModSecurity-style rule
engine, no learning mode, no IP reputation feeds). It exists to reject the
cheap, high-volume, automated-scanner-grade attacks (path traversal probes,
obvious SQLi/XSS payloads in query params, oversized request bodies)
before they reach routing/auth/business logic at all, complementing —
never replacing — the real defenses that already exist deeper in the
stack: SQLAlchemy's parameterized queries are what actually prevent SQL
injection; this middleware's SQLi pattern check is a cheap early-reject
for obviously-malicious traffic, not the thing holding the line.

Every blocked request is recorded as a `waf_block` security event (via
the same threat-detection path other Phase 9 signals use) so a pattern of
WAF rejections from one source feeds the same brute-force-style alerting
already in services/threat_detection_service.py, rather than being a
silent drop.

Fails open on its own errors, same principle as every other Phase 9
middleware here: a bug in pattern-matching must never turn into every
request being rejected.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import unquote

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

import services.threat_detection_service as threat_detection_service

logger = logging.getLogger(__name__)

# Deliberately small and specific rather than a large generic ruleset —
# each pattern here corresponds to a known, cheap, automated-scanner-grade
# probe, not an attempt at exhaustive SQLi/XSS coverage (which parameterized
# queries and output encoding are the actual defense against; see module
# docstring).
_PATH_TRAVERSAL_RE = re.compile(r"\.\./|\.\.\\|%2e%2e%2f|%2e%2e/", re.IGNORECASE)
_SQLI_RE = re.compile(
    r"(\bunion\s+select\b|\bor\s+1\s*=\s*1\b|;\s*drop\s+table\b|\bxp_cmdshell\b|--\s*$)",
    re.IGNORECASE,
)
_XSS_RE = re.compile(r"<script\b|javascript:|onerror\s*=|onload\s*=", re.IGNORECASE)

# Above this, reject before reading the body at all. Generous enough for
# any legitimate admin-API payload (plugin manifests, bulk player-risk
# queries) this codebase actually sends; a request bigger than this is far
# more likely to be a DoS attempt than a real use case.
_MAX_BODY_BYTES = 10 * 1024 * 1024  # 10 MiB

_EXEMPT_PATHS = {"/metrics", "/health"}


def _matches_any(value: str) -> str | None:
    if _PATH_TRAVERSAL_RE.search(value):
        return "path_traversal"
    if _SQLI_RE.search(value):
        return "sqli_pattern"
    if _XSS_RE.search(value):
        return "xss_pattern"
    return None


class WAFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        try:
            client_ip = request.client.host if request.client else None

            content_length = request.headers.get("content-length")
            if content_length is not None and content_length.isdigit():
                if int(content_length) > _MAX_BODY_BYTES:
                    await threat_detection_service.record(
                        event_type="waf_block", source_ip=client_ip, detail={"reason": "oversized_body"}
                    )
                    return JSONResponse(
                        status_code=413,
                        content={"code": "PAYLOAD_TOO_LARGE", "message": "Request body exceeds the maximum permitted size."},
                    )

            raw_query = request.url.query
            if isinstance(raw_query, bytes):
                raw_query = raw_query.decode("utf-8", errors="replace")
            candidates = [str(request.url.path), unquote(raw_query).replace("+", " ")]
            for reason in (_matches_any(c) for c in candidates if c):
                if reason:
                    await threat_detection_service.record(
                        event_type="waf_block", source_ip=client_ip, detail={"reason": reason}
                    )
                    return JSONResponse(
                        status_code=400,
                        content={"code": "BAD_REQUEST", "message": "Request rejected by API hardening rules."},
                    )
        except Exception:
            logger.exception("WAF middleware failed its own checks — failing open for this request")

        return await call_next(request)
