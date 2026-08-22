# DISPATCH: Phase 15 Backend A — AnticheatViolation Table + Plugin server_id

**Type:** Sub-chat (write access)
**Scope:** `umbrella-core-CURRENT/` and `minecraft-plugin/` only
**Write PAT:** [WRITE_PAT — see head chat]
**Read-only PAT:** [READ_ONLY_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip at dispatch time:** 185fe32

---

## Context

Read before touching anything:
- `PHASE15-SPEC.md` — full phase spec
- `umbrella-core-CURRENT/models/` — existing model files
- `umbrella-core-CURRENT/alembic/versions/` — existing migrations
- `umbrella-core-CURRENT/api/routers/anticheat.py` — current flag handler
- `umbrella-core-CURRENT/services/anticheat_service.py` — current flag storage logic
- `minecraft-plugin/src/main/java/com/umbrellaos/plugin/GrimBridge.java` — current flag payload

Commit after every task. Push to main after each commit.
Do NOT touch `umbrella-dashboard-CURRENT/`.

---

## Task 1 — New AnticheatViolation model

**File:** `umbrella-core-CURRENT/models/anticheat_violation.py` (new file)

Create a dedicated SQLAlchemy model:
```python
class AnticheatViolation(Base):
    __tablename__ = "anticheat_violations"
    id: str (UUID, primary key)
    player_uuid: str (indexed)
    player_name: str
    server_id: str (indexed, nullable — old records won't have it)
    check_name: str (indexed)
    verbose: str
    vl: int
    timestamp: datetime (indexed)
```

---

## Task 2 — Alembic migration

**File:** `umbrella-core-CURRENT/alembic/versions/XXXX_add_anticheat_violations_table.py`

Write the migration to create the `anticheat_violations` table with the schema above. Follow the exact same pattern as existing migration files. Include both `upgrade()` and `downgrade()`.

DO NOT run the migration — just write the file. A separate test chat will verify and run it.

---

## Task 3 — Update anticheat service to write to new table

**File:** `umbrella-core-CURRENT/services/anticheat_service.py`

Update `handle_cheat_flag()` to write to `AnticheatViolation` instead of (or in addition to) `AITask` rows. Keep the AITask write if it exists — just add the new violation write alongside it.

Fields to map from the incoming flag payload:
- `player_uuid`, `player_name` → direct
- `server_id` → from payload (may be null for old plugin versions)
- `check_name`, `verbose`, `vl` → direct
- `timestamp` → `datetime.now(timezone.utc)`

---

## Task 4 — Update GET /api/v1/anticheat/violations

**File:** `umbrella-core-CURRENT/api/routers/anticheat.py`

The endpoint was added in Phase 14 but queries the wrong table (AITask rows). Update it to query `AnticheatViolation` instead. The response schema stays the same. The `server_id` filter now actually works.

---

## Task 5 — Update Minecraft plugin to send server_id

**File:** `minecraft-plugin/src/main/java/com/umbrellaos/plugin/GrimBridge.java`

The plugin currently posts GrimAC flags to `POST /api/v1/anticheat/flag` without a `server_id` field. Add it.

- The plugin already has access to `config.yml` via `ConfigManager` — add a `server.id` config key (default: `"default"`)
- In the flag payload JSON, add `"server_id": configManager.getServerId()` (or however ConfigManager exposes config values)
- Add `getServerId()` to `ConfigManager.java` if it doesn't exist, reading from `server.id` in config.yml
- Update `minecraft-plugin/src/main/resources/config.yml` to include `server.id: "default"` with a comment explaining it should match the server_id used in the dashboard

---

## Commit Instructions

- `core: add AnticheatViolation model (P15 Task 1)`
- `core: add anticheat_violations migration (P15 Task 2)`
- `core: write cheat flags to AnticheatViolation table (P15 Task 3)`
- `core: query AnticheatViolation in GET /api/v1/anticheat/violations (P15 Task 4)`
- `plugin: send server_id in anticheat flag payloads (P15 Task 5)`

When done write `dispatches/PHASE15-BACKEND-A/SUBCHAT-HANDBACK.md` with all commits and any decisions made.
