# UmbrellaOS — broad live functional test (resumed session)

Date: 2026-08-17
Scope: resumed the "broad live functional test against real Postgres with real owner
token" that a prior session was mid-way through when it was cut off. Same live
codespace (sturdy-tribble-r49xx959q7wxhwg5), same running Postgres + Redis + app
(uvicorn on :8765, DEBUG=true), no code changes.

## Bug #7 — rate-limit counters can permanently wedge open with no self-healing path

Summary:
`RateLimiter.check()` in `services/rate_limit_service.py` sets the key's TTL only
on the increment that creates the key (`count == 1`). This is a deliberate,
documented trade-off — but there is no fallback if that one `EXPIRE` call is lost
(dropped connection, Redis restart racing the request, etc.). When that happens,
`INCR` keeps succeeding forever on a key with no expiry, so the identifier is
rate-limited permanently until someone manually flushes Redis.

Real evidence:
- On resuming this session, `/openapi.json` — a docs endpoint — was returning
  `429`, blocking nearly everything.
- Inspected Redis directly: `umbrella:ratelimit:127.0.0.1:60` had `count=564`,
  `ttl=-1` (no expiry), consistent with exactly this failure mode.
- Deleting that single key immediately restored `200` responses across the app
  with no other change.

Impact:
- Any transient Redis hiccup on a request's first hit can permanently lock out
  that identifier (IP or user) in production, with no automatic recovery and no
  visible error to the operator — it just looks like the app silently stopped
  responding to that client.
- Confirms and gives root cause for the same rate-limit symptom noted in bug #2
  of the prior review (`review-2-live-postgres-test-2026-08-16.md`), and is likely
  the actual mechanism behind it.

Suggested direction (not implemented — no code changes made this pass):
Set the TTL unconditionally after every `INCR` (Redis `SET key val EX seconds NX`
pattern, or a Lua script combining `INCR`+`EXPIRE` atomically) instead of only on
`count == 1`, so a lost `EXPIRE` can't leave a permanent counter.

## Confirmed working end-to-end (real requests, real Postgres, real Redis, real owner session)

- `auth.dev.mint_test_session` capability mints a working session token (DEBUG-gated
  as designed; correctly rejected without `X-Admin-Key` — not separately retested
  this pass since prior session already covered it).
- `/api/v1/auth/me` returns full profile with a correct, complete owner permission
  set (52 permissions).
- `/health` reports real DB connectivity (`"database": "connected"`).
- Read paths all real `200`s against live Postgres: `/api/v1/players`, `/api/v1/roles`,
  `/api/v1/roles/permissions`, `/api/v1/settings`, `/api/v1/audit`,
  `/api/v1/security/events`, `/api/v1/dashboard/servers`, `/api/v1/dashboard/plugins`,
  `/api/v1/appeals`, `/api/v1/punishments`, `/api/v1/logs`, `/api/v1/analytics/summary`,
  `/api/v1/alts/flagged`, `/api/v1/verification/pending`, `/api/v1/replay/sessions`,
  `/api/v1/bridge/settings`, `/metrics`.
- Audit log genuinely records real actions with correct actor/action/outcome
  metadata (verified by reading `/api/v1/audit` after minting sessions).
- Foreign-key integrity is real, not decorative: `POST /api/v1/punishments` against
  a nonexistent player correctly returned `404 Player not found` rather than
  silently succeeding.
- Plugin-authenticated routes (`/api/v1/plugin/health`, `/api/v1/anticheat/flag`)
  consistently reject a user bearer token with `401 Invalid or missing plugin key`
  — write-path auth is applied consistently across plugin-facing routes, not just
  ad hoc on some.
- `/api/v1/staff/discord-members` correctly returns `503` with a clear message
  when no Discord bot token/guild ID is configured, rather than crashing or
  returning bad data.

## Not exercised this pass

- Actual plugin-key-authenticated write paths (would need a real plugin API key,
  not the owner session token used throughout this pass).
- Discord OAuth round-trip (`/api/v1/auth/discord/*`) — requires real Discord app
  credentials, out of scope for this environment.

Session notes: resumed live functional test, one real infrastructure-level bug
found and root-caused (permanently-wedging rate limiter), broad read/write/auth
surface otherwise confirmed genuinely functional against real Postgres + Redis.
2026-08-17.
