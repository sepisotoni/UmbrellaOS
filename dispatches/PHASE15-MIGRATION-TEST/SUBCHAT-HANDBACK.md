# SUBCHAT HANDBACK: Phase 15 Migration Test
**Sub-chat:** Migration Test (Verify + Run)
**Date:** 2026-08-22
**Repo tip at start:** `38c85ca`
**Supabase project:** `isofkwkivftnssorqzkd`

---

## Status: ✅ ALL MIGRATIONS APPLIED AND VERIFIED

---

## Migration Verification (Task 1)

Both Phase 15 migration files were present in `umbrella-core-CURRENT/alembic/versions/`:

### `030_add_anticheat_violations_table.py` ✅
- **revision:** `030_add_anticheat_violations_table`
- **down_revision:** `029_feature_flags`
- `upgrade()`: Creates `anticheat_violations` table with correct column types — UUIDs as `String(36)`, timestamp as `DateTime(timezone=True)`, `server_id` nullable (old plugin compat), `verbose`/`vl` have server_defaults
- All 4 required indexes present: `player_uuid`, `server_id`, `check_name`, `timestamp`
- `downgrade()`: Drops indexes then table in correct reverse order ✅
- No missing imports, no FK constraints (clean drop) ✅

### `030_appeal_close_fields.py` ✅
- **revision:** `030_appeal_close_fields`
- **down_revision:** `029_feature_flags`
- `upgrade()`: Adds 6 columns to `appeals` (`action_taken`, `handled_by`, `case_summary`, `closed_at`, `ai_review_status`, `ai_review_result`) + `status` column to `punishments` with `NOT NULL DEFAULT 'ACTIVE'`
- All column types correct, nullable flags appropriate ✅
- `downgrade()`: Drops columns in correct reverse order ✅
- No missing imports ✅

**⚠️ Branch note:** Both migrations share `down_revision = '029_feature_flags'`, forming a legitimate Alembic multi-head branch. Both were recorded in `alembic_version` as dual heads.

**⚠️ Reserved word note:** `verbose` and `timestamp` are Postgres reserved words. Applied with double-quoting in raw SQL — the Alembic migration file itself uses `sa.Column("verbose", ...)` which SQLAlchemy handles via quoting automatically. No defect in the migration file.

---

## DB State Before Running (Task 2)

| Check | Result |
|---|---|
| `anticheat_violations` table | **Did not exist** |
| `appeals` new columns | **None present** — table had: `id, punishment_id, player_uuid, status, message, created_at` |
| `punishments.status` column | **Did not exist** — table had: `id, player_uuid, staff_id, type, reason, created_at, expires_at, active` |
| `alembic_version` table | **Did not exist** — migrations have been applied manually in prior phases |

---

## SQL Run (Task 3)

### Migration 1 — anticheat_violations table
```sql
CREATE TABLE anticheat_violations (
    id VARCHAR(36) PRIMARY KEY,
    player_uuid VARCHAR(36) NOT NULL,
    player_name VARCHAR(64) NOT NULL,
    server_id VARCHAR(128) NULL,
    check_name VARCHAR(128) NOT NULL,
    "verbose" TEXT NOT NULL DEFAULT '',
    vl INTEGER NOT NULL DEFAULT 0,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_anticheat_violations_player_uuid ON anticheat_violations (player_uuid);
CREATE INDEX ix_anticheat_violations_server_id ON anticheat_violations (server_id);
CREATE INDEX ix_anticheat_violations_check_name ON anticheat_violations (check_name);
CREATE INDEX ix_anticheat_violations_timestamp ON anticheat_violations ("timestamp");
```
Applied via `Supabase:apply_migration` — **success**.

### Migration 2 — appeal_close_fields
```sql
ALTER TABLE appeals ADD COLUMN action_taken VARCHAR(32) NULL;
ALTER TABLE appeals ADD COLUMN handled_by VARCHAR(128) NULL;
ALTER TABLE appeals ADD COLUMN case_summary TEXT NULL;
ALTER TABLE appeals ADD COLUMN closed_at TIMESTAMPTZ NULL;
ALTER TABLE appeals ADD COLUMN ai_review_status VARCHAR(16) NULL;
ALTER TABLE appeals ADD COLUMN ai_review_result TEXT NULL;

ALTER TABLE punishments ADD COLUMN "status" VARCHAR(32) NOT NULL DEFAULT 'ACTIVE';
```
Applied via `Supabase:apply_migration` — **success**.

---

## alembic_version Update (Task 4)

`alembic_version` table did not exist — created it with `VARCHAR(128)` primary key (Alembic's actual schema) and inserted both heads:

```sql
CREATE TABLE alembic_version (
    version_num VARCHAR(128) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version (version_num) VALUES ('030_add_anticheat_violations_table');
INSERT INTO alembic_version (version_num) VALUES ('030_appeal_close_fields');
```

---

## Verification Results After Running (Task 3 post-checks)

### anticheat_violations columns ✅
| column | type | nullable | default |
|---|---|---|---|
| id | varchar | NO | — |
| player_uuid | varchar | NO | — |
| player_name | varchar | NO | — |
| server_id | varchar | YES | — |
| check_name | varchar | NO | — |
| verbose | text | NO | `''` |
| vl | integer | NO | `0` |
| timestamp | timestamptz | NO | `now()` |

### anticheat_violations indexes ✅
- `anticheat_violations_pkey` (id)
- `ix_anticheat_violations_player_uuid`
- `ix_anticheat_violations_server_id`
- `ix_anticheat_violations_check_name`
- `ix_anticheat_violations_timestamp`

### appeals new columns ✅
| column | type | nullable |
|---|---|---|
| action_taken | varchar | YES |
| handled_by | varchar | YES |
| case_summary | text | YES |
| closed_at | timestamptz | YES |
| ai_review_status | varchar | YES |
| ai_review_result | text | YES |

### punishments.status ✅
- type: `varchar`, NOT NULL, default: `'ACTIVE'`

### alembic_version ✅
```
030_add_anticheat_violations_table
030_appeal_close_fields
```

---

## Issues Found

1. **`verbose` is a Postgres reserved word** — the migration file's use of `sa.Column("verbose", ...)` is fine (SQLAlchemy quotes it), but direct SQL needed `"verbose"`. Not a defect in the migration file itself.
2. **`alembic_version` table did not exist** — created fresh as part of this task. Used `VARCHAR(128)` to accommodate the full-length revision IDs (the migration files use `VARCHAR(32)` in the Alembic spec, but the actual revision strings are longer than 32 chars).
3. **Dual `down_revision`** — both migrations point to `029_feature_flags`. This is valid Alembic multi-head branching. Both heads are recorded in `alembic_version`. If Alembic is run later with `upgrade head`, it will find both already applied and no-op correctly.

---

## Summary

Both Phase 15 migrations are **valid, applied, and verified**. The live Supabase DB now has:
- `anticheat_violations` table with all 8 columns and 4 indexes
- `appeals` table extended with 6 close/AI-review columns
- `punishments` table extended with `status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'`
- `alembic_version` tracking both `030` heads
