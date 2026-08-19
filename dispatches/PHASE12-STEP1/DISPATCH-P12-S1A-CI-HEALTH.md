# Phase 12 S1A — CI/CD + Health Check Extension

Read-only repo access. Hand back a zip, don't push.
Repo: `https://github.com/sepisotoni/UmbrellaOS`
Read-only PAT: [READ-ONLY-PAT — provided by Sepiso Toni in starter prompt]

## Files to read before writing anything

- `umbrella-core-CURRENT/api/routers/health.py` — existing `/health` endpoint
- `umbrella-core-CURRENT/main.py` lines ~180–193 — how Redis is already wired
- `umbrella-core-CURRENT/config/settings.py` — `redis_url` field
- `umbrella-core-CURRENT/tests/test_health.py` — existing health tests, don't duplicate
- `umbrella-core-CURRENT/requirements.txt` — confirm `fakeredis` is already there

That's it. Don't read anything else unless you hit something unexpected.

---

## Item 1 — Extend `/health` to check Redis

Add a Redis ping to `GET /health`. New response shape:
```json
{
  "status": "ok",          // "ok" only if both DB + Redis up, else "degraded"
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected",    // or "unreachable"
  "service": "umbrella-core"
}
```

- Inject Redis via a `Depends` (add a `get_redis` dependency somewhere clean,
  constructed from `settings.redis_url`)
- Ping with `await redis.ping()`, catch `redis.exceptions.RedisError`
- Endpoint stays public, no auth

**Tests:** add to `tests/test_health.py`. Two cases: Redis reachable
(use `fakeredis.aioredis.FakeRedis`), Redis unreachable (mock `ping()`
to raise `RedisError`). Run just these tests and include output in handback.

---

## Item 2 — GitHub Actions workflows

Create `.github/workflows/` with three files:

**`backend-ci.yml`** — triggers on push/PR to main:
1. Checkout, Python 3.11
2. `pip install -r umbrella-core-CURRENT/requirements.txt`
3. Start Redis: `sudo apt-get install -y redis-server && sudo redis-server --daemonize yes`
4. Postgres via `services:` block: `postgres:15`, env `POSTGRES_PASSWORD=test POSTGRES_DB=umbrella_test`
5. Env vars: `DATABASE_URL=postgresql+asyncpg://postgres:test@localhost/umbrella_test`, `REDIS_URL=redis://localhost:6379/0`, `SECRET_KEY=ci-test-secret`, `ADMIN_KEY=ci-test-admin`, `PLUGIN_KEY=ci-test-plugin`
6. `cd umbrella-core-CURRENT && python -m pytest tests/ -x --tb=short`

**`dashboard-ci.yml`** — triggers on push/PR to main:
1. Checkout, Node 20
2. `cd umbrella-dashboard-CURRENT && npm ci`
3. `npx tsc --noEmit && npm run lint && npm run build`

**`plugin-ci.yml`** — triggers on push/PR to main:
1. Checkout, Java 21 (use 21 LTS — pom.xml says 25 which isn't LTS and
   may not be available; note in handback if this causes a compiler mismatch)
2. `cd minecraft-plugin && mvn test -B`
   Note: will fail if `GrimAPI:1.1.0.0` isn't resolvable from
   `repo.grim.ac/snapshots` — flag it but don't work around it.

Use: `actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`,
`actions/setup-java@v4`, `actions/upload-artifact@v4`.

Workflows can't be live-tested from a read-only clone — just make sure
YAML is valid. Head chat will verify on push.

---

## Deliverable

Zip with:
1. New/modified files in full
2. File manifest
3. Short handback doc: status of each item, new health test output,
   any known CI blockers, anything noticed outside scope
4. Leak check output: `find . -iname ".env" -o -iname "*.db" -o -iname "*.sqlite*"`
