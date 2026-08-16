"""
api/middleware/rate_limit.py — Per-client-IP rate limiting at the API
gateway layer, using services/rate_limit_service.py.

Keyed by client IP, not by authenticated identity — this is the first line
of defense against unauthenticated abuse (credential-stuffing against
/auth routes, brute-force probing) before a request is even authenticated,
which is exactly the case an identity-keyed limiter can't cover. Per-API-key
or per-user limits are a reasonable future refinement layered on top of
this, not a replacement for it.

Fails open, not closed: if Redis is unreachable, requests are allowed
through rather than the entire API going down because a secondary,
defense-in-depth feature's backing store had an outage. This was found and
fixed during Phase 3's own testing — the initial version let a
redis.exceptions.ConnectionError propagate and take down every request,
discovered because it broke the existing test suite the moment it was
wired into main.py, not by inspection. Every failure of this kind is
logged, so a real, ongoing Redis outage is still visible in logs even
though it no longer blocks traffic.

Phase 7 addition (docs/design/public-rest-api-and-webhooks.md, Decision 1):
when a request presents `X-Api-Key`, a second, additive check runs keyed by
a hash of that key's plaintext value (never the plaintext itself, never
logged — same sha256 `ApiKeyService` already uses to look the key up), on
top of the existing per-IP check, not instead of it. Both must pass. This
was flagged as future work in this module's own docstring before Phase 7 —
real external callers behind a shared IP need a bucket that isn't shared
with every other caller on that IP. Deliberately does NOT look the key up
against the database here: this middleware has no DB session, and rate
limiting doesn't need the key to be valid — an invalid/garbage key still
gets its own stable bucket, which incidentally also rate-limits credential
probing against X-Api-Key, a reasonable side benefit rather than a goal.
"""
import hashlib
import logging

from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from services.rate_limit_service import RateLimiter
import services.threat_detection_service as threat_detection_service

logger = logging.getLogger(__name__)

DEFAULT_EXEMPT_PATHS = {"/health"}


def _api_key_identifier(plaintext: str) -> str:
    """Same hash function ApiKeyService uses for lookup — reused here only
    to derive a stable, non-reversible rate-limit bucket name, never to
    validate the key."""
    return "apikey:" + hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        requests_per_window: int = 120,
        window_seconds: int = 60,
        exempt_paths: set[str] | None = None,
        api_key_requests_per_window: int = 300,
        api_key_window_seconds: int = 60,
    ):
        super().__init__(app)
        self._limiter = rate_limiter
        self._limit = requests_per_window
        self._window = window_seconds
        self._exempt_paths = exempt_paths if exempt_paths is not None else set(DEFAULT_EXEMPT_PATHS)
        self._api_key_limit = api_key_requests_per_window
        self._api_key_window = api_key_window_seconds

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._exempt_paths:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        try:
            result = await self._limiter.check(client_ip, self._limit, self._window)
        except RedisError:
            logger.warning(
                "rate limiter backend unreachable — failing open (request allowed) for %s",
                client_ip,
            )
            return await call_next(request)

        if not result.allowed:
            await threat_detection_service.record(event_type="rate_limit_violation", source_ip=client_ip)
            return JSONResponse(
                status_code=429,
                content={
                    "code": "RATE_LIMITED",
                    "message": f"Rate limit exceeded: {self._limit} requests per {self._window}s",
                },
                headers={"Retry-After": str(result.reset_seconds)},
            )

        api_key = request.headers.get("x-api-key")
        if api_key:
            try:
                key_result = await self._limiter.check(
                    _api_key_identifier(api_key), self._api_key_limit, self._api_key_window
                )
            except RedisError:
                logger.warning(
                    "rate limiter backend unreachable — failing open (request allowed) for API key"
                )
                key_result = None

            if key_result is not None and not key_result.allowed:
                await threat_detection_service.record(event_type="rate_limit_violation", source_ip=client_ip)
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": "RATE_LIMITED",
                        "message": (
                            f"API key rate limit exceeded: {self._api_key_limit} requests "
                            f"per {self._api_key_window}s"
                        ),
                    },
                    headers={"Retry-After": str(key_result.reset_seconds)},
                )
            if key_result is not None:
                result = key_result

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        return response
