# DISPATCH: Discord Bot Critical Bug Fixes (BUG-1 + BUG-2)

**Type:** Sub-chat (write access)
**Scope:** `umbrella-discord-CURRENT/` and `umbrella-core-CURRENT/` only
**Write PAT:** [WRITE_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip:** c3fe1e8

Read files lazily. Commit after every fix. Push after each commit.

---

## Context

Two critical bugs identified in the bot audit (`dispatches/AUDIT-DISCORD-BOT/BOT-AUDIT.md`). Read it first.

---

## Fix 1 — Add `get(path)` to `UmbrellaCoreClient`

**File:** `umbrella-discord-CURRENT/bot/services/umbrella_core_client.py`

Read the file first. The client has `invoke()` and `list_capabilities()` but no `get()` method.

Add a `get(path: str) -> dict` async method that:
- Makes a GET request to `self._base_url + path`
- Sends the PBKDF2 auth headers from `_make_auth_headers()`
- Returns the parsed JSON response
- Raises an exception on non-2xx responses with the status code and body

Pattern to follow — look at how `invoke()` makes its HTTP request and use the same session/headers pattern.

---

## Fix 2 — Settings router accepts PBKDF2 auth

**File:** `umbrella-core-CURRENT/api/routers/settings.py`

Read the file first. The settings router currently uses `require_owner` or `require_admin_key_or_session` which rejects PBKDF2 MAC headers. The bot needs to read settings via `GET /api/v1/settings/{key}`.

Update the settings GET endpoint(s) to also accept `require_admin_hmac_or_session` — look at how `POST /api/v1/bot/register` uses it in `api/routers/bot_registration.py` and apply the same pattern to the settings read endpoint.

Keep write endpoints (POST/PUT) requiring the stricter auth — only the GET needs to accept the bot's PBKDF2 headers.

---

## Fix 3 — Ephemeral followups on server_restart and server_kill

**File:** `umbrella-discord-CURRENT/bot/cogs/hosting_cog.py`

Find `server_restart` and `server_kill` command handlers. Add `ephemeral=True` to their `interaction.followup.send()` calls so action confirmations don't go public. Match the pattern of other server commands that already use `ephemeral=True`.

---

## Commit Instructions

- `bot: add get() method to UmbrellaCoreClient (BUG-1)`
- `core: settings GET accepts PBKDF2 auth from bot (BUG-2)`
- `bot: ephemeral followups on server_restart and server_kill (SILENT-2)`

When done write `dispatches/BUGFIX-BOT-CRITICAL/SUBCHAT-HANDBACK.md` and push.
