# Phase 3 — Identity, Access & Dashboard Hosting UI: changes in this PR

Two components change: `umbrella-core` (API keys, MFA, rate limiting, the console WS gateway) and
`umbrella-dashboard` (three new hosting pages, live console, and the API/query layer backing them).
Discord OAuth, sessions, and RBAC already existed in this codebase prior to this phase and were not
rebuilt — only what was actually missing was added (see docs/adr/0004).

## umbrella-core: new files

```
models/api_key.py                       ApiKey model
alembic/versions/013_identity_phase3.py Migration: api_keys table + User.mfa_secret/mfa_enabled

services/api_key_service.py             Scoped, revocable API keys (never wildcard/superuser)
services/mfa_service.py                 TOTP enrollment (two-step commit) and verification
services/rate_limit_service.py          Redis fixed-window rate limiter

api/middleware/api_key_auth.py          Combined API-key / admin-key / session auth dependency
api/middleware/rate_limit.py            Rate limiting HTTP middleware (fails open on Redis errors)
api/routers/hosting_console_ws.py       WebSocket console proxy: dashboard -> core -> node daemon

capabilities/identity.py                6 capabilities: apikey.{create,list,revoke},
                                         mfa.{begin_enrollment,confirm_enrollment,disable}

docs/adr/0004-identity-and-console-gateway.md

tests/test_api_key_service.py             8 tests
tests/test_mfa_service.py                 7 tests
tests/test_rate_limit_service.py          5 tests
tests/test_rate_limit_middleware.py       5 tests
tests/test_api_key_auth.py                5 tests
tests/test_hosting_console_ws.py          6 tests
tests/registry/test_capabilities_identity.py  8 tests
```

## umbrella-core: modified files

- **`models/user.py`** — added `mfa_secret`, `mfa_enabled`.
- **`models/__init__.py`** — registers `ApiKey`.
- **`registry/context.py`** — `CallContext.from_web_auth` accepts `ApiKey` as a third auth type
  (`actor_type="plugin"`, permissions from the key, never superuser).
- **`registry/adapters/rest.py`** — the capability invoke endpoint now accepts `X-Api-Key` alongside
  admin-key/session.
- **`services/roles_service.py`** — added the `identity.apikey.manage` permission key.
- **`config/settings.py`** — added `rate_limit_requests_per_window`, `rate_limit_window_seconds`.
- **`main.py`** — wires the rate limit middleware and mounts the console WS router.
- **`requirements.txt`** — added `pyotp==2.9.0`, `websockets==16.0`, `fakeredis==2.26.2` (test-only).

## umbrella-dashboard: new files

```
app/hosting/page.tsx                    Server fleet: cards, start/stop/restart/kill/delete, create dialog
app/hosting/nodes/page.tsx              Node registration (shows signing secret once) + port allocation
app/hosting/servers/[id]/page.tsx       Server detail: live stats polling + console + controls
components/hosting-console.tsx          WebSocket console viewer/input against the new proxy endpoint
lib/hosting-queries.ts                  React Query hooks for the hosting + identity domains
```

## umbrella-dashboard: modified files

- **`lib/types.ts`** — added the hosting-domain types (`HostingNode`, `ServerTemplate`,
  `PortAllocation`, `HostedServer`, `HostedServerStats`, `ApiKeySummary`), kept distinct from the
  legacy `MinecraftServer`/`ServerSummary` types per ADR-0003.
- **`lib/api.ts`** — added `invokeCapability()`, the single generic Capability Registry call helper,
  plus typed wrappers for every hosting/identity capability.
- **`lib/nav.ts`** — added "Hosting" and "Nodes" nav entries (admin/owner only).

## Verification performed

- **44 new Python tests, all passing.** Full suite re-run: **313/314** — same single pre-existing,
  unrelated failure flagged in Phase 0, still out of scope here.
- **Zero new TypeScript errors.** The dashboard's pre-existing baseline already has 28 unrelated
  `tsc --noEmit` errors (a dependency-version mismatch in the `@base-ui` components library, present
  before this phase touched anything) — saved as a baseline and diffed after every new file; the diff
  is empty (one line differs only in TypeScript's own nondeterministic display ordering of an unrelated
  pre-existing error's type union).
- **A real Next.js production build was run**, not just `tsc`. It fails in this sandbox specifically
  because `next/font/google` needs `fonts.googleapis.com`, which isn't in this environment's network
  allowlist — confirmed pre-existing and unrelated to this phase's code (the font import is in
  `app/layout.tsx`, untouched here). To prove the rest of the build path (routing, prerendering, every
  new page) actually works, the font import was temporarily bypassed, the build was run to completion —
  all three new hosting routes compiled and prerendered successfully alongside every existing page —
  and `layout.tsx` was immediately restored byte-for-byte to its original content (diffed to confirm)
  before this PR was finalized. That bypass is not part of this deliverable.

## Two real bugs found and fixed during this phase, not glossed over

1. **The rate limiter took down the entire test suite the moment it was wired into `main.py`** — an
   unreachable Redis in this environment caused every HTTP request to raise. Fixed by making the
   middleware fail open on `RedisError`, with a regression test pointing a real (but deliberately
   unreachable) Redis client at the middleware and asserting the request still succeeds.
2. **`require_capability_auth`'s first draft would have rejected valid API-key requests** — declaring
   `require_admin_key_or_session` via `Depends()` evaluates it eagerly regardless of which auth method
   the request actually used. Caught by reasoning through FastAPI's dependency resolution order before
   the code was ever run, fixed by calling it as a plain function only in the branch that needs it, and
   pinned with a test that constructs the exact request shape (valid API key, no other auth headers)
   the bug would have rejected.

## Known follow-ups (explicitly not built now)

- Generic OIDC beyond Discord — Discord OAuth already exists and is the only IdP in active use; adding
  a second one speculatively isn't justified yet.
- Console-send permission is currently the same `hosting.server.view` required to just watch — a
  dedicated write-scoped permission is a reasonable future tightening, flagged in
  `api/routers/hosting_console_ws.py` rather than silently assumed unnecessary.
- RCON-based management for externally-hosted servers (e.g. a server on a third-party Minecraft host
  with no Docker/root access) and per-plugin resource attribution (extending the existing in-JVM
  `minecraft-plugin`, since RCON cannot expose that data from outside the JVM) — real, concrete next
  work, scoped in conversation but not built in this PR.
