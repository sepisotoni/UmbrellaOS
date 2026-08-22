# DISPATCH: Phase 15 Migration Test — Verify and Run Migrations

**Type:** Sub-chat (read-only + Supabase access)
**Scope:** Read migrations, verify them, run against live DB
**Read-only PAT:** [READ_ONLY_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Supabase project:** isofkwkivftnssorqzkd
**DB password:** [DB_PASSWORD — see head chat]
**Direct port:** 5432 (NOT 6543)

---

## Context

Backend A (running in parallel) is writing two new Alembic migrations:
1. `add_anticheat_violations_table` — new `anticheat_violations` table
2. Appeal model new columns — `action_taken`, `handled_by`, `case_summary`, `closed_at`, `ai_review_status`, `ai_review_result`

Your job: wait for Backend A and B to commit their migrations, then verify and run them.

**DO NOT run migrations until you have read and verified them first.**

---

## Task 1 — Wait and read migrations

Check `umbrella-core-CURRENT/alembic/versions/` for the two new migration files from Phase 15 Backend A and B. If they're not there yet, check the commit log — they should be committed before this chat is sent.

Read both migration files fully. Verify:
- `upgrade()` function is correct SQL
- `downgrade()` function properly reverses the upgrade
- No missing imports
- Column types are appropriate (UUID as String, datetime as DateTime with timezone)
- Indexes are defined for `player_uuid`, `server_id`, `check_name`, `timestamp` on anticheat_violations
- Foreign keys are correct if any

---

## Task 2 — Check existing DB state

Connect to Supabase and check current state:
```sql
-- Check if anticheat_violations table already exists
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'anticheat_violations';

-- Check current appeals table columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'appeals' 
ORDER BY ordinal_position;

-- Check current alembic version
SELECT version_num FROM alembic_version;
```

Report what you find before running anything.

---

## Task 3 — Run migrations

If migrations look correct and the tables/columns don't already exist:

Connect to the Supabase DB directly (port 5432) and run the migration SQL manually — DO NOT use `alembic upgrade head` since the codespace isn't available. Extract the raw SQL from the migration files and run it directly.

After running, verify:
```sql
-- Verify anticheat_violations table
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'anticheat_violations';

-- Verify appeals new columns
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'appeals' AND column_name IN 
('action_taken', 'handled_by', 'case_summary', 'closed_at', 'ai_review_status', 'ai_review_result');

-- Check indexes
SELECT indexname FROM pg_indexes WHERE tablename = 'anticheat_violations';
```

---

## Task 4 — Update alembic_version

After running migrations manually, update the alembic version table to match:
```sql
UPDATE alembic_version SET version_num = '{new_migration_head}';
```

Use the revision ID from the last migration file as the new version.

---

## Handback

Write `dispatches/PHASE15-MIGRATION-TEST/SUBCHAT-HANDBACK.md` with:
- Whether migrations were valid
- What the DB state was before running
- What SQL was run
- Verification results after running
- Any issues found

Do NOT commit to the repo — this chat is read-only on GitHub.
