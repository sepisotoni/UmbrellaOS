# SUBCHAT HANDBACK: Phase 16A — Discord Bot Deploy

**Status:** ✅ Complete — bot online and authenticated
**Final commit:** 5ba7f62

---

## Bot Status

```
INFO:bot.bot:Logged in as Moon-Bot#4491 (id=1515725320865710110)
INFO:httpx: POST .../capabilities/moderation_intelligence.escalation.list/invoke "HTTP/1.1 200 OK"
INFO:httpx: POST .../capabilities/marketplace.install.discord_commands/invoke "HTTP/1.1 200 OK"
INFO:httpx: GET  .../capabilities "HTTP/1.1 200 OK"
```

All 11 cogs loaded, slash commands synced globally, umbrella-core calls returning 200. Bot is live.

---

## All commits (P16A)

| Commit | Description |
|--------|-------------|
| `88cc28c` | feat: add umbrella-discord-CURRENT — Discord bot Phase 8 + verified role assignment |
| `94ca55e` | docs: P16A handback (initial) |
| `ac4f763` | fix: trim server_delete slash command description to <100 chars (Discord limit) |
| `6c039a8` | (intermediate) |
| `5ba7f62` | fix: send X-Admin-Key not X-Api-Key in umbrella_core_client (admin key auth path) |

---

## Issues encountered and fixed

### 1. `server_delete` slash command description too long (102 chars, Discord limit 100)
- Crashed on first boot during `tree.sync()`
- Fixed by trimming description to 87 chars

### 2. `X-Api-Key` vs `X-Admin-Key` header mismatch (401 Unauthorized on all core calls)
- Bot's `umbrella_core_client.py` sent the admin key as `X-Api-Key`
- umbrella-core's `api_key_auth.py` only accepts `X-Api-Key` for database-stored API keys; the admin key must go in `X-Admin-Key`
- Fixed: changed both `invoke()` and `list_capabilities()` to send `X-Admin-Key`

### 3. Entry point mismatch
- HeavenCloud runs `bot.py` by default; the archive had `main.py` as entry point
- Fixed: added `bot.py` shim at root that delegates to `main.py`

---

## Files on HeavenCloud (`671e0e33`)

```
/.env                          ← filled (token, guild, role, channel)
/bot.py                        ← HeavenCloud entry point shim
/main.py
/requirements.txt
/bot/__init__.py
/bot/bot.py
/bot/config.py
/bot/cogs/  (11 cogs)
/bot/services/umbrella_core_client.py
/bot/services/marketplace_sync.py
/bot/services/__init__.py
```

---

## Notes for head chat

- Bot identity: **Moon-Bot#4491** (`1515725320865710110`)
- No further action needed — bot is running and healthy
- `STAFF_ALERT_CHANNEL_ID` is set so escalation notifications will post to the configured channel
- Diagnostic note: future sub-chats should clone repo into `/workspaces` or `/tmp` fresh rather than relying on stale codespace working tree

---

## Ideas for Phase 16B (discussed with sub-chat, needs head chat decision)

### 1. PBKDF2 auth (replace plaintext admin key on the wire)

Currently the bot sends the raw admin key as `X-Admin-Key`. Proposed: replace with PBKDF2-HMAC-SHA256 derived key — same KDF as WPA2. Both sides know the shared secret; bot derives `PBKDF2(secret, salt, iterations)` and sends the result, core verifies by deriving the same value. Raw key never travels over the wire. Replay protection via timestamp in the salt or a separate nonce header.

Scope: change in `umbrella_core_client.py` (bot side) and `api/middleware/auth.py` / `api/middleware/api_key_auth.py` (core side).

### 2. Bidirectional core ↔ bot communication (replace polling with push)

Currently the bot polls core every few minutes for staff escalations. Proposed:

**Bot registration:** on startup the bot POSTs its own callback URL to a new core endpoint (e.g. `POST /api/v1/bot/register`). Core stores the URL. If the stored URL already matches, do nothing; if it changed (new HeavenCloud IP/port), overwrite it.

**Core push:** when events fire (staff escalations, punishments, player flags, verifications, etc.) core POSTs to the stored bot callback URL instead of waiting for a poll.

**Bot HTTP server:** bot gets a small aiohttp listener (aiohttp already in deps) on a configurable port (e.g. 8080, set via `BOT_CALLBACK_PORT` env var). HeavenCloud would need that port opened/forwarded.

**What events to push:** TBD — at minimum staff escalations (replacing the current poll), potentially punishments issued, anticheat flags, verification completions.

Both ideas can be scoped independently. Needs head chat decision on priority and scope before implementation.
