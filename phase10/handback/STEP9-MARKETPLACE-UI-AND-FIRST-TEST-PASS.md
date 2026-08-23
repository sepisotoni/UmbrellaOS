# Step 9 — Marketplace listing/install UI + first real manual/browser test pass

Scoped dispatch, both tasks from `SUBCHAT-HANDOFF-PHASE10-COMPLETION.md`.
Session: `subchat-phase10-completion`. Everything below was independently
re-verified before being written up — nothing here is copied from the
handoff doc's own claims without checking them first (rule 2.1).

## Pre-flight verification — done before writing any code

Fresh venv, offline install from `wheels/`, real `pytest -q` run:
**838/838 passed**, `pip check` clean, no stray `.env`/`.db` written
during the run. Fresh `npm install`: **0 vulnerabilities**, `npx tsc
--noEmit` clean, `npm run lint` clean, `npm run build` clean. All
matching what the handoff doc claimed, confirmed independently rather
than trusted — same discipline `STEP6-VERIFICATION-ADDENDUM.md` and
`STEP7-VERIFICATION-ADDENDUM.md` already established for this project.

## Task A — Marketplace listing/install UI: done, independently verified

Replaces `app/(dashboard)/marketplace/page.tsx`'s step-2 placeholder
(flagged as still-open in `STEP8-TIER2-CONFIG-TOGGLES-BACKEND.md`'s
"what's left" section, item 2).

- `lib/marketplace-listings.ts` — server-only fetch (`marketplace.listing.list`,
  `marketplace.install.list`, `marketplace.listing.versions`), same
  catch-and-degrade-to-empty-array posture as every other list fetch in
  this app (`fetchPluginNavEntries`, `fetchConfigurablePlugins`). Writes
  (`installPlugin`/`uninstallPlugin`) left to throw, matching
  `lib/plugin-config.ts`'s convention — the API route is the layer that
  needs to distinguish failure modes.
- `app/(dashboard)/marketplace/page.tsx` — catalog, cross-referenced
  against installed versions, permission-gated on
  `marketplace.install.manage`. `marketplace.listing.publish` (a plugin
  author uploading a new zip) confirmed out of scope against the handoff
  doc before starting — that's a separate, larger upload/validation UI.
- `app/api/marketplace-install/route.ts` — same-origin write route
  (POST install, DELETE uninstall), following
  `app/api/dashboard-layout/route.ts`'s exact pattern: bearer token
  stays server-side, backend error shape (403/404/409) mapped to
  something the client leaf can branch on.
- `components/widgets/marketplace-install-button.tsx` — the one client
  leaf, following `dashboard-customizer.tsx`'s scoping convention. Real
  pending state (install/uninstall are genuinely not instant —
  `marketplace.install.install` does manifest validation + sandbox setup
  server-side), not an optimistic flip. Distinct
  forbidden/conflict/not-found/network error states.

**Verified for real, not just self-reported:** `npx tsc --noEmit`,
`npm run lint`, `npm run build`, `npm audit` all clean after the build.
Then actually clicked through it in a real headless browser (see Task B)
against a real published plugin — Install → "Installed v1.0.0" +
Uninstall button appears (via `router.refresh()`) → Uninstall (confirm
dialog) → reverts to Install. No console errors from this code; the one
console 404 seen on every route is a pre-existing missing
`favicon.ico`, unrelated to this work (checked: no favicon file anywhere
in `app/`) — cosmetic, out of scope, not fixed here.

## Task B — First real manual/browser test pass: done

**Nobody has clicked through this dashboard in a browser at any point in
Phase 10** (see `STEP8`'s "what's left" item 5) — every prior step's
verification was static (tests, build, lint, audit). This is that pass.

### The auth-for-testing gap: `auth.dev.mint_test_session`

`capabilities/dev_auth.py` — new capability, hard no-op (`404`, not
`403` — see its module docstring for why the distinction matters) unless
`settings.debug` is explicitly `True`. Mirrors the `X-Admin-Key`
bypass's own gating conventions (`api/middleware/session.py`), same
seriousness, not a free pass. Mints a real `Session` row (same shape
`discord_callback` produces) for a given role, plus optional
`extra_permissions` via `User.extra_permissions` — the mechanism that
makes "a role with `marketplace.install.view` but not `.manage`"
mintable, since no `DEFAULT_ROLES` entry has exactly that combination.
Re-invoking with the same `label` updates the existing synthetic dev
user in place rather than accumulating duplicates across test runs.

`tests/test_dev_auth.py` — 6 tests. The one that matters most: minting
is unreachable (`404`) when `debug=False`. Full suite: **844/844**
(838 + 6 new), re-run after every change in this session.

### A real gap in the handoff doc's own claim, found before trusting it

The doc pointed at `database_url_sync`'s "sqlite fallback" in
`config/settings.py` as the way to stand up a test backend. **Checked —
it doesn't exist.** Worse: running the actual alembic chain against
sqlite (`alembic upgrade head`) hits a hard, structural wall at
migration 005 — `op.create_foreign_key`'s `ALTER TABLE ADD CONSTRAINT`
isn't supported by SQLite without a full batch-mode rewrite. Making the
whole 28-file migration chain sqlite-compatible is real, separate work,
well outside this dispatch's two tasks — flagged here rather than
silently expanded into.

**What worked instead:** `database/engine.py::create_tables()`, already
wired into `main.py`'s startup lifespan and explicitly commented "safe
in dev; in prod, use Alembic migrations instead." Confirmed it creates
every table cleanly against sqlite (no Postgres-specific column types
anywhere in the ORM models) and that startup already seeds default
settings/roles afterward. Standing up a sqlite-backed instance for this
test pass meant running the app normally, not `alembic upgrade head` —
a deviation from the dispatch's literal instruction, stated here rather
than silently substituted.

### Three real migration bugs found and fixed along the way

While attempting the (ultimately abandoned, per above) sqlite alembic
run, found these — **all three are real bugs against Postgres too**,
not sqlite artifacts; they'd never actually been triggered because
nobody had run these migrations against a fresh database before:

- `alembic/versions/003_phase7_discord_bridge.py` — a raw-SQL
  `INSERT INTO settings` never supplied `id`, and `settings.id`
  (`models/setting.py`) has only a Python-side ORM default, no
  DB-level `server_default` (confirmed against its `op.create_table` in
  `001_initial.py`). Fixed with explicit literal UUIDs, generated once
  at migration-write time.
- `alembic/versions/004_phase8_verification.py`,
  `alembic/versions/005_phase9_alt_detection.py` — both declared a
  column with `index=True` *and* a redundant explicit
  `op.create_index` for the identically-named index — a duplicate-index
  error on any database. Removed the redundant explicit calls.
- Scanned every other migration for the same `index=True` +
  duplicate-`create_index` pattern — these two were the only instances.

### The actual test pass

Headless Chrome via `playwright-core` (installed via `npm install
--no-save`, not added to `package.json` — this is throwaway test
tooling, not a project dependency), driving the sandbox's pre-cached
"Chrome for Testing" binary directly, since `npx playwright install
chromium`'s CDN download is blocked by this environment's egress
allowlist. Both servers (backend on sqlite with `DEBUG=true`, frontend
production build via `npm run start`) brought up for real, in-process,
for the duration of the pass.

Covered:
- All 4 real dashboard routes (`/dashboard`, `/marketplace`,
  `/settings`, `/topology` — confirmed against `lib/nav-config.ts` and
  the actual `app/(dashboard)/` directory, not guessed) across 3
  permission levels: `owner` (full access), `member` +
  `marketplace.install.view` only (no `.manage`), `helper` with no
  marketplace permissions at all. All 12 combinations: `200`, no
  console errors beyond the pre-existing favicon 404, no error
  boundaries.
- Anonymous access: `/`, `/dashboard`, `/marketplace` all correctly
  redirect to `/login?next=<route>` with no session cookie.
- Install-route permission enforcement via direct HTTP: a
  zero-marketplace-permission session gets `403` from
  `POST /api/marketplace-install`; a real install attempt against a
  nonexistent plugin correctly surfaces `404`.
- The actual click-through described in Task A above: publish a real
  minimal valid plugin package, Install it as the UI, watch state
  update, Uninstall it, watch state revert. This is the one part of
  this pass that exercises Task A specifically, beyond its own static
  checks.

Test-only artifacts (`smoke-test.mjs`, `smoke-test-interact.mjs`, the
throwaway plugin zip, `playwright-core` in `node_modules`) were **not**
committed — they're sandbox-specific (hardcoded Chrome path, a
dependency not declared in `package.json`) and wouldn't reproduce in a
different environment. This doc is the record of what they found.

## What's left for the whole project after this

1. **The leak-investigation report** (`UNVERIFIED-leak-investigation/`,
   referenced in `MASTER-PROJECT-STATUS-AND-HANDOFF.md` §9) — not part
   of this scoped package, so not independently checkable from here.
   Still worth a direct check with Sepiso Toni on whether those
   `SECRET_KEY`/`ADMIN_KEY` values need rotating, separate from
   anything in this dispatch.
2. **`marketplace.listing.publish`** (a plugin author uploading a new
   zip from the dashboard) — confirmed out of scope for Task A, still
   not built. The only way to add a listing right now is a direct
   capability call (as this test pass did), not a dashboard UI.
3. **SQLite is not a real option for this project's migration chain**
   as currently written — worth a decision (rule 2.2) on whether that
   matters enough to invest in a batch-mode rewrite, given Postgres is
   the actual production target and `create_tables()` already covers
   the dev/test case.
4. **Missing `favicon.ico`** — cosmetic, seen on every route, not
   fixed here (out of scope for either task).
5. **Minecraft plugin** — separate track, unchanged by this session.
6. **Housekeeping, low priority, unchanged from `STEP8`:**
   `anticheat_service.py` dead code + zero coverage; `middleware.ts` →
   `proxy` naming deprecation warning.
