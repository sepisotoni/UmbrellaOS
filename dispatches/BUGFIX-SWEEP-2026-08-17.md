# Bugfix Sweep — the 6 findings from CRITICAL-FINDINGS-2026-08-17.md

You are a scoped sub-chat. **Read `CLAUDE.md` at the repo root first, in
full**, then `PROJECT-PRINCIPLES-AND-WORKING-RULES.md`. Read-only repo
access, hand back a diff/manifest, don't push.

**Required reading before anything else:** `CRITICAL-FINDINGS-2026-08-17.md`
at the repo root, in full — it has the exact repro steps, file locations,
and reasoning for every bug below. This dispatch doc is a scope summary,
not a replacement for reading it.

This is a standalone dispatch, not part of the Phase 13 (Minecraft plugin)
series — don't touch anything under `minecraft-plugin/` or the
`dispatches/PHASE13-MINECRAFT-PLUGIN/` docs.

## Scope — six items, fix all of them, in this order

### 1. Bug #9 — appeals status/constraint mismatch
`POST /api/v1/appeals` hardcodes `status="pending"`;
`ck_appeals_status` only permits `open`/`accepted`/`denied`. Pick the
correct fix (likely: write `"open"` instead of `"pending"`, since that
reads as the intended initial state — but check callers/frontend
expectations for `"pending"` before assuming, in case something else
depends on that literal). Retest: create an appeal, confirm it succeeds
and lands with a constraint-valid status.

### 2. Bug #10 — kick/ipban type/constraint mismatch
Both write type literals never added to `ck_punishments_type`
(`warn`/`mute`/`tempban`/`ban` only). Reconcile app code and constraint —
either add the missing types to the constraint, or fix the app code to
write valid ones, whichever is actually correct per what `kick`/`ipban`
are supposed to represent. **Use the chat bridge's `player_uuid="server"`
→ NULL-out pattern as the reference** for `ipban`'s `player_uuid="SYSTEM"`
case if that's part of what's broken there — `CRITICAL-FINDINGS-2026-08-17.md`
and `cross-chat-findings/review-6-untested-surfaces-2026-08-17.md` both
flag this as the correct pattern already proven to work elsewhere in this
codebase. Retest both `kick` and `ipban` live against real Postgres.

### 3. Bug #8 — verification.confirm always fails for new players
`verification/request` never creates a `players` row, so the later
`discord_accounts` FK insert always fails. Fix: create the `players` row
during `verification/request` (or wherever the real gap is — confirm
against the actual code, don't assume the fix location from the finding
doc's summary alone). Retest: a genuinely new player's first verification
attempt, end to end, against real Postgres.

### 4. Bug #7 — rate-limiter TTL loss
`RateLimiter.check()` only sets a key's TTL on the request that creates it
(`count == 1`); a lost `EXPIRE` call leaves a permanently-wedged counter.
Fix by making the count-increment and TTL-set atomic (e.g. Redis pipeline,
or `SET key val EX seconds NX`-style single command instead of two
separate calls that can race or partially fail). This needs more than a
one-line fix and more than a unit test — retest under conditions that can
actually reproduce the original stuck-key symptom (`ttl=-1`, high count),
not just a fresh-key happy path, against real Redis.

### 5. Hermetic test suite
`tests/conftest.py` needs to actually account for the real rate-limit
middleware being active during test runs, rather than relying on Redis
happening to be absent. Get a real Redis into the test environment (or
explicitly, visibly disable/mock the rate limiter for tests that aren't
testing it) so `pytest` results stop being conditional on an unstated
environmental fact. Once that's in place, **run the full suite against
real Redis and triage the failures** — don't assume they're all one root
cause. Categorize: how many are caused by bugs #7–10 above (should
resolve once those are fixed), how many are separate real bugs, and how
many are test-setup artifacts of the previous fail-open masking. Report
the breakdown in your handback, not just a final pass count.

### 6. Migration chain can't bootstrap a fresh database
`users`, `sessions`, `discord_oauth_pending`, `plugin_commands`, and
`plugin_heartbeats` are never created by any migration in the `001`→`028`
chain. Add the missing `create_table` migrations for all five (check for
any other tables with the same gap while you're auditing this — the
finding doc's grep was for `users` specifically as the confirmed case,
not necessarily exhaustive for every table). **Verify by actually running
`alembic upgrade head` against a genuinely empty Postgres database** —
not `Base.metadata.create_all()`, not a database that already has tables
from a prior run. This project has never had this succeed once; don't
report success without having actually done this specific test.

## Explicitly out of scope

- Bug `mute` being unreachable — that's a flagged product decision
  (add a route, or drop it from the constraint), not a bug to silently
  resolve either way. Note it in your handback, don't decide it yourself.
- The two minor ergonomics notes from `review-6` (missing `SECRET_KEY` in
  `.env.example`, `id`/`subscription_id` naming inconsistency in the
  webhooks capability) — small enough to fix opportunistically if you're
  already in those files, but not the point of this dispatch; don't go
  out of your way for them.
- Anything not in the six items above. If you notice something else that
  looks broken while working through these, note it in your handback,
  don't expand scope to fix it.

## Testing standard for this whole dispatch

Every fix needs to be verified against real Postgres and (where relevant)
real Redis — not just unit tests, and not `Base.metadata.create_all()`
standing in for real migrations. This entire dispatch exists because past
verification silently relied on unstated environmental gaps (Redis
absent, `create_all()` instead of migrations) — don't reproduce that
pattern while fixing it.

## Deliverable for handback

- Diff/manifest package covering all six items.
- For each item: what changed, how it was verified live, and the exact
  before/after result (e.g. "appeal creation: was 100% failure, now
  succeeds; confirmed via live POST against real Postgres").
- The full test-suite triage breakdown from item 5.
- Confirmation that `alembic upgrade head` was run against a genuinely
  empty database and passed (item 6) — with the actual command output,
  not a summary claim.
- Anything noticed outside these six items, flagged but not acted on.
