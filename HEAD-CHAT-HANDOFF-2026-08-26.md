# HEAD CHAT HANDOFF — 2026-08-26

**Repo:** https://github.com/sepisotoni/UmbrellaOS  
**Tip at handoff:** d209178

---

## Open Items (priority order)

### 🔴 BLOCKED — Bot offline (HeavenCloud node outage)

HeavenCloud "Free Node - Texas" daemon is returning 504 on all container ops. Auth works (panel API 200s), but file write, power signal, and resource check all fail. Nothing to do until node recovers.

**When node comes back — run this from codespace (`account: secondary`):**

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
  -d '{"content":"DISCORD_BOT_TOKEN=<DISCORD_BOT_TOKEN>\nUMBRELLA_CORE_URL=https://umbrellaos-core.onrender.com\nUMBRELLA_CORE_API_KEY=<ADMIN_KEY>\n"}'

# Restart
curl -s -o /dev/null -w "restart → %{http_code}\n" -X POST \
  'https://control.heavencloud.in/api/client/servers/671e0e33/power' \
  -H 'Authorization: Bearer <HEAVENCLOUD_API_KEY>' \
  -H 'Content-Type: application/json' \
  -d '{"signal":"restart"}'
```
All uploads → `204`, restart → `204`.

### 🟡 Plugin not built/deployed to BisectHosting

Code exists in `minecraft-plugin/`, compiles clean (Java 21, Paper 1.20.4, 72 tests pass). Not yet on the actual server.

Steps:
1. `cd minecraft-plugin && mvn package -DskipTests` → `target/UmbrellaOSPlugin-*.jar`
2. If GrimAC Maven dep fails: it's `softdepend` — build with `-pl . -am -Dgrimac.skip` or add local jar
3. Upload jar to BisectHosting `plugins/` via SFTP or panel
4. Set `umbrella_core_url` and `plugin_api_key` in `plugins/UmbrellaOSPlugin/config.yml` (check `ConfigManager.java` for exact keys)
5. Restart server → plugin heartbeats should appear on dashboard Fleet tab

### 🟡 Console stream not tested end-to-end

Core has push/pull endpoints, plugin pushes every 5s, dashboard polls as fallback. Untested until plugin is live on BisectHosting.

### 🟡 Phase 16F — Knowledge base

Not started. `/knowledge_search` bot command works against whatever is in the DB. Dashboard Knowledge tab is stubbed. Need: ingestion UI (staff paste/upload docs), embedding storage, search endpoint.

### 🟢 Low priority

- `/verify` Discord slash command (in-game only right now)
- Bot cogs still read some settings from old env vars — should fully migrate to `self.bot.remote.*`
- Dashboard login subtitle is aspirational copy

---

## Alembic Migration Heads

- `035_plugin_console_lines` (main chain)
- `030_appeal_close_fields` (valid side branch)

---

## Dashboard — All tabs on real data ✅

Settings: categorised sidebar, AI task models per-task, plugin tabs  
Profile modal: RBAC perms, sign out, Discord avatar  
Console: WS with plugin poll fallback (⚡/🔌 badge)  
Staff: roles from backend, permission preview in appoint modal  

---

## Key Architecture Notes

- **Plugin console:** JVM buffer → POST /api/v1/plugin/servers/{id}/console/lines every 5s → `plugin_console_lines` table (cap 500/server) → dashboard polls GET .../console/recent
- **Bot RemoteConfig:** `fetch_bot_config()` called in `setup_hook`, reads `discord.*` from core settings API. Falls back to hardcoded defaults.
- **Bot .env:** 3 vars only — token, core URL, admin key. Everything else from DB.
- **Plugin auth:** `require_plugin_key` (X-Plugin-Key header). Also accepts admin key as fallback.
- **Permissions:** Resolved fresh from DB per request. No re-login needed after role changes.
- **HeavenCloud API calls:** Must be made from codespace (`account: secondary`), not sandbox.
