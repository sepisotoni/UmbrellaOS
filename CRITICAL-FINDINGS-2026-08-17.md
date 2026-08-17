# UmbrellaOS — Critical findings, independently confirmed, 2026-08-17

Two things found by `subchat-live-functional-test` (working in the live
`sturdy-tribble-r49xx959q7wxhwg5` codespace against real Postgres+Redis)
and then **independently reproduced by the head chat in a completely
separate sandbox**, not just relayed. Both are more consequential than
any individual phase's status — read this before trusting any prior
"X/Y tests passed" claim in this project's history, including this
session's own Phase 7 and Phase 8 verifications.

## 1. This project's entire test suite has never actually been hermetic

`api/middleware/rate_limit.py`'s `RateLimitMiddleware` is registered
unconditionally in `main.py`, and `tests/conftest.py` imports and tests
against the real `main.app` (not a stripped-down test app) — so the real
rate limiter has always been active during every `pytest` run, in every
environment, this entire project's history. It just never mattered,
because the middleware **fails open when Redis is unreachable**
(`except RedisError: return await call_next(request)`), and every
sandbox this project has ever been verified in — including every
dispatch this session, including Phase 7 and Phase 8's own
verification — happened to have no Redis running by default.

**Independently confirmed by the head chat, reproducibly, in both
directions, same sandbox, same codebase, only Redis's presence changed:**
- Redis unreachable (this project's normal verification conditions,
  every session, every phase): `860 passed` (backend's current count as
  of Phase 8).
- Redis genuinely reachable (`redis-server --daemonize yes`, default
  `redis_url` from `config/settings.py` pointing straight at it, no
  config changes needed): **`272 failed, 583 passed, 5 errors`** — close
  to `subchat-live-functional-test`'s own `347 failed, 489 passed, 8
  errors` from a longer-lived, differently-sized test run.

**What this means concretely:** every "clean" test result this project
has ever produced was clean *conditional on Redis being absent from the
verification environment*. This isn't a Phase 7/8-specific regression —
it's a structural gap in `tests/conftest.py` that predates this
session's dispatches, likely predates the git repository itself. The
rate limiter's actual behavior under load has never once been exercised
by this test suite passing.

## 2. The migration chain cannot bootstrap a fresh production database

Confirmed independently, exhaustively, by grepping every file in
`alembic/versions/` for `op.create_table` against `users`: it appears
**nowhere**. `013_identity_phase3.py` does
`op.add_column('users', 'mfa_secret', ...)` — assuming the table already
exists — and creates `api_keys` with an FK to `users.id`, but the table
itself is never created by any migration in the 001→028 chain.
`sessions`, `discord_oauth_pending`, `plugin_commands`, and
`plugin_heartbeats` (all real, live `models/*.py` classes) have the same
problem — zero `create_table` calls anywhere for any of them.

**Why this has never surfaced:** every test run
(`tests/conftest.py:63`) and every live-app boot
(`main.py`'s startup `create_tables()` call) uses
`Base.metadata.create_all()` directly — which builds tables from the
live ORM models, completely bypassing whatever the migration chain
actually contains. `alembic upgrade head` against a genuinely empty
Postgres database has, as far as this project's own history shows,
**never once been run and passed** — Phase 7's own dispatch hit an
adjacent but different symptom (a SQLite `ALTER TABLE` limitation on
migration `005`) and worked around it the same way, without reaching
this deeper gap.

## Also confirmed this session (relayed from `subchat-live-functional-test`,
not independently re-run by the head chat, but well-evidenced with real
reproduction steps against live Postgres — see `cross-chat-findings/`
for the full write-ups):

- **Bug #7** — `RateLimiter.check()` only sets a key's TTL on the
  request that creates it (`count == 1`); a lost `EXPIRE` call leaves a
  permanently-wedged counter with no self-healing path. Reproduced live
  (`ttl=-1`, `count=564` on a stuck key, blocking nearly the whole app
  until manually deleted).
- **Bug #8** — `verification.confirm` can never succeed for a brand-new
  player, on both the legacy REST route and its intended capability
  replacement — `verification/request` never creates a `players` row,
  so the later `discord_accounts` FK insert always fails. 100% failure
  rate on every new player's first verification attempt.
- **Bug #9** — `POST /api/v1/appeals` hardcodes `status="pending"`, but
  `ck_appeals_status` only permits `open`/`accepted`/`denied`. No
  successful path exists to create an appeal at all.
- **Bug #10** — `kick` and `ipban` moderation endpoints write type
  literals never added to `ck_punishments_type` (`warn`/`mute`/
  `tempban`/`ban` only). Both fail 100% of the time.

Bugs #8/#9/#10 share one root pattern: application code and the
database's own check constraints were never reconciled, in three
separate places. Worth treating as one class of bug to audit for
elsewhere, not three unrelated ones.

## Recommendation

None of Phase 7 or Phase 8's own work is implicated by any of this —
both were verified under the same conditions every phase in this
project has always been verified under, and neither touches migrations,
rate-limiting, verification, appeals, or moderation. But these five
findings (the two structural ones plus #7/#8/#9/#10) are more consequential
than moving on to Phase 11/12 or any further feature work, and probably
warrant their own dedicated dispatch before anything else.
