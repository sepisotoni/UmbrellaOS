# UmbrellaOS — Bugfix Dispatch 01 (BUGFIX-01)

Read `CLAUDE.md` then `PROJECT-PRINCIPLES-AND-WORKING-RULES.md` first.
You have **read-only** repo access — hand back a zip with a diff/manifest, don't push.

Repo: `https://github.com/sepisotoni/UmbrellaOS`
Read-only PAT: `[READ-ONLY-PAT — provided by Sepiso Toni in starter prompt]`
Clone with: `git clone https://x-access-token:<PAT>@github.com/sepisotoni/UmbrellaOS.git`
Current tip: `2e67ce7`

This dispatch is scoped to the six items from
`CRITICAL-FINDINGS-2026-08-17.md` plus one addition (item 7 below, a
fail-closed fix decided this session). Don't touch anything under
`minecraft-plugin/` or `umbrella-dashboard-CURRENT/`.

Required reading before anything else:
- `CRITICAL-FINDINGS-2026-08-17.md` — full repro steps and reasoning for
  bugs #7–10 and the two structural issues.
- `dispatches/BUGFIX-SWEEP-2026-08-17.md` — the original scope doc; this
  dispatch doc supersedes it where they differ.

---

## Head-chat pre-verification (facts you can rely on — independently confirmed)

The following were read directly from the current source before this
dispatch was written. Don't re-derive these; start from them:

**Bug #9 (appeals status):** `api/routers/appeals.py` line 104 writes
`status="pending"`. `alembic/versions/002_phase3_foundation_models.py`
line 53: `CheckConstraint("type IN ('warn', 'mute', 'tempban', 'ban')",
name="ck_punishments_type")` — wait, that's punishments. The appeals
constraint is separate. Locate `ck_appeals_status` yourself in the
migration chain and confirm the valid values before picking the fix. The
likely correct fix is `"open"` (the intended initial state), but **check
the constraint before assuming**.

**Bug #10 (kick/ipban type mismatch):** `api/routers/moderation.py`
writes `type="kick"` (line 95) and `type="ipban"` (line 206).
`alembic/versions/002_phase3_foundation_models.py` line 53 confirms
`ck_punishments_type` only permits `warn`/`mute`/`tempban`/`ban` —
`kick` and `ipban` are absent. Decide the right fix: add `kick`/`ipban`
to the constraint (they're real moderation actions that belong there),
or change the app code to write valid types (probably wrong — `kick` and
`ipban` are semantically different from ban/warn). A new migration is
needed either way.

**Bug #8 (verification always fails for new players):** The bug is in
the `request` flow, not the `confirm` flow. `confirm_verification` in
`services/verification/service.py` does `account.player_uuid =
verification_code.player_uuid` and inserts/updates a `discord_accounts`
row, with a FK to `players.uuid`. But the `request` flow never creates
a `players` row for a new player. Find where `/verify` or the
`verification.request` capability creates a `VerificationCode` and
confirm the player row is never inserted there — then fix it by
inserting a `players` row during the request step if one doesn't already
exist for that UUID. Check what columns `players` requires to be not-null
before writing the fix.

**Bug #7 (rate-limiter TTL loss):** `services/rate_limit_service.py`.
`RateLimiter.check()` does `count = await self._redis.incr(key)` then
`if count == 1: await self._redis.expire(key, window_seconds)`. If the
`expire` call fails after a successful `incr` (connection drop between
the two calls), the key has no TTL and wedges permanently. Fix: make
INCR + EXPIRE atomic via a Redis pipeline, or use a Lua script. The
pipeline approach (`async with self._redis.pipeline() as pipe:
pipe.incr(key); pipe.expire(key, window_seconds, nx=True);
results = await pipe.execute()`) is the simplest correct fix — `NX` on
`EXPIRE` ensures you don't reset a valid TTL mid-window on a key that
already has one.

**Migration chain gaps:** `001_initial.py` through `028_plugin_execution_records.py`
contain zero `create_table` calls for `users`, `sessions`,
`discord_oauth_pending`, `plugin_commands`, or `plugin_heartbeats`. This
was confirmed by the head chat. `plugin_heartbeats` specifically: check
whether it has its own model file before adding a migration for it — the
Gemini sweep flagged `plugin_heartbeat.py` exists, confirm its table
name. Audit every model file in `models/` for its `__tablename__` and
cross-reference against `grep -r "create_table" alembic/versions/` to
find every gap, not just the five known ones — the original finding grep
was for `users` specifically, not exhaustive.

**`plugin_command.py` import (Gemini claim, not independently
verified):** `models/plugin_command.py` line 4: `from database import
Base`. `database/__init__.py` re-exports `Base` from `.engine`, so this
import resolves correctly — the Gemini sweep's "broken import" claim
appears wrong. Confirm before spending time on it, don't assume it needs
fixing.

**`ai_service.py` truncation (Gemini claim, not independently
verified):** The head chat read `services/ai_service.py` tail and it
ended with a complete function. The Gemini claim of a truncated mid-
statement file appears wrong for the current commit. Confirm before
acting.

**`capabilities/hosting.py` truncation (Gemini claim, not independently
verified):** Same — head chat read the tail and it ended with a complete
function. Confirm.

---

## Seven items in scope, fix in this order

### 1. Bug #9 — appeals status/constraint mismatch
Fix `api/routers/appeals.py` to write the constraint-valid initial
status. Locate `ck_appeals_status` in the migrations to confirm the
valid values first. Retest: `POST /api/v1/appeals` succeeds and returns
a constraint-valid status.

### 2. Bug #10 — kick/ipban type/constraint mismatch
Add `kick` and `ipban` to `ck_punishments_type` via a new migration
(`029_...`). Don't change the app code — `kick` and `ipban` are
semantically distinct from the existing types and should be in the
constraint. Retest: both `POST /api/v1/moderation/kick` and
`POST /api/v1/moderation/ipban` succeed against real Postgres.

### 3. Bug #8 — verification.confirm always fails for new players
Fix the `request` flow to create a `players` row if one doesn't exist
for the given UUID. Check required columns. Retest: a genuinely new
player UUID completes the full request→confirm flow end-to-end against
real Postgres.

### 4. Bug #7 — rate-limiter TTL loss
Fix `services/rate_limit_service.py` `RateLimiter.check()` to make INCR
and EXPIRE atomic (pipeline with `expire(key, window, nx=True)` is the
recommended approach above). Retest under conditions that can actually
reproduce a stuck key, not just the happy path.

### 5. Hermetic test suite
Get a real Redis into the test environment (or explicitly disable/mock
the rate limiter in `tests/conftest.py` for tests that don't test it —
a `TESTING=true` env var bypassing the real middleware, or a
`fakeredis` backend). Then run the full suite against real Redis and
triage every failure: which are resolved by fixes #7–10 above, which
are separate real bugs, and which are test-setup artifacts. Report the
breakdown in your handback — not just a final pass count.

### 6. Migration chain — add missing create_table migrations
Audit every `models/*.py` file for its `__tablename__`, cross-reference
against `grep -r "create_table" alembic/versions/` to find every table
with no migration. Add `create_table` migrations for all of them as a
new migration (`030_...` or continuing from wherever 029 lands). **Verify
by running `alembic upgrade head` against a genuinely empty Postgres
database** — not `Base.metadata.create_all()`, not a pre-populated DB.
This project has never had this succeed once. Report the actual command
output in your handback.

### 7. BanEnforcer fail-closed (new, decided this session)
`minecraft-plugin/src/main/java/com/umbrellaos/plugin/BanEnforcer.java`
currently fails open: if `umbrella-core` is unreachable during a login
check, a banned player is allowed to join. Change it to fail closed:
if the HTTP call fails (IOException, InterruptedException, non-2xx, or
any exception from the response parse), **kick the player** rather than
allowing them in.

This is a deliberate one-flag-flip decision, not a judgment call — don't
soften it or make it configurable without asking. The kick message should
say something like "Unable to verify ban status — please try again
shortly." Retest: simulate a core-unreachable condition (wrong URL or
core not running) and confirm the player is kicked, not allowed in.

---

## Explicitly out of scope

- `mute` punishment type — flagged as an open product decision, not
  decided, don't touch.
- Anything the Gemini sweep flagged that you can't reproduce independently
  in code — note it in your handback, don't fix a Gemini hallucination.
- Anything under `umbrella-dashboard-CURRENT/`, `minecraft-plugin/`
  (except item 7 above), or `umbrella-sdk-ts/`.
- Any Phase 11/12 work.
- The two minor ergonomics notes from review-6 (missing SECRET_KEY in
  .env.example, id/subscription_id naming inconsistency in webhooks) —
  opportunistic only if you're already in those files, not the point.

---

## Testing standard

Every fix verified against real Postgres and (where relevant) real Redis.
Not unit tests only. Not `Base.metadata.create_all()` standing in for
real migrations. This dispatch exists because past verification silently
relied on unstated environmental gaps — don't reproduce that pattern
while fixing it.

---

## Deliverable for handback

Zip containing:
1. Modified files (full, not just diffs — easier to apply cleanly).
2. A `git diff` or file manifest listing every changed file.
3. Handback doc covering:
   - Status of each of the 7 items (done / partial / blocked, with why).
   - For each: what changed, how verified live, exact before/after result.
   - Full test-suite triage breakdown from item 5.
   - Actual `alembic upgrade head` output from item 6.
   - Anything noticed outside these 7 items, flagged but not acted on.
   - Explicit confirmation of which Gemini claims you reproduced vs.
     couldn't reproduce.
4. Leak-checked before zipping: `find . -iname ".env" -o -iname "*.db"
   -o -iname "*.sqlite*"`.

Session label for any commits in a scratch clone: `subchat-bugfix-01`.
