# Database

## Connection
- Supabase PostgreSQL, project: isofkwkivftnssorqzkd
- Async via asyncpg + SQLAlchemy
- Migrations via Alembic (umbrella-core-CURRENT/alembic/versions/)

## Migration rules
- Always use `if not inspect(bind).has_column(table, col)` before adding columns
- Alembic revision IDs must be ≤32 chars (alembic_version column is VARCHAR(32))
- Current head: migration 053
- Chain 001→053 is clean and verified — don't break it

## RLS
- All 65 tables have RLS disabled — pre-launch blocker
- Don't enable without writing policies first or everything locks out
- All DB access goes through FastAPI — no direct Supabase client from dashboard

## Common mistakes
- Raw DB insert instead of going through service layer (bypasses audit log)
- Missing `if_not_exists` on column additions in migrations
- VARCHAR too short — discord_message_id and similar IDs need at least 64 chars
