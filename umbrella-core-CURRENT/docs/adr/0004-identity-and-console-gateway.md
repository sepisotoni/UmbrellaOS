# ADR-0004: Identity domain (API keys, MFA, rate limiting) and the dashboard console gateway

**Status:** Accepted, implemented (Phase 3).

## Context

Phase 3 needed machine-to-machine authentication beyond the existing admin-key/session tiers, MFA for
elevated account security, rate limiting at the API gateway, and — the piece ADR-0003 explicitly
deferred — a real WebSocket gateway now that the dashboard is a real consumer for it.

## Decisions

**API keys are deliberately weaker than the admin-key tier, not a second copy of it.** An API key can
only ever carry an explicit, finite list of permission keys (`ApiKeyService.create_api_key` rejects a
wildcard outright). This is a real constraint, not a formality: if something needs full access, it
should be a session-authenticated staff account, not an API key configured to look like one.

**The combined auth dependency calls the existing session dependency as a plain function, not via
`Depends()`.** `require_admin_key_or_session` raises on its own when neither an admin key nor a
session token is present. Declaring it as a FastAPI dependency inside `require_capability_auth` would
make FastAPI resolve it eagerly for *every* request — including ones authenticating validly via
`X-Api-Key` — incorrectly rejecting them before the API-key branch ever ran. Reasoned through before
writing the code, then confirmed with a test that specifically constructs that exact request shape
(valid API key, no session/admin-key headers at all).

**The rate limiter fails open, not closed.** Caught the hard way: wiring a real Redis-backed rate
limiter into `main.py` immediately broke the entire existing test suite, because Redis is unreachable
in this environment and the first version let `redis.exceptions.ConnectionError` propagate and take
down every request. Fixed by catching `RedisError` and allowing the request through, logged as a
warning. This is also the correct production stance independent of the test-suite discovery: a
defense-in-depth feature's backing store having an outage should degrade that one feature, not the
entire API.

**The console WebSocket gateway lives in core, proxying to the correct node's daemon — the dashboard
never receives a node token.** A browser client authenticates to core with its own session (token as a
query parameter, the standard unavoidable pattern for browser-originated WebSocket auth); core looks up
the server's node, issues a short-lived node token itself, and pipes bytes both directions. This keeps
node tokens exactly where ADR-0002 and ADR-0003 already said they should live — server-to-server,
never handed to a browser.

**`pipe_console`'s task cleanup uses `try/finally`, not a bare sequential cleanup after `asyncio.wait`.**
Found via a real test producing a "Task was destroyed but it is pending!" warning: if the coroutine
running `pipe_console` is itself cancelled from outside (e.g. the browser tab closes and FastAPI
cancels the handler), a cleanup path that only runs *after* `asyncio.wait` returns normally never
executes — the `CancelledError` propagates through that line and skips it entirely. Fixed by moving the
cancel-and-await-both-tasks logic into a `finally` block, so it runs regardless of how the wait exits.

## Consequences

- `whoami` (Phase 0's original capability) turned out to be exactly the right end-to-end proof for this
  phase too — the REST integration tests confirm an API-key-authenticated call reports
  `actor_type: "plugin"`, `is_superuser: false`, with the key's actual scoped permissions, through the
  same capability every other adapter already used.
- The dashboard's hosting pages call the Capability Registry through one generic `invokeCapability()`
  helper (`lib/api.ts`) — adding a new hosting/identity capability to the dashboard going forward is
  one typed wrapper function, not new fetch plumbing, mirroring the backend's own "declare once" pattern
  on the frontend side.

## Alternatives considered

- **A separate, harder rate limit specifically on `/auth` routes**: not built now — the global
  per-IP limit already covers unauthenticated abuse generally; a stricter, route-specific limit is a
  reasonable future refinement once there's a real abuse pattern to tune it against, not a
  speculative addition now.
- **Sliding-window rate limiting** instead of fixed-window: rejected for this phase — the boundary-case
  imprecision fixed-window accepts (see `services/rate_limit_service.py`'s own docstring) is a
  reasonable trade-off for "stop obvious abuse," which is what Phase 3 actually needs.
