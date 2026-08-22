# SUBCHAT HANDBACK: Phase 16A — Discord Bot Deploy

**Status:** ✅ Complete — all tasks done, server NOT started (awaiting .env fill)
**Commit:** 88cc28c

---

## Tasks Completed

### Task 1 — Archive extraction
Extracted `umbrella-discord-PHASE8-COMPLETE.zip` from the `archive` branch.

**Structure found:**
```
main.py                          ← entry point
requirements.txt
pytest.ini
bot/
  __init__.py
  bot.py
  config.py
  cogs/   (11 cogs)
  services/
    marketplace_sync.py
    umbrella_core_client.py
tests/   (15 test files)
```

### Task 2 — Bot file updates

**`bot/config.py`** — added:
- `discord_guild_id: int | None = None`
- `discord_verified_role_id: int = 0`
- `umbrella_core_url` default set to `https://umbrellaos-core.onrender.com`

**`bot/cogs/verification_cog.py`** — added `_assign_verified_role()` method:
- Reads `settings.discord_verified_role_id` (0 = skip)
- Iterates all shared guilds, assigns role after successful verification
- Best-effort only — missing role or Manage Roles permission logged and skipped, never raised

**`requirements.txt`** — relaxed pins to minimums per dispatch + added `aiohttp>=3.9.0`:
```
discord.py>=2.3.0
aiohttp>=3.9.0
httpx>=0.28.0
pydantic-settings>=2.6.0
python-dotenv>=1.0.0
```

**`bot.py` (new, root level)** — HeavenCloud runs `bot.py` by default; created a shim that imports and calls `main.py`'s `main()` so the deployment works without any panel config change:
```python
from main import main
if __name__ == "__main__": main()
```

### Task 3 — Repo commit
Committed as `umbrella-discord-CURRENT/` to main:
- Commit: `88cc28c`
- Message: `feat: add umbrella-discord-CURRENT — Discord bot Phase 8 + verified role assignment (P16A Task 3)`

### Task 4 — HeavenCloud upload
All files uploaded via Pterodactyl file API (all returned HTTP 204):

| Path | Status |
|------|--------|
| `/bot.py` | ✅ |
| `/main.py` | ✅ |
| `/requirements.txt` | ✅ |
| `/bot/__init__.py` | ✅ |
| `/bot/bot.py` | ✅ |
| `/bot/config.py` | ✅ |
| `/bot/cogs/` (11 files) | ✅ |
| `/bot/services/` (3 files) | ✅ |

### Task 5 — .env created on server
`.env` uploaded at `/.env` with:
```
DISCORD_BOT_TOKEN=          ← NEEDS FILLING
DISCORD_GUILD_ID=           ← NEEDS FILLING
UMBRELLA_CORE_URL=https://umbrellaos-core.onrender.com
UMBRELLA_CORE_API_KEY=8c186becf081a4cd4a499ed3099d564f7b81a5d6fcee769c14c0f9c424467731
DISCORD_VERIFIED_ROLE_ID=   ← NEEDS FILLING (or leave blank to skip role assignment)
STAFF_ALERT_CHANNEL_ID=     ← OPTIONAL — channel for staff escalation notifications
```

---

## What Sepiso needs to do before starting the bot

1. **Open the HeavenCloud file manager** → edit `/.env`
2. **Fill in:**
   - `DISCORD_BOT_TOKEN` — the bot's token from Discord Developer Portal
   - `DISCORD_GUILD_ID` — your Discord server's ID (right-click server → Copy Server ID)
   - `DISCORD_VERIFIED_ROLE_ID` — ID of the "Verified" role to assign on Minecraft verification (right-click role → Copy Role ID). Leave blank to skip role assignment.
   - `STAFF_ALERT_CHANNEL_ID` — (optional) channel ID where staff escalation alerts post
3. **Start the server** from the HeavenCloud panel

The bot will auto-install `requirements.txt` on startup (HeavenCloud behaviour per dispatch).

---

## Issues found in bot code

- **No `DISCORD_GUILD_ID` used anywhere in cogs** — the config field was added but the original cogs don't use it (they discover guilds dynamically via `self.bot.guilds`). This is fine for a single-server deployment but means there's no guild-scoping if the bot is ever added to multiple servers. Not a blocker.
- **`notifications_cog.py`** — has a `STAFF_ALERT_CHANNEL_ID` optional field (already in original config). Added to `.env` template as optional.
- **Tests** — the 15 test files are present in `umbrella-discord-CURRENT/tests/` in the repo but were NOT uploaded to HeavenCloud (not needed for runtime). If you want to run them locally: `cd umbrella-discord-CURRENT && pip install -r requirements.txt && pytest`.

---

## Server state
**NOT started.** `.env` has blank token fields — starting now would crash immediately on `discord_bot_token` validation. Fill `.env` first.
