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
