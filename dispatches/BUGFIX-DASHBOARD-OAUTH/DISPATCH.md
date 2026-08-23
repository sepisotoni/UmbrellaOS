# DISPATCH: Dashboard Fixes — Discord OAuth + Flickering Banner

**Type:** Sub-chat (write access)
**Scope:** `umbrella-dashboard-CURRENT/` only
**Write PAT:** [WRITE_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip:** c3fe1e8

Read files lazily. Commit after every fix.

---

## Context

Two issues spotted on the live dashboard:
1. "Method Not Allowed" error when clicking "Continue with Discord" on the login page
2. Flickering at the bottom of the page — likely the disconnected banner re-rendering on every health poll

---

## Fix 1 — Discord OAuth "Method Not Allowed"

Read `umbrella-dashboard-CURRENT/src/components/auth/LoginView.tsx` and `umbrella-dashboard-CURRENT/src/lib/api.ts`.

The Discord OAuth button is hitting `POST /api/v1/auth/discord/authorize` — check exactly what the dashboard is sending and what the core expects.

Also check `umbrella-core-CURRENT/api/routers/auth.py` — read the authorize endpoint to see what method and body it expects.

Common causes:
- Dashboard sending GET instead of POST
- Dashboard sending POST with wrong content-type
- The authorize endpoint redirects and the dashboard doesn't follow it correctly

Fix whatever is wrong. The correct flow is:
1. `POST /api/v1/auth/discord/authorize` with body `{ redirect_uri: "..." }` → returns `{ authorize_url, state }`
2. Dashboard redirects user's browser to `authorize_url`
3. Discord redirects back to `redirect_uri` with `?code=...&state=...`
4. Dashboard calls `POST /api/v1/auth/discord/callback` with `{ code, state, redirect_uri }` → returns `{ token, user }`

If `VITE_UMBRELLA_CORE_URL` isn't set, the dashboard will try to hit `undefined/api/v1/...` — also check the `.env.example` and make sure the dashboard reads the env var correctly.

---

## Fix 2 — Flickering disconnected banner

Read `umbrella-dashboard-CURRENT/src/components/common/DisconnectedBanner.tsx` and wherever the health check polling happens (likely `DashboardContext.tsx`).

The flicker is caused by the banner unmounting and remounting on every poll cycle. Fix by:
- Using `useState` to track the connected/disconnected state and only updating when it actually changes (don't set state if the value is the same)
- Or wrap the banner in a CSS transition so it fades in/out instead of snapping

Don't change the poll interval — just make the state update stable.

---

## Commit Instructions

- `dashboard: fix Discord OAuth Method Not Allowed error`
- `dashboard: fix disconnected banner flickering`

When done write `dispatches/BUGFIX-DASHBOARD-OAUTH/SUBCHAT-HANDBACK.md` and push.
