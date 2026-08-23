# BOT-AUDIT.md — umbrella-discord Discord Bot Audit

**Repo tip audited:** `625f39b`
**Live bot state:** Offline (HeavenCloud `671e0e33`, 0 MB)

## Critical Bugs

**BUG-1 — `verification_cog.py:112` — `AttributeError: 'UmbrellaCoreClient' has no attribute 'get'`**
Severity: High. Template loading silently fails on every call. Dashboard-configured verification messages never reach users. Falls back to hardcoded defaults forever.

**BUG-2 — `GET /api/v1/settings/{key}` rejects PBKDF2 auth**
Severity: High (blocks BUG-1's fix). Settings router uses `require_admin_key_or_session` which only accepts raw `X-Admin-Key`, not PBKDF2 MACs. Even after adding `.get()` to the client, a 401 follows.
Fix: add `require_admin_hmac_or_session` as accepted auth on the settings router, OR expose a bot-facing settings capability via the capability registry.

## Silent Failures

**SILENT-1** — No `/verify` slash command. Users must know to DM the bot a 6-digit code. No discovery path from within Discord.

**SILENT-2** — `server_restart` and `server_kill` followup messages are not ephemeral — action confirmations go public. All other server commands use `ephemeral=True`.

**SILENT-3** — If `moderation_report_cog` `create` succeeds but `analyze` fails, the report ID is lost and user gets a generic error.

## What's Working

- 12 cogs loaded, 12 implemented — no stubs, no fake data
- 21 slash commands, all real implementations
- PBKDF2 auth bot→core: correct (matches core's verifier exactly)
- PBKDF2 auth core→bot (webhook server): correct
- Webhook server registers on startup, verifies MACs on inbound events
- Tree sync: guild-scoped when `DISCORD_GUILD_ID` set (instant registration)
- Verification flow: DM listener, code matching, confirm, nickname sync, role assignment all correct

## Port Note

Dispatch said port 3607 for webhook server. Actual default in codebase is 8080 (configurable via `BOT_CALLBACK_PORT`). The `.env` on HeavenCloud was set to 3607 but the code defaults to 8080 — need to confirm `BOT_CALLBACK_PORT=3607` is actually being read.

## Fixes Needed (priority order)

1. Add `get(path)` method to `UmbrellaCoreClient`
2. Fix settings router to accept PBKDF2 auth (or add bot-facing settings capability)
3. Add `ephemeral=True` to `server_restart` and `server_kill` followups
4. Restart bot on HeavenCloud (currently offline)
