# SUBCHAT HANDBACK — Bugfix: Plugin key → operational_intelligence.view

**Status:** ✅ Complete — 1 commit pushed  
**Final tip:** `dad55d6`

---

## Root Cause

`POST /api/v1/ai/copilot` (and other AI endpoints) use `require_permission("operational_intelligence.view")` as their auth dependency. That dependency calls `require_admin_key_or_session` internally.

`require_admin_key_or_session` only accepted `X-Admin-Key` or a Bearer session token. The Minecraft plugin sends `X-Plugin-Key` — so every plugin request was hitting the 401 path and never reaching the permission layer at all.

## Fix

**File:** `umbrella-core-CURRENT/api/middleware/session.py`

Added `X-Plugin-Key` acceptance to `require_admin_key_or_session`:
- Imported `plugin_key_header` from `api.middleware.auth` (already defined there)
- Added `x_plugin_key` parameter with `Security(plugin_key_header)`
- Added check: if `x_plugin_key == settings.secret_key` → return the key as `str`

Returning a `str` is the existing convention for pre-authorised callers (admin key does the same). `require_permission` already has `if isinstance(auth, str): return auth` — so the plugin key now bypasses role/permission checks exactly like the admin key does, which is correct (plugin is a trusted first-party caller).

## Scope

Change is 3 lines net. No router changes, no DB migrations, no new models. Every other endpoint that uses `require_admin_key_or_session` (settings, discord routes, etc.) is unaffected in behaviour — plugin key was already accepted there via `require_plugin_key`; this just extends acceptance to the session-based dependency chain.
