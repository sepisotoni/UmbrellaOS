# SUBCHAT HANDBACK — Phase 15 Backend A
**Sub-chat:** Backend A (AnticheatViolation + Plugin)
**Completed:** 2026-08-22
**Tip at handback:** ecfe601

---

## All Tasks Complete

### Task 1 — New AnticheatViolation model ✅
**Commit:** `f8d5efe` — `core: add AnticheatViolation model (P15 Task 1)`
**Files changed:**
- `umbrella-core-CURRENT/models/anticheat_violation.py` — new file
- `umbrella-core-CURRENT/models/__init__.py` — added import + `__all__` export

**Model fields:** `id` (UUID PK), `player_uuid` (indexed), `player_name`, `server_id` (nullable, indexed), `check_name` (indexed), `verbose` (Text), `vl` (int), `timestamp` (DateTime, indexed)

---

### Task 2 — Alembic migration ✅
**Commit:** `a579a2b` — `core: add anticheat_violations migration (P15 Task 2)`
**File:** `umbrella-core-CURRENT/alembic/versions/030_add_anticheat_violations_table.py`

- Revision ID: `030_add_anticheat_violations_table`
- Down-revision: `029_feature_flags`
- Creates table with all 8 columns + 4 indexes (player_uuid, server_id, check_name, timestamp)
- `downgrade()` drops all 4 indexes then the table
- **NOT run** — left for Migration Test sub-chat to verify and apply

---

### Task 3 — Update anticheat service ✅
**Commit:** `a9f864f` — `core: write cheat flags to AnticheatViolation table (P15 Task 3)`
**File:** `umbrella-core-CURRENT/services/anticheat_service.py`

**Changes:**
- `handle_cheat_flag()` now accepts `server_id: str | None = None` parameter
- Writes an `AnticheatViolation` row after every processed flag
- Retains the existing `AITask` write (for audit history and tempban context)
- Response dict now includes `violation_id` alongside existing `ai_task_id`

---

### Task 4 — Update GET /api/v1/anticheat/violations ✅
**Commit:** `d72dc96` — `core: query AnticheatViolation in GET /api/v1/anticheat/violations (P15 Task 4)`
**File:** `umbrella-core-CURRENT/api/routers/anticheat.py`

**Changes:**
- `ViolationRecord.id` type corrected from `int` to `str` (UUID)
- `AnticheatFlagRequest` gains `server_id: str | None = None` field
- `POST /flag` now passes `server_id` through to `handle_cheat_flag()`
- `GET /violations` now queries `AnticheatViolation` directly — all three filters (player_uuid, server_id, check_name) are indexed column lookups, not regex parsing
- Removed all the old `AITask` regex parsing, player-map joins, and `server_id=None` stub

---

### Task 5 — Plugin sends server_id ✅
**Commit:** `ecfe601` — `plugin: send server_id in anticheat flag payloads (P15 Task 5)`
**Files changed:**
- `minecraft-plugin/src/main/java/com/umbrellaos/plugin/GrimBridge.java`
- `minecraft-plugin/src/main/java/com/umbrellaos/plugin/UmbrellaPlugin.java`
- `minecraft-plugin/src/main/resources/config.yml`

**Design decisions:**
- `server.id` was already in `config.yml` and read by `UmbrellaPlugin.onEnable()` as `serverId` (used for heartbeat). Reused this — no new config key needed.
- `GrimBridge` constructor gains a `String serverId` parameter. Blank/null → `"default"`.
- `UmbrellaPlugin` passes `serverId` to `new GrimBridge(this, apiClient, serverId)`.
- `buildFlagPayload()` gains a `String serverId` parameter and includes `"server_id":"..."` in the JSON.
- `getServerId()` accessor added for test assertions.
- Old 2-arg `buildFlagPayload(uuid, name, check, verbose, vl)` signature **removed** — any existing tests that called it directly need updating to pass `serverId` as a 6th arg. No test file was present to update.
- `config.yml` `server.id` default changed from `""` to `"default"` and comment expanded to explain anticheat payload tagging.

**Backward compat:** Old core versions (pre-P15) ignore the unknown `server_id` field — Pydantic discards extra keys by default. Plugin update is safe to deploy before core update.

---

## Files Touched (Backend A scope only)

| File | Change |
|------|--------|
| `umbrella-core-CURRENT/models/anticheat_violation.py` | New |
| `umbrella-core-CURRENT/models/__init__.py` | +2 lines |
| `umbrella-core-CURRENT/alembic/versions/030_add_anticheat_violations_table.py` | New |
| `umbrella-core-CURRENT/services/anticheat_service.py` | Updated |
| `umbrella-core-CURRENT/api/routers/anticheat.py` | Updated |
| `minecraft-plugin/src/main/java/com/umbrellaos/plugin/GrimBridge.java` | Updated |
| `minecraft-plugin/src/main/java/com/umbrellaos/plugin/UmbrellaPlugin.java` | 1 line |
| `minecraft-plugin/src/main/resources/config.yml` | Comment + default updated |

---

## Notes for Migration Test Sub-chat

- Migration: `030_add_anticheat_violations_table` — revision chain `029_feature_flags → 030`
- Run: `alembic upgrade 030_add_anticheat_violations_table` (or `alembic upgrade head`)
- Downgrade: `alembic downgrade 029_feature_flags`
- No seed data, no FK constraints, safe to run on live DB

## Notes for Frontend Sub-chat

- `GET /api/v1/anticheat/violations` response `id` field is now a `str` (UUID), not `int` — update TypeScript types if they assumed `number`
- `server_id` filter on that endpoint is now functional
- `violation_id` is available in `POST /api/v1/anticheat/flag` response alongside `ai_task_id`
