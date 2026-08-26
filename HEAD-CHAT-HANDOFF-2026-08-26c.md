# HEAD CHAT HANDOFF — 2026-08-26c

**Repo:** https://github.com/sepisotoni/UmbrellaOS  
**Tip:** 8dcdcba

---

## Stack
- **umbrella-core-CURRENT** — FastAPI on Render (`srv-da3k11f10e5c73eka6o0`)
- **umbrella-dashboard-CURRENT** — React/Vite/TS on Vercel (`umbrella-os`, team `team_jxYs3eCsymnBsVpR7sBO1ueu`)
- **umbrella-discord-CURRENT** — discord.py bot on HeavenCloud (server `671e0e33`)
- **minecraft-plugin** — Java Paper plugin, BisectHosting
- **DB** — Supabase (`isofkwkivftnssorqzkd`), Alembic heads: `036_bot_command_manifest`, `030_appeal_close_fields`

---

## Open Items

### 🔴 Bot offline — HeavenCloud node outage
"Free Node - Texas" daemon still 504. When it recovers, run from codespace (`account: secondary`):

```bash
cd /workspaces && git clone https://<WRITE_PAT>@github.com/sepisotoni/UmbrellaOS.git 2>/dev/null || (cd UmbrellaOS && git pull)
cd /workspaces/UmbrellaOS

for FILE in \
  "umbrella-discord-CURRENT/bot/cogs/ask_cog.py:/bot/cogs/ask_cog.py" \
  "umbrella-discord-CURRENT/bot/cogs/webhook_cog.py:/bot/cogs/webhook_cog.py" \
  "umbrella-discord-CURRENT/bot/cogs/notifications_cog.py:/bot/cogs/notifications_cog.py" \
  "umbrella-discord-CURRENT/bot/utils/__init__.py:/bot/utils/__init__.py" \
  "umbrella-discord-CURRENT/bot/utils/checks.py:/bot/utils/checks.py" \
  "umbrella-discord-CURRENT/bot/bot.py:/bot/bot.py" \
  "umbrella-discord-CURRENT/bot/config.py:/bot/config.py"
do
  SRC="${FILE%%:*}"; DEST="${FILE##*:}"
  ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$DEST'))")
  CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "https://control.heavencloud.in/api/client/servers/671e0e33/files/write?file=$ENCODED" \
    -H 'Authorization: Bearer <HEAVENCLOUD_API_KEY>' \
    -H 'Content-Type: application/json' \
    -d "{\"content\": $(python3 -c "import json; print(json.dumps(open('$SRC').read()))")}")
  echo "$DEST → $CODE"
done

# Slim .env (3 vars only)
curl -s -o /dev/null -w ".env → %{http_code}\n" -X POST \
  'https://control.heavencloud.in/api/client/servers/671e0e33/files/write?file=%2F.env' \
  -H 'Authorization: Bearer <HEAVENCLOUD_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{"content":"DISCORD_BOT_TOKEN=<BOT_TOKEN>\nUMBRELLA_CORE_URL=https://umbrellaos-core.onrender.com\nUMBRELLA_CORE_API_KEY=<ADMIN_KEY>\n"}'

curl -s -o /dev/null -w "restart → %{http_code}\n" -X POST \
  'https://control.heavencloud.in/api/client/servers/671e0e33/power' \
  -H 'Authorization: Bearer <HEAVENCLOUD_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{"signal":"restart"}'
```
All uploads → 204, restart → 204. Bot will then push its command manifest automatically on startup.

### 🟡 Plugin audit fixes pending
Full audit doc (`PLUGIN-AUDIT-2026-08-26.md`) identified 19 issues across 8 batches. Prompt written and ready to dispatch. Key issues: Paper 1.20.4→1.21.4 API bump, AsyncChatEvent migration, JSON escaping in GrimBridge/ConsoleStreamManager, delta tracking for console push, orphaned BukkitTask on disable, 4 untested classes.

### 🟢 RLS on Supabase
All 65 tables have RLS disabled. Not urgent (core is the only DB client) but should be enabled before going public. Enabling without policies first locks everything out — needs careful policy writing per table.

---

## What Landed This Session

| Commit | What |
|---|---|
| `622699e` | Core: bot command manifest model + migration 036 + GET/POST /api/v1/bot/commands |
| `adb6837` | Bot: push slash command manifest to core on startup via setup_hook |
| `7ea9a49` | Dashboard: Discord Hub fully real — all 4 stat cards, guild identity, role table, slash commands from manifest |
| `8dcdcba` | Bot: notifications_cog + webhook_cog use self.bot.remote.* for DB settings |

---

## Full Feature Status

### Dashboard — all tabs on real data ✅

| Tab | Status |
|---|---|
| Overview | ✅ |
| Fleet | ✅ |
| Players | ✅ |
| Moderation | ✅ |
| Appeals | ✅ |
| AI Tasks | ✅ |
| Staff | ✅ Roles from backend, permission preview |
| Feature Flags | ✅ |
| Settings | ✅ Categorised sidebar, AI task models, plugin tabs |
| Knowledge Base | ✅ Two-panel, CRUD, pending review |
| Discord Hub | ✅ All real data — bot status, guild ID, role sync, slash commands from manifest |
| Console | ✅ WS + plugin poll fallback |
| Profile modal | ✅ RBAC perms, sign out, Discord avatar |
| Alt Detection | ✅ |
| Verification | ✅ |
| Audit | ✅ |

### Bot
| Feature | Status |
|---|---|
| All cogs | ✅ |
| Role permission system | ✅ |
| RemoteConfig (DB-backed settings) | ✅ All cogs use self.bot.remote.* |
| Command manifest push | ✅ Fires on startup |
| File upload to HeavenCloud | 🔴 Blocked — node outage |

### Core
| Feature | Status |
|---|---|
| All CRUD endpoints | ✅ |
| Knowledge base | ✅ |
| Bot registration + command manifest | ✅ |
| Plugin console push/pull | ✅ |
| Settings (all categories) | ✅ |

### Plugin
| Feature | Status |
|---|---|
| Core code | ✅ Deployed to BisectHosting |
| Audit fixes | ⏳ Prompt ready, not yet applied |

---

## Architecture Notes
- **Bot .env:** 3 vars only — `DISCORD_BOT_TOKEN`, `UMBRELLA_CORE_URL`, `UMBRELLA_CORE_API_KEY`. Everything else from DB via `self.bot.remote.*`.
- **Command manifest:** Bot pushes `POST /api/v1/bot/commands` on startup. Dashboard reads `GET /api/v1/bot/commands`. Falls back to static list if bot hasn't pushed yet.
- **HeavenCloud API calls:** Must come from codespace (`account: secondary`), not sandbox.
- **Permissions:** Fresh from DB per request. No re-login needed after role changes.
- **Alembic heads:** `036_bot_command_manifest` (main), `030_appeal_close_fields` (side branch — valid).
