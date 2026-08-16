# Bugs found — live functional test pass, 2026-08-16 (sub-chat)

Format: what's broken, how I triggered it, real evidence. Not deep
root-cause analysis — head chat to investigate further.

Context: dispatched to run live functional tests (Phase 9 security
middleware, dashboard visual/mobile/permission checks) that a prior
session in this project's history had flagged as untested. Fresh venv,
real pip install, real redis-server, real headless-Chrome screenshots —
not unit-test mocks.

## 1. Rate-limit exempt path is dead config
- `api/middleware/rate_limit.py` DEFAULT_EXEMPT_PATHS = {"/healthz"}
- Searched the whole app (`main.py`, `api/`) for a route matching
  `/healthz`: none exists. Confirmed live — `GET /healthz` returns 404,
  same as any undefined path.
- Effect: whatever this exemption was meant to protect (a
  monitoring/uptime check hitting the backend) has no real endpoint to
  hit, so the exemption is currently unreachable code, not a real
  behavior.

## 2. Dev-auth mint documented path is misleading
- `capabilities/dev_auth.py` registers `auth.dev.mint_test_session`.
  A naive `POST /api/dev-auth/mint` (what a prior session's transcript
  implied, and what the capability name might suggest as a shortcut)
  returns a real 404.
- Real working path, confirmed live: `POST
  /api/v1/capabilities/auth.dev.mint_test_session/invoke` with an
  `X-Admin-Key` header — returned a real token successfully once I used
  it. Not a functional bug, but a real discoverability gap worth a doc
  note.

## 3. Mobile viewport is not responsive — real layout bug
- How I got there: real headless-Chrome screenshot (playwright, 390x844
  mobile viewport) of `/fleet`, logged in as a real minted session.
- What's broken: the left sidebar nav doesn't collapse into a mobile
  menu — stays a fixed ~220px-wide column on a 390px-wide screen, eating
  over half the viewport. The top bar (`UmbrellaOS` / search / username
  / role badge) has no responsive wrapping either — username + role
  badge wrap onto three stacked lines and visually collide with the
  search box.
- Confirmed real (not a screenshot artifact) — same page/session renders
  correctly at desktop width (1400px).
- Scope note: only checked `/fleet`. Didn't check the other 5 routes for
  the same or separate mobile issues.

## 4. Orphaned pre-rewrite secrets found sitting live in a codespace filesystem
- Not a code bug — an operational/security finding from continuing this
  dispatch in an existing codespace (`sturdy-tribble-r49xx959q7wxhwg5`)
  rather than a fresh sandbox clone.
- That codespace's local `main` was still on an old commit
  (`8e0004c`) from before this project's history rewrite (D4's
  "Baseline" commit) — `git fetch` reported a **forced update** on
  `origin/main`, confirming real divergence, not just a stale branch
  pointer.
- After `git reset --hard origin/main`, two untracked `.env` files were
  still physically present on disk (not in git at all — the current repo
  has neither `discord-bot/` nor `files/umbrella-core/`):
  `discord-bot/.env` and `files/umbrella-core/.env`. Checked
  non-destructively (key names + value lengths only, never printed raw
  values): both had real-looking populated secrets — `DISCORD_BOT_TOKEN`
  (72 chars, identical in both files), `DISCORD_CLIENT_SECRET`,
  `OPENROUTER_API_KEY` (73 chars), `SECRET_KEY`, `ADMIN_KEY`.
- Per Sepiso Toni's direct instruction this session, fully wiped via
  `git clean -fdx` — codespace now matches `origin/main` exactly, no
  leftover files. **These credentials should be treated as compromised
  and rotated if they're still live anywhere** (same treatment this
  project's own principles doc already gives the earlier `UmbrellaOS.zip`
  `.env` finding).

## Confirmed NOT bugs (checked, then ruled out)
- Settings page showing "No installed plugins have dashboard-configurable
  settings yet." is correct/intentional — read the page source
  (`app/(dashboard)/settings/page.tsx`): this route is explicitly scoped
  to plugin Tier-2 config toggles only, not core system settings.
- Role-based permission gating: minted a real `member` role session (not
  `owner`) and hit `/fleet` for real — correctly shows "You don't have
  permission to view hosted server state," and the sidebar correctly
  hides nav items that role can't reach.

## What else got confirmed working (positive results, real live triggers)
- WAF blocks real path-traversal, XSS, and oversized-body requests
  (400s/413).
- Rate limiter genuinely returns 429 after ~120 req/min from one IP, with
  real `retry-after` headers.
- Real `traceparent` header present on responses — tracing is live.
- Threat detection: drove real WAF-block events past threshold, confirmed
  a real `security.threat_detected` event landed in the `events` table.
- CVE/dependency scanner: ran `pip-audit` for real against real PyPI
  advisory data — clean, no findings.
- All 6 dashboard routes (`/dashboard`, `/fleet`, `/activity`,
  `/marketplace`, `/settings`, `/topology`) render correctly at desktop
  width — real pixels via headless Chrome, first time this project has
  had actual screenshots rather than raw HTML.
- Seeded real multi-node/multi-server data via the ORM and
  re-screenshotted `/fleet` and `/topology` — status color-coding, memory
  formatting, empty-node messaging, and the SVG topology graph (including
  the previously-undiscovered "Capability dependencies" tab) all render
  correctly with real data.

Session: subchat-live-functional-test, 2026-08-16
