"""
api/middleware/rate_limit.py — Per-client-IP rate limiting at the API
gateway layer, using services/rate_limit_service.py.

Keyed by client IP, not by authenticated identity — this is the first line
of defense against unauthenticated abuse (credential-stuffing against
/auth routes, brute-force probing) before a request is even authenticated,
which is exactly the case an identity-keyed limiter can't cover. Per-API-key
or per-user limits are a reasonable future refinement layered on top of
this, not a replacement for it.

Proxy-aware IP resolution: `X-Forwarded-For` is read when present, using
the rightmost (proxy-injected, non-spoofable) entry as the rate-limit key.
Without this, all traffic routed through Render's LB would appear to come
from the proxy's IP and share a single rate-limit bucket, making the
per-IP limit useless in production.

Fails open, not closed: if Redis is unreachable, requests are allowed
through rather than the entire API going down because a secondary,
defense-in-depth feature's backing store had an outage. This was found and
fixed during Phase 3's own testing — the initial version let a
redis.exceptions.ConnectionError propagate and take down every request,
discovered because it broke the existing test suite the moment it was
wired into main.py, not by inspection. Every failure of this kind is
logged, so a real, ongoing Redis outage is still visible in logs even
though it no longer blocks traffic.

Widened 2026-09-05: catching only redis.exceptions.RedisError was too
narrow to fully deliver on the "fails open" promise above. Confirmed via
a real CI failure (RuntimeError('Event loop is closed'), surfaced when a
Redis connection object created under one pytest-asyncio test's event
loop was reused after that loop closed — a test-infrastructure artifact,
not something a real long-running server process can hit, since it has
exactly one event loop for its entire lifetime) — but the underlying
principle applies beyond that one test symptom: a broken pipe, a DNS
failure resolving the Redis host, or any other transport-level failure
during the redis-py call can surface as a plain RuntimeError or OSError
rather than a RedisError subclass, depending on exactly where in the
stack it occurs. All of these represent "the rate limiter's backing store
is not currently usable," which is exactly the condition this module's
own stated design says should fail open — narrowly matching only one
exception family among several that indicate that same condition
undermines the module's own documented guarantee. Still deliberately not
catching bare Exception: an AttributeError/NameError from a genuine
coding mistake inside RateLimiter.check() itself should keep failing
loudly in tests, not be silently swallowed as if it were a backend outage.

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

# Exception types that mean "the rate limiter's backend is not currently
# usable" — see the widened-catch note in the module docstring above for
# why this is broader than just RedisError.
_LIMITER_BACKEND_ERRORS = (RedisError, RuntimeError, OSError)


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

        # Resolve the real client IP behind Render's reverse proxy.
        # Render (and most CDN/LB layers) appends the real client IP as the
        # *last* value in X-Forwarded-For, making it the only trustworthy
        # one — earlier entries can be spoofed by the client. We fall back
        # to request.client.host (the TCP peer) if the header is absent.
        forwarded_for = request.headers.get("x-forwarded-for", "").strip()
        if forwarded_for:
            # Last entry is injected by the trusted proxy, not the client
            client_ip = forwarded_for.split(",")[-1].strip() or (request.client.host if request.client else "unknown")
        else:
            client_ip = request.client.host if request.client else "unknown"

        try:
            result = await self._limiter.check(client_ip, self._limit, self._window)
        except _LIMITER_BACKEND_ERRORS:
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
            except _LIMITER_BACKEND_ERRORS:
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
