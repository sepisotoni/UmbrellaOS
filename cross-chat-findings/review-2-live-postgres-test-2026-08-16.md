# UmbrellaOS — live bug log against the original repo baseline

Date: 2026-08-16
Scope: original repo state only; no code fix attempted; no feature edits; only documentation written in this folder.
Baseline rule: we restored the working tree to the repo’s committed HEAD before testing, then ran the project against a live Postgres + Redis environment and reviewed the dashboard pages without modifying app code.

## 1. Test baseline and methodology

What I verified:
- `git restore --source=HEAD --staged --worktree` was used to remove local file edits before testing.
- Backend dependencies were installed in a fresh Python 3.12 venv, because the default system Python in this codespace is 3.14 and the pinned `pydantic-core` build chain is incompatible with it.
- The real Postgres service (`umbrella_postgres`) and Redis service (`umbrella_redis`) were used, not a fake in-memory fallback.
- The original `pytest -q` suite was run against the repo’s unmodified code.
- The dashboard was built with `npm run build`, `npx tsc --noEmit`, and `npm run lint` against the original frontend code.

Evidence:
- `git status --short` returned only the documentation file after restoration, with no backend code diff left in place.
- `python3.12 --version` reported `Python 3.12.3` and the fresh venv installed the project requirements cleanly.
- `docker ps --format 'table {{.Names}}\t{{.Status}}'` showed `umbrella_postgres` and `umbrella_redis` as healthy.
- `pytest -q` on the original backend returned: `347 failed, 489 passed, 8 errors in 516.96s`.
- `npm run build` on the original dashboard completed successfully and generated all app routes.

## 2. Bug #1 — fresh Postgres migrations fail on an empty database

Summary:
The migration chain does not create all required tables from empty state. The codebase can appear healthy when a manually created DB already has those tables, but it is not deployable from a clean Postgres instance.

How I triggered it:
- I created a truly fresh database and ran the migration chain with Alembic against it.
- I also checked the model definitions versus the migration files.

Real evidence:
- `alembic upgrade head` fails on a new database with missing-table errors related to `users`.
- The model-to-migration audit found these SQLAlchemy tables exist in the actual code but have no real migration creation path anywhere in the migration chain:
  - `users`
  - `sessions`
  - `discord_oauth_pending`
  - `plugin_commands`
  - `plugin_heartbeats`
- This is not a naming mismatch; the DB was genuinely empty before the run.

Impact:
- The project cannot bootstrap a fresh Postgres database from the repo’s original migration chain as-is.
- Any prior “all green” result likely relied on a pre-seeded database, undocumented manual schema creation, or a non-fresh environment.

Relevant architecture clue:
- `main.py` calls `await create_tables()` during app startup, which is a dev convenience path, not a replacement for a complete migration chain. That does not solve the issue for a real empty-production database.

## 3. Bug #2 — Redis-backed rate limiting is live and breaks the test suite when Redis is reachable

Summary:
The backend’s rate limit middleware is real and active. When Redis is reachable, requests start receiving HTTP 429s and the middleware records real security events against the live database, which means the tests are not isolated from the runtime environment.

How I triggered it:
- I ran the original backend test suite against the live Postgres + Redis stack.
- I checked the live security-event inserts while the test client was exercising routes.

Real evidence:
- Test output contained many failed assertions like `assert 429 == 200` and `assert 429 == 401`.
- The logs showed actual inserts into `security_events` using Postgres/asyncpg parameters, not SQLite:
  - `INSERT INTO security_events (id, event_type, source_ip, identifier, detail) VALUES ($1::VARCHAR, ...)`
- This matches the middleware path in `api/middleware/rate_limit.py` and the check in `services/rate_limit_service.py`.
- Repeated rate-limit violations produced real `rate_limit_violation` events.

Why this happened:
- `tests/conftest.py` creates an in-memory SQLite DB and overrides app DB dependencies, but it does not flush or isolate the Redis state used by the live limiter.
- The production `RateLimitMiddleware` is in path, and the app runs with a real Redis URL from `.env`.
- Once the Redis counter exceeds the default window threshold, every route is 429’d until the limiter’s state resets.

Impact:
- The current test environment is not hermetic when Redis is reachable.
- A prior “clean pass” result may have been running while Redis was unreachable, because the middleware deliberately fails open on Redis errors (`except RedisError` returns the request instead of blocking it), which would hide the issue completely.

## 4. Bug #3 — threat detection writes to a separate live DB session instead of the test DB

Summary:
The threat-detection service is designed to use its own async session and does not participate in the per-test DB override. This makes the production DB path interfere with tests and can trigger live DB writes while the app under test is meant to be isolated.

How I triggered it:
- I ran the original pytest suite and watched the logs as it hit the rate-limit path.

Real evidence:
- `services/threat_detection_service.py` explicitly opens `AsyncSessionLocal()` and records a `SecurityEvent` row from that session.
- The stack trace shows a live Postgres insert during a test run, including a `sqlalchemy.dialects.postgresql.asyncpg.InterfaceError` with `cannot perform operation: another operation is in progress`.
- The failure was not limited to one test; it cascaded across the suite as the real DB and real Redis state were being touched.

Impact:
- The same request being tested can trigger a DB write outside the in-memory test transaction.
- This explains the “event loop is closed” and cross-request interference signatures seen across the suite.

## 5. Bug #4 — the original dashboard compiles, but it is runtime-blocked by the backend’s live 429 issue

Summary:
The dashboard itself is not obviously broken at compile time; the route structure is present and builds cleanly. However, every protected route depends on the backend API being healthy, and under the live Postgres/Redis test environment the backend is returning real `429 Too Many Requests` responses that effectively break the dashboard experience.

Page-by-page review:
- `/login` — present, compiles, and should redirect to `/dashboard` when a session exists. No direct compile-time bug found.
- `/dashboard` — present and built; page content depends on widget data from the backend. In the live failing environment it receives rate-limited API responses and therefore cannot populate widgets reliably.
- `/settings` — present and built; it fetches plugin config through the backend and is blocked by the same API instability.
- `/marketplace` — present and built; catalog + install state are fetched from live backend capability calls and also fail under 429s.
- `/marketplace/[pluginId]` — present and built; plugin detail page is tied to plugin install metadata and is likewise backend-dependent.
- `/activity` — route exists and builds; the page does not have an independent data-layer bug in the code, but it cannot be validated in a stable runtime while the backend is rate-limiting.
- `/fleet` — same as above; route exists and builds, but depends on the backend being healthy.
- `/topology` — same as above; route exists and builds, but the live data path is backend-dependent.

Real evidence:
- `npm run build` in the original dashboard completed successfully and generated all listed routes.
- `npx tsc --noEmit` passed.
- `npm run lint` passed.
- The backend failures show the app layer, not the frontend build, is the true blocker: 429s from the API prevent data from reaching those pages.

## 6. Bug #5 — environment mismatch with Python 3.14 is a real project-level portability issue

Summary:
The repo pins dependencies that do not build cleanly on the default Python in this environment. This is not a code bug, but it is a real setup failure that can make the project look “broken” to a fresh session.

Real evidence:
- Default environment Python in this codespace is 3.14.
- The pinned `pydantic-core`/dependency set does not have a working wheel path for 3.14 in this environment and fails in the build path.
- The project was successfully installed only after switching to `python3.12`, which is the correct interpreter for this repo in this environment.

Impact:
- Fresh sessions may fail before they even reach the app logic.
- This should be documented in setup instructions or pinned with an explicit `.python-version`/README note.

## 7. Bug #6 — the repo’s original baseline is not cleanly test-isolated from external infrastructure

Summary:
The app is not self-contained in a test run. It reaches out to Redis and Postgres as part of its runtime path, and the test suite depends on those services being unreachable or perfectly isolated. That is operationally fragile and affects correctness.

Real evidence:
- Real Redis and Postgres were running and healthy.
- Requests reached the real rate-limiter and security-event path.
- A large number of tests that should have returned 200/201/401/403 instead returned 429 because the environment was not isolated.

Impact:
- Test results are environment-dependent rather than deterministic.
- The repo does not currently provide a consistent “original repo baseline” harness that ensures Redis is reset between tests or that the live rate limiter is bypassed for automated testing.

## 8. Consolidated conclusion

Status of the original repo baseline:
- The backend is not currently reliable against a fresh Postgres + live Redis environment.
- The migration chain is incomplete for a new DB.
- The rate-limiter, security-event path, and test isolation issues break the suite under real runtime conditions.
- The dashboard itself builds cleanly, but every protected route is effectively runtime-blocked by the live backend instability.
- No app code was edited during this pass; this is a documentation-only review against the original committed state.

This was a real validation pass, not a code-fix pass. The project should be treated as requiring a full environment and infrastructure isolation fix before the suite or the dashboard can be trusted end-to-end.

Session notes: original repo baseline, no code changes except this log file under the cross-chat-findings directory; 2026-08-16.
