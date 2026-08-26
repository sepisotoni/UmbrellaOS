# HEAD CHAT HANDOFF — 2026-08-26b

**Repo:** https://github.com/sepisotoni/UmbrellaOS  
**Tip:** c21d098

---

## Open Items

### 🔴 Bot offline — HeavenCloud node outage
"Free Node - Texas" daemon still returning 504. When node recovers, run from codespace (`account: secondary`):

```bash
cd /workspaces && git clone https://<WRITE_PAT>@github.com/sepisotoni/UmbrellaOS.git 2>/dev/null || (cd UmbrellaOS && git pull)
cd /workspaces/UmbrellaOS

for FILE in \
  "umbrella-discord-CURRENT/bot/cogs/ask_cog.py:/bot/cogs/ask_cog.py" \
  "umbrella-discord-CURRENT/bot/cogs/webhook_cog.py:/bot/cogs/webhook_cog.py" \
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
All uploads → 204, restart → 204. Once bot is online it will push its command manifest to `POST /api/v1/bot/commands` automatically.

### 🟡 Discord Hub page — mock data
`DiscordView.tsx` still has hardcoded stat cards, guild info, role sync table, and slash commands. A prompt has been written to fix all of it — see conversation history. The slash commands section specifically needs the bot to be online first so it can push its manifest to `POST /api/v1/bot/commands`. The core endpoint (`GET /api/v1/bot/commands`) and migration (036) still need to be built as part of that fix — they were added to the Discord Hub prompt as an extra section.

### 🟡 Console stream untested end-to-end
Plugin pushes to core every 5s, dashboard polls as fallback. Untested until plugin is confirmed healthy on BisectHosting.

### 🟢 Low priority
- Bot cogs fully migrate to `self.bot.remote.*` (some still read env vars)
- `/verify` Discord slash command (in-game only currently)
- Dashboard login subtitle copy

---

## What Landed This Session

| Commit | What |
|---|---|
| `fbcdac1` | Core: knowledge REST router — 8 endpoints, all auth'd |
| `9bdd2da` | Dashboard: Knowledge Base UI — two-panel, search, create, edit, delete, approve/reject, version history |
| `c21d098` | Bot: knowledge_cog → direct REST instead of capability registry |
| `9c5c77b` | Bugfixes: API key auth in permissions, replay event normalization, webhook deliver, dashboard field mismatches |
| `6f8a5cc` | Audit: utcnow sweep + post-pull verification |

---

## Full Feature Status

### Dashboard tabs
All on real data. Knowledge Base tab fully built and wired.

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
| Knowledge Base | ✅ Two-panel, search, CRUD, pending review |
| Discord Hub | ⚠️ Mostly mock — needs Discord Hub fix prompt applied |
| Console | ✅ WS + plugin poll fallback |
| Profile modal | ✅ RBAC perms, sign out, Discord avatar |
| Alt Detection | ✅ |
| Verification | ✅ |
| Audit | ✅ |

### Bot
| Feature | Status |
|---|---|
| Hosting cog | ✅ |
| Role permission system | ✅ |
| /ask copilot | ✅ |
| Knowledge search | ✅ REST endpoint |
| Webhook/event push | ✅ |
| Duplicate command fix | ✅ |
| RemoteConfig (read settings from DB) | ✅ wired in bot.py/config.py |
| File upload to HeavenCloud | 🔴 Blocked — node outage |
| Command manifest push | ✅ In bot.py, triggers on startup |

### Core
| Feature | Status |
|---|---|
| Auth (Discord OAuth + session) | ✅ |
| RBAC permissions | ✅ Fresh from DB per request |
| Players / Risk scoring | ✅ |
| Punishments / Appeals | ✅ |
| AI tasks (copilot, review, crash) | ✅ |
| Knowledge base | ✅ Full CRUD + search |
| Settings (all categories) | ✅ |
| Plugin heartbeat | ✅ |
| Plugin console push/pull | ✅ |
| Bot registration | ✅ |
| Bot command manifest | ⚠️ Endpoint + migration still to build (in Discord Hub prompt) |
| Discord Hub stats endpoint | ⚠️ Still to build |

---

## Alembic Migration Heads
- `035_plugin_console_lines` (main chain)
- `030_appeal_close_fields` (valid side branch)
- Migration 036 (bot_command_manifest) — still to create

---

## Architecture Notes
- **Knowledge search:** ILIKE, no embeddings. Fast, works offline.
- **Bot command manifest:** Bot pushes `POST /api/v1/bot/commands` on startup → stored as JSON in `bot_command_manifest` table → dashboard reads `GET /api/v1/bot/commands`. Not built yet — part of Discord Hub fix.
- **Plugin console:** JVM buffer → POST /api/v1/plugin/servers/{id}/console/lines every 5s → capped 500/server → dashboard polls GET .../recent
- **RemoteConfig:** Bot reads `discord.*` from core settings at startup. Falls back to defaults if missing.
- **Permissions:** Fresh from DB per request. No re-login after role changes.
- **HeavenCloud API calls:** Must come from codespace (`account: secondary`), not sandbox.
