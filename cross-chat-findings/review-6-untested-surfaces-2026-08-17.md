# UmbrellaOS — remaining untested surfaces, live Postgres test

Date: 2026-08-17
Scope: fresh sandbox, not the persistent `sturdy-tribble-r49xx959q7wxhwg5`
codespace used by prior reviews. Cloned `github.com/sepisotoni/UmbrellaOS`
read-only, real Postgres 16 + Redis 7 installed and run locally, app booted
via `uvicorn main:app` (real `create_tables()` startup path — the migration
chain's inability to bootstrap fresh is bug #1, already confirmed repeatedly,
not re-tested here). No application code was changed. Picked up exactly the
items prior reviews explicitly flagged as unexercised, to avoid duplicating
work already covered in `review-2` through `review-5`, `CRITICAL-FINDINGS`,
and the subchat logs.

## 1. `tempban` — reachable and confirmed working (review-5 left this open)

Review-5 noted `mute` was untested because "no route calls it" but didn't
check `tempban` specifically, and the constraint-vs-code audit only called
out `kick`/`ipban` as broken. Checked: `tempban` **is** reachable — not via
its own route, but via `POST /moderation/ban` with `is_temporary: true`
(`api/routers/moderation.py:156`, `type="tempban" if body.is_temporary else
"ban"`).

Live test against real Postgres:
```
POST /api/v1/moderation/ban {"player_uuid": "...", "reason": "...",
  "is_temporary": true, "expires_at": "2026-08-20T00:00:00Z"}
→ 201, {"type":"tempban", "active":true, "expires_at":"2026-08-20T00:00:00Z", ...}
```
Row landed correctly in `punishments` with the right `type`/`expires_at`.
**Confirmed working, not a bug.** `ck_punishments_type` allows `tempban` and
the app never writes anything outside that set for this path — unlike
`kick`/`ipban` (bug #10), this one was already reconciled correctly.

`mute` remains genuinely unreachable: grepped `api/` and `capabilities/`
again for any route/capability writing `type="mute"` — none exists anywhere
in the codebase. Not a bug (nothing broken), just dead constraint vocabulary
with no code path to reach it. Worth a product decision (add a mute route,
or drop `mute` from the constraint) rather than further testing — there's
nothing left to test until one exists.

## 2. Chat bridge (`/api/v1/bridge/*`) — fully confirmed working

Named directly in review-5's constraint audit as "not exercised this pass."
Exercised the full surface live against real Postgres:

- `POST /bridge/message` with `source: "minecraft"` (real player_uuid) → `200`,
  row landed in `chat_messages` with `source="minecraft"`, correct FK.
- `POST /bridge/message` with `source: "discord"` → `200`, row landed with
  `source="discord"`, `discord_id` set, `player_uuid` correctly `NULL`.
- `POST /bridge/message` with `player_uuid: "server"` (the code's own system-
  sender sentinel, `api/routers/bridge.py`: *"Treat 'server' as a system
  sender — skip FK constraint by nulling it out"*) → `200`, `player_uuid`
  correctly written as `NULL`, no FK violation. This is the same sentinel-value
  pattern that broke `ipban` (bug #10's `player_uuid="SYSTEM"`), but here it's
  handled correctly by nulling instead of writing a non-existent FK value —
  worth citing as the reference pattern if `ipban` ever gets fixed.
- `GET /bridge/messages` → `200`, all three rows returned correctly ordered.
- `PATCH /bridge/settings` (`mode: "full"`, both directions on) → `200`,
  settings rows created/updated correctly, `GET /bridge/settings` reflects it.

**`ck_chat_messages_source` is not a bug.** App code only ever writes
`"minecraft"` or `"discord"` (validated explicitly before the DB write,
`bridge.py`: `if body.source not in ("minecraft", "discord"): raise 400`),
matching the constraint exactly. This is the one constrained-field case in
the whole codebase where app code and DB constraint were actually reconciled
correctly — contrast with bugs #9/#10 (appeals, kick/ipban) which are the
same pattern done wrong.

## 3. Plugin-key-authenticated write paths — fully confirmed working

Explicitly called out as not exercised in `review-3` ("would need a real
plugin API key, not the owner session token used throughout that pass").

Found the actual mechanism: `require_plugin_key`
(`api/middleware/auth.py`) checks against `settings.secret_key`, which is a
**different** setting from `settings.admin_key` (used by `require_admin_key`
for dashboard/bridge-message auth) — both default to
`"change-me-in-production"` but are independently configurable. This repo's
`.env.example` only documents `ADMIN_KEY`; `SECRET_KEY` isn't mentioned
there at all, so a fresh deployer would have no way to know the plugin key
is a separate value from the admin key unless they read
`config/settings.py` directly. Not a functional bug (the two-tier design
works as coded) but a real documentation gap worth a note in
`.env.example`.

Live-tested all four plugin routes with the correct key (`X-Plugin-Key:
change-me-in-production`, the default `secret_key`), against real Postgres:

- `GET /plugin/health` → `200`, `{"status":"ok","database":"connected",...}`.
- `POST /plugin/heartbeat` (create) → `200`, real row inserted into
  `plugin_heartbeats`.
- `POST /plugin/heartbeat` (same `server_id`, different values, second call)
  → `200`, confirmed via direct DB query this is a **real upsert** — one row,
  updated values (`online_count` 5→9, `tps` 19.8→19.5,
  `plugin_version` 1.0.0→1.0.1), not a duplicate insert.
- `GET /plugin/config` → `200`, real settings bundle returned, correctly
  excludes `sensitive=True` rows, correct `by_category` grouping.
- `POST /plugin/control` → `200`, real row inserted into `plugin_commands`
  with `status="pending"`.
- Wrong key (`X-Plugin-Key: wrong-key`) → `401`, confirmed rejected as
  expected — auth isn't just accepting anything.

**All four plugin-facing write/read paths confirmed genuinely functional
against live Postgres, including a real upsert semantics check that hadn't
been done anywhere in this project's history yet.**

## 4. Webhook subscription CRUD (`webhooks.subscription.*`) — fully confirmed working

Not mentioned as tested or untested in any prior review — Phase 7 built it,
nothing in `cross-chat-findings/` had exercised it live. Full lifecycle
tested against real Postgres via the capability registry (these are
capabilities, not a bespoke router — reachable at
`/api/v1/capabilities/{name}/invoke`, per this codebase's own "no shadow
APIs" rule, `capabilities/webhooks.py`'s own module docstring):

- `webhooks.subscription.create` → `200`, real row created, real signing
  `secret` returned (and, confirmed via a second `list` call right after,
  the secret is correctly *not* re-exposed on list — only present in the
  creation response, matching the code's own docstring claim).
- `webhooks.subscription.list` → `200`, returns the real row.
- `webhooks.subscription.update` → first attempt with `{"id": ...}` failed
  `422` (`subscription_id` field required, not `id` — a real param-name
  gotcha for any caller guessing the schema instead of reading it). Retried
  with the correct field name → `200`, `active: false` genuinely persisted.
- `webhooks.subscription.delete` → `200`, `{"deleted": true}`, confirmed
  gone via a follow-up `list` (empty array).

**No bugs — full CRUD lifecycle genuinely works.** The one thing worth a
note: `update`/`delete` take `subscription_id`, not `id`, unlike the
`create`/`list` responses which use `id` as the field name — a real but
minor API-consistency wrinkle, not a functional defect.

## 5. Automation schedules (`automation.schedule.*`) — CRUD **and** live cron execution both confirmed working

Also never exercised live anywhere in this project's history. Went beyond
CRUD to confirm the actual background execution loop works, not just the
database rows:

- `automation.schedule.create` (cron `0 3 * * *`, scheduling the harmless
  `webhooks.subscription.list` capability as the test payload) → `200`,
  real row, `enabled: true`, `last_run_at: null` as expected for a
  never-run schedule.
- `automation.schedule.list` → `200`, real row returned.
- `automation.schedule.set_enabled` (`false`) → `200`, persisted correctly.
- `automation.schedule.delete` → `200`, confirmed gone via follow-up list.
- **Live execution test**: created a second schedule with cron `* * * * *`
  (due every minute) at `18:22:40 UTC`, waited 90s with zero further
  interaction, then re-listed. Result: `last_run_at:
  "2026-08-17T18:23:26...+00:00"`, `last_run_status: "success"`,
  `last_run_error: null` — the app's own background
  `run_scheduler_loop` task (wired into `main.py` startup via
  `asyncio.create_task`, confirmed by reading the source before testing)
  genuinely woke up, found the due schedule, and executed it through the
  real capability registry (`registry.call()`) with no human triggering it.

**This is the first time this project's automation scheduler has been
confirmed to actually fire on its own, live** — every prior mention of
Phase 4/7 in this codebase's history was about the CRUD surface or the
code existing, not about watching the cron loop genuinely execute a
capability unattended. No bugs found; this is a real, working feature.

## Not exercised this pass (same reasons as before, still genuinely blocked)

- Discord OAuth round-trip — still requires real Discord app credentials,
  out of scope for any sandboxed environment.
- Dashboard mobile-viewport check on the 5 routes review-3 didn't get to
  (`/dashboard`, `/activity`, `/marketplace`, `/settings`, `/topology` —
  only `/fleet` was screenshotted and found broken). Attempted this pass:
  blocked by this sandbox's network allowlist not including a Playwright
  browser-binary download host, so headless-Chrome screenshots aren't
  reproducible here. Needs a session with that network access, not a code
  or logic gap.
- `ipban`'s `player_uuid="SYSTEM"` secondary FK question (review-5) — still
  can't be reached independently since the `ck_punishments_type` check fails
  first; would need bug #10 fixed before this is testable at all.

Session notes: five previously-unexercised surfaces (`tempban`, chat
bridge, plugin-key writes, webhook subscription CRUD, automation schedule
CRUD + live cron execution) all confirmed genuinely working against real
Postgres, no new bugs found in any of them — a real negative result, not
just unexplored territory anymore. Two minor API-ergonomics notes (missing
`SECRET_KEY` in `.env.example`; `id` vs `subscription_id` field-name
inconsistency between webhook create/list and update/delete). No
application code changed this pass.

**Note on git access:** this session cloned with a read-only PAT per the
project's own two-PAT convention (see `PROJECT-PRINCIPLES-AND-WORKING-RULES.md`)
— confirmed read-only for real: `git push` returned a real `403` from
GitHub. This file exists only in the sandbox this session ran in
(`/home/claude/UmbrellaOS/cross-chat-findings/` there) and needs to be
copied into the real repo by a session holding the read-write PAT.
