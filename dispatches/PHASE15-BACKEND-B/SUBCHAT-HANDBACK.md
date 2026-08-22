# SUBCHAT HANDBACK — Phase 15 Backend B
**Sub-chat:** BACKEND-B (Player Profile + Appeals + AI Review)
**Date:** 2026-08-22
**Status:** All 5 tasks complete ✅

---

## Commits

| Commit | Message | Tasks |
|--------|---------|-------|
| `50117a6` | `core: add GET /api/v1/players/{uuid}/full-profile (P15 Task 1)` | Tasks 1 + 2 |
| `85b55bb` | `core: add POST /api/v1/appeals/{id}/close (P15 Task 3)` | Task 3 |
| `18d54bd` | `core: update appeal AI review with full context (P15 Task 4)` | Tasks 4 + 5 |

> Tasks 1 and 2 were committed together (model + migration + router in same logical unit).  
> Tasks 4 and 5 were committed together (both live in `ai_service.py`, separating them would have created a half-baked intermediate state).

---

## Task 1 — Full player profile endpoint ✅

**File:** `umbrella-core-CURRENT/api/routers/players.py`  
**Endpoint:** `GET /api/v1/players/{uuid}/full-profile`

- Uses `asyncio.gather()` for all 4 parallel DB queries (punishments, appeals, discord, alt groups, anticheat)
- Anticheat section uses a try/import guard (`_HAS_ANTICHEAT`) — if Backend A not merged, returns empty stub; if merged, queries live
- AltGroupMember → AltGroup → other Player records resolved in follow-up queries after gather
- `current_server` is `None` in response — field exists in Player schema but is not persisted in the `players` table (populated by plugin heartbeat at runtime). Noted in code comment
- Route order: `/{uuid}/full-profile` registered **before** `/{uuid}` so FastAPI doesn't swallow it as a UUID

---

## Task 2 — Appeal model close fields + Punishment status ✅

**Files:**
- `umbrella-core-CURRENT/models/player.py` — Appeal and Punishment models updated
- `umbrella-core-CURRENT/alembic/versions/030_appeal_close_fields.py` — migration written, NOT run

**Appeal new fields:**
- `action_taken`: VARCHAR(32) nullable
- `handled_by`: VARCHAR(128) nullable
- `case_summary`: TEXT nullable
- `closed_at`: TIMESTAMPTZ nullable
- `ai_review_status`: VARCHAR(16) nullable
- `ai_review_result`: TEXT nullable (JSON blob)

**Punishment new field:**
- `status`: VARCHAR(32) not null default `'ACTIVE'` — needed by appeal close logic to mark `PARDONED`

**Migration:** `030_appeal_close_fields` — revises `029_feature_flags`

---

## Task 3 — Appeal close endpoint ✅

**File:** `umbrella-core-CURRENT/api/routers/appeals.py`  
**Endpoint:** `POST /api/v1/appeals/{appeal_id}/close`

Actions implemented:
- `ACCEPT` → `punishment.active=False`, `punishment.status="PARDONED"`, `appeal.status="ACCEPTED"`
- `REDUCE_SENTENCE` → `punishment.expires_at=new_expiry`, `appeal.status="REDUCED"` (requires `new_expiry`)
- `REJECT` → `appeal.status="REJECTED"`
- `ESCALATE` → `appeal.status="ESCALATED"`
- `SCHEDULE_REVIEW` → `appeal.status="REVIEW_SCHEDULED"`

Auto-generates case summary, saves `action_taken`, `handled_by`, `case_summary`, `closed_at`.  
Writes `appeal.closed` audit log entry.

**Decision:** `handled_by` is pulled from the `_auth` return value (the actor identifier from `require_permission`). If the auth layer returns a non-descriptive key id, staff username won't appear. Head chat may want to confirm the auth dependency returns a usable username string for the close endpoints.

---

## Task 4 — Appeal AI review with full context ✅

**File:** `umbrella-core-CURRENT/services/ai_service.py`  
**Function:** `review_appeal()`

Changes:
- Parallel fetch: punishment + player + all punishments + previous appeals
- GrimAC ±72hr window around `punishment.created_at` (stubbed if `_HAS_ANTICHEAT=False`)
- Builds structured context string (not raw JSON dump) — first-offence detection, appeal history, check-level summaries
- System prompt returns: `recommendation`, `confidence`, `reasoning`, `punishment_context`, `flag_summary`, `risk_factors`, `mitigating_factors`
- Saves `appeal.ai_review_result` (JSON) and `appeal.ai_review_status`
- On failure: sets `ai_review_status="FAILED"`, commits, re-raises → router returns 503
- Never fakes a result

**Router:** `POST /api/v1/ai/review/appeal/{appeal_id}` now returns 503 (not 400) on failure, includes `ai_result` blob + `ai_review_status` in response for dashboard decision UI.

---

## Task 5 — Player AI review with GrimAC history ✅

**File:** `umbrella-core-CURRENT/services/ai_service.py`  
**Function:** `review_flagged_player()`

Changes:
- Parallel fetch: punishments + suspicion events + AnticheatViolation (last 30 days)
- Builds structured context string: flag counts by check, VL escalation milestones, up to 5 notable verbose strings, punishment breakdown
- System prompt returns: `risk_level`, `confidence`, `reasoning`, `recommendation`, `key_findings`, `mitigating_factors`
- `risk_level` prefixed into `ai_summary` for at-a-glance display in task list
- Router returns 503 on failure
- Never fakes a result

---

## Backend A Stub Status

At dispatch time, `AnticheatViolation` was not yet merged.  
**By the time this sub-chat pushed, Backend A had already merged** (commits `a9f864f`, `d72dc96`, `4747478` visible in log).

The try/import guard in `players.py` and `ai_service.py` resolved correctly — `_HAS_ANTICHEAT = True` in production. The guard is harmless to leave in; it protects against future import errors if the model is ever renamed.

---

## Open Items for Head Chat

1. **`handled_by` on appeal close** — populated from `require_permission()` return value. Confirm this returns the staff username (not just a token/role string). If not, the close endpoint needs an explicit `staff_username` field in the request body.

2. **`current_server` in full-profile response** — hardcoded `None`. This field is live from plugin heartbeats, not persisted in the `players` table. Frontend needs to know it will always be `null` from this endpoint and should fetch live status separately if needed (or Backend A can add a join to `plugin_heartbeats`).

3. **`Punishment.status` backfill** — migration 030 adds `status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'`. All existing rows get `'ACTIVE'`. Rows that were historically pardoned won't get `'PARDONED'` status — they'll still show as `'ACTIVE'` until the next close action touches them. If historical accuracy matters, a data migration is needed.

4. **Appeal `status` column width** — original schema was `String(16)`. New statuses like `REVIEW_SCHEDULED` are 15 chars — fits. `REDUCE_SENTENCE` would be 15 chars for `appeal.status="REDUCED"` (I used the shorter "REDUCED", not the full action name). Fine as-is.

5. **Migration 030 not run** — as instructed. Needs to be run against staging/prod before any close or AI review actions work.

---

## Files Changed

```
umbrella-core-CURRENT/
  api/routers/
    players.py             — Task 1: full-profile endpoint
    appeals.py             — Task 3: close endpoint
    ai_tasks.py            — Tasks 4+5: 503 on failure, ai_result in response
  models/
    player.py              — Task 2: Appeal close fields, Punishment status
  services/
    ai_service.py          — Tasks 4+5: structured context, GrimAC integration
  alembic/versions/
    030_appeal_close_fields.py  — Task 2: migration (not run)
```
