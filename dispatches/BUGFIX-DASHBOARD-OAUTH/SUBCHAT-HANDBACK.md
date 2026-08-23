# SUBCHAT HANDBACK — BUGFIX-DASHBOARD-OAUTH

**Status:** DONE — 2 fixes, 2 commits

---

## Fix 1 — Discord OAuth "Method Not Allowed"

**Root cause:** `getDiscordAuthUrl()` in `api.ts` was sending a `GET` request with `redirect_uri` as a query param. The backend at `POST /api/v1/auth/discord/authorize` expects a `POST` with a JSON body `{ redirect_uri }`.

**File changed:** `umbrella-dashboard-CURRENT/src/lib/api.ts`

**What changed:** Rewrote `getDiscordAuthUrl` to use `POST` with `JSON.stringify({ redirect_uri })`. The `discordAuthorize` wrapper was left untouched since it delegates correctly.

**Commit:** `dashboard: fix Discord OAuth Method Not Allowed error`

---

## Fix 2 — Flickering disconnected banner

**Root cause:** `checkHealth()` in `DashboardContext.tsx` called `setIsDisconnected(false)` or `setIsDisconnected(true)` unconditionally on every 30s poll — even when the value hadn't changed. React re-rendered on every state set, causing the banner to unmount and remount every poll cycle.

**File changed:** `umbrella-dashboard-CURRENT/src/context/DashboardContext.tsx`

**What changed:** Switched both `setIsDisconnected` calls to functional updater form that only transitions the value when it actually differs from the current state. No change to poll interval.

**Commit:** `dashboard: fix disconnected banner flickering`

---

## Tip after handback
Check `git log --oneline -4` — should show both commits on top of `81f78af`.
