# UmbrellaOS — Phase 12 Step 1A: CI/CD + Health Check Extensions

Read `CLAUDE.md` then `PROJECT-PRINCIPLES-AND-WORKING-RULES.md` first.
Read-only repo access — hand back a zip, don't push.

Repo: `https://github.com/sepisotoni/UmbrellaOS`
Read-only PAT: [READ-ONLY-PAT — provided by Sepiso Toni in starter prompt]
Clone: `git clone https://x-access-token:<PAT>@github.com/sepisotoni/UmbrellaOS.git`
Current tip: `085688c`

This is a backend-only dispatch. Don't touch `umbrella-dashboard-CURRENT/`,
`minecraft-plugin/`, or anything Phase 11/13 related.

Parallel dispatch running: `DISPATCH-P12-S1B-FEATURE-FLAGS.md` — that
sub-chat is building feature flags (new model/service/capability). Don't
touch `models/feature_flag.py`, `services/feature_flag_service.py`, or
`capabilities/feature_flags.py` — those are theirs. No other overlap.

---

## Context — what already exists

Read these before writing anything:

- `umbrella-core-CURRENT/api/routers/health.py` — existing `/health`
  endpoint. Returns DB connectivity + hardcoded `"version": "1.0.0"`.
  No Redis check. No Redis import in this file.
- `umbrella-core-CURRENT/main.py` — Redis is already wired for rate
  limiting: `_redis_asyncio.from_url(settings.redis_url)`. That same
  client or a new one from the same URL can be used for the health check.
- `umbrella-core-CURRENT/config/settings.py` — `redis_url` field exists,
  defaults to `redis://localhost:6379/0`.
- `umbrella-core-CURRENT/tests/test_health.py` — existing health tests,
  read before adding new ones so you don't duplicate.
- `umbrella-core-CURRENT/tests/conftest.py` — no Redis fixture currently.
  `fakeredis` is in `requirements.txt` (already a dep, not dev-only).

---

## Item 1 — Extend `/health` to include Redis

**What to build:**

Add a Redis connectivity check to `GET /health`. The response should
include a `redis` field: `"connected"` or `"unreachable"`. Overall
`status` should be `"ok"` only if both DB and Redis are reachable;
`"degraded"` if either is down.

The health endpoint must stay **public, no auth required** — don't add
auth middleware to it.

**Implementation notes:**
- Don't create a module-level Redis client in `health.py` — inject it.
  The cleanest approach: add a `get_redis` dependency (similar to
  `get_db`) in `database/` or a new `dependencies/` file, constructed
  from `settings.redis_url`. Wire it into the health handler via
  `Depends`.
- Ping Redis with `await redis.ping()`, catch `redis.exceptions.RedisError`
  the same way the rate limiter does.
- Don't change the existing response fields — add to them.

**Tests:**
- Test both paths: Redis reachable (use `fakeredis.aioredis.FakeRedis`)
  and Redis unreachable (mock `ping()` to raise `RedisError`).
- Don't break existing health tests.

---

## Item 2 — CI/CD: GitHub Actions workflows

No `.github/` directory exists in the repo at all. Build it from scratch.

Create these three workflow files:

### `.github/workflows/backend-ci.yml`

Trigger: `push` and `pull_request` on `main`.

Steps:
1. Checkout
2. Set up Python 3.11
3. `pip install -r requirements.txt` (from `umbrella-core-CURRENT/`)
4. Start Redis: `sudo apt-get install -y redis-server && sudo redis-server --daemonize yes`
5. Start Postgres: use `services:` block with `postgres:15` image,
   env `POSTGRES_PASSWORD=test POSTGRES_DB=umbrella_test`
6. Set env vars: `DATABASE_URL=postgresql+asyncpg://postgres:test@localhost/umbrella_test`,
   `REDIS_URL=redis://localhost:6379/0`, `SECRET_KEY=ci-test-secret`,
   `ADMIN_KEY=ci-test-admin`, `PLUGIN_KEY=ci-test-plugin`
7. `cd umbrella-core-CURRENT && python -m pytest tests/ -x --tb=short`
8. On failure: upload pytest output as artifact

**Important:** This CI run will likely surface failures from the bugs in
`CRITICAL-FINDINGS-2026-08-17.md` (rate-limiter TTL, migration chain,
etc.) — those are being fixed in a parallel BUGFIX-01 dispatch. Don't
try to fix test failures here; just get CI running and reporting honestly.
Note in your handback which failures you see and whether they match the
known bugs.

### `.github/workflows/dashboard-ci.yml`

Trigger: `push` and `pull_request` on `main`.

Steps:
1. Checkout
2. Set up Node 20
3. `cd umbrella-dashboard-CURRENT && npm ci`
4. `npx tsc --noEmit`
5. `npm run lint`
6. `npm run build`

### `.github/workflows/plugin-ci.yml`

Trigger: `push` and `pull_request` on `main`.

Steps:
1. Checkout
2. Set up Java 17 (not 25 — GH Actions `setup-java` supports 17 LTS
   stably; the pom.xml targets 25 which is not an LTS and may not be
   available on the standard runner — check and use the highest LTS
   available, currently 21, and note in your handback if the pom's
   `maven.compiler.source=25` causes a build failure)
3. `cd minecraft-plugin && mvn test -B`

**Note on GrimAC dep:** `mvn test` in CI will fail if `GrimAPI:1.1.0.0`
isn't resolvable from `repo.grim.ac/snapshots`. Check whether that repo
is publicly accessible. If it is, great. If not, note it in your
handback as a known blocker — don't work around it with local installs
in CI (that's not reproducible).

---

## Testing standard

Item 1: tests run against `fakeredis`, both reachable and unreachable
paths covered. Don't need real Redis for the health check tests
specifically — fakeredis is the right tool here.

Item 2: the workflows themselves can't be run from a read-only clone.
Verify they are syntactically valid YAML and reference real action
versions (use `actions/checkout@v4`, `actions/setup-python@v5`,
`actions/setup-node@v4`, `actions/setup-java@v4`, `actions/upload-artifact@v4`).
Note in your handback that live CI run verification requires a push to
main, which the head chat will do after reviewing your handback.

---

## Deliverable for handback

Zip containing:
1. Modified/new files (full, not just diffs).
2. File manifest of everything changed/added.
3. Handback doc:
   - Status of each item (done / partial / blocked).
   - For item 1: test output showing both Redis paths passing.
   - For item 2: any known CI blockers (GrimAC dep, Java 25 vs LTS, etc.).
   - Anything noticed outside scope, flagged but not acted on.
4. Leak check: `find . -iname ".env" -o -iname "*.db" -o -iname "*.sqlite*"`

Session label for any scratch clone commits: `subchat-p12-s1a`.
