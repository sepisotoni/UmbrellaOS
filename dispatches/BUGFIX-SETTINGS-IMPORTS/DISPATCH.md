# DISPATCH: Bugfix — SettingsView.tsx broken imports (build fails)

**Type:** Sub-chat (write access)
**Scope:** `umbrella-dashboard-CURRENT/src/components/settings/SettingsView.tsx` only
**Write PAT:** [WRITE_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip:** 36508e1

---

## Problem

`SettingsView.tsx` was written against the OLD Gemini dashboard and imports from paths that don't exist in the current Claude dashboard:
- `../../context/DashboardContext` — DOES NOT EXIST (current dashboard uses `../../context/AuthContext`)
- `../../types/dashboard` — DOES NOT EXIST
- `api` default export from `../../lib/api` — DOES NOT EXIST (current api.ts uses named exports)

This breaks the Vercel build with TypeScript errors.

## What DOES exist in the current dashboard

Read these files first (lazily):
- `umbrella-dashboard-CURRENT/src/context/AuthContext.tsx` — exports `useAuth()` with `{ token, user, login, logout }`
- `umbrella-dashboard-CURRENT/src/lib/api.ts` — named exports: `auth`, `dashboard`, `players`, `punishments`, `appeals`, `staff`, `anticheat`, `verification`, `alts`, `settings`, `aiConfig`, `feature_flags`, `audit`, `plugins`, `bridge`, `getBaseUrl()`
- `umbrella-dashboard-CURRENT/src/components/pages/SettingsPage.tsx` — the CURRENT settings page (this is the correct one)

## Task

The current `SettingsPage.tsx` already exists and works. The broken `SettingsView.tsx` is a relic from the old dashboard that the 16CE sub-chat accidentally added new sections to instead of `SettingsPage.tsx`.

**Do this:**
1. Read `umbrella-dashboard-CURRENT/src/components/pages/SettingsPage.tsx` to understand what's there
2. Read `umbrella-dashboard-CURRENT/src/components/settings/SettingsView.tsx` to extract ONLY the new sections added by 16CE:
   - AI Configuration section (per-task model config)
   - Player Experience section (greeter + chat responder)
3. Port those two sections into `SettingsPage.tsx` using the correct imports (`useAuth`, named api exports)
4. Delete `umbrella-dashboard-CURRENT/src/components/settings/SettingsView.tsx` entirely
5. Make sure `App.tsx` or wherever routing happens uses `SettingsPage` not `SettingsView`

Fix any other `implicit any` type errors in the new sections while you're at it.

## Commit

`dashboard: fix SettingsView broken imports — port AI config + player experience into SettingsPage`

Then push. No handback needed — just fix and push.
