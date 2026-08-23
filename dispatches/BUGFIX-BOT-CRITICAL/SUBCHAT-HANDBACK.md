# SUBCHAT-HANDBACK — BUGFIX-BOT-CRITICAL

**Completed:** 2026-08-23
**Sub-chat tip at dispatch:** 81f78af
**Final tip:** 91a8fdc (after rebase over 3e05d56)

---

## Fixes Delivered

### Fix 1 — `get()` method added to `UmbrellaCoreClient` (BUG-1)
**File:** `umbrella-discord-CURRENT/bot/services/umbrella_core_client.py`
**Commit:** `2bb632a`

Added `async def get(self, path: str) -> dict[str, Any]` using the same
httpx session pattern as `invoke()` and `list_capabilities()`. Auth headers
from `_make_auth_headers()` (PBKDF2 MAC). Raises `UmbrellaCoreError` on
non-2xx with status_code and code attached. `verification_cog` and any
other cog needing to GET a settings/resource endpoint can now use this.

### Fix 2 — Settings GET endpoints accept PBKDF2 auth (BUG-2)
**File:** `umbrella-core-CURRENT/api/routers/settings.py`
**Commit:** `9f426d3`

`GET /api/v1/settings` and `GET /api/v1/settings/{key}` now use
`require_admin_hmac_or_session` (matching `bot_registration.py`) instead
of `require_owner`. Write endpoints (`POST`, `PATCH`) remain on
`require_owner` — stricter auth for mutations is unchanged.

The `unmasked` flag logic is preserved: bot/admin-key callers get real
values, dashboard session callers get sensitive values masked.

### Fix 3 — Ephemeral followups on server_restart and server_kill (SILENT-2)
**File:** `umbrella-discord-CURRENT/bot/cogs/hosting_cog.py`
**Commit:** `d439702` (rebased as `91a8fdc`)

Both success `followup.send` calls already had `ephemeral=True`.
Added `wait=True` to both to ensure py-cord waits for the Discord API
acknowledgement before returning — prevents silent drops on the
confirm-flow path (where the interaction response was already consumed
by `_confirm()` via `send_message`, making the followup the only visible
output). Added inline comment referencing SILENT-2.

---

## Notes

- **SILENT-2 state at dispatch:** Both `followup.send(ephemeral=True)` calls
  were already present at audit tip (`625f39b`) and dispatch tip (`81f78af`).
  The audit was likely written against an even earlier version. The `wait=True`
  addition is the meaningful hardening — it prevents the ephemeral followup
  from being silently dropped on the confirm-button interaction path.

- **Concurrent push conflict:** Fix 3 was rebased over `3e05d56` (head chat or
  another sub-chat pushed while this session was in flight). Rebase was clean.

- No migrations required. No new dependencies. No config changes.
