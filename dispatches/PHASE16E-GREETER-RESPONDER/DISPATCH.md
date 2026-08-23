# DISPATCH: Phase 16E — Greeter + Chat Keyword Responder

**Type:** Sub-chat (write access)
**Scope:** `minecraft-plugin/` and `umbrella-core-CURRENT/`
**Write PAT:** [WRITE_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip:** 6fbeaff

Read files lazily. Commit after every task. Push to main after each commit.

---

## Context

Two new plugin features triggered by in-game events:
1. **Greeter** — welcomes new players on first join with a configurable message
2. **Chat Keyword Responder** — detects common questions in chat and replies via AI

Both features:
- Are toggleable per-server from settings (`greeter.enabled`, `chat_responder.enabled`)
- Read message templates from core via `MessageTemplateManager` (already built in Phase 16D)
- Are configurable from the dashboard Settings page (Phase 16D already added the template fields)

Read these first:
- `minecraft-plugin/src/main/java/com/umbrellaos/plugin/UmbrellaPlugin.java`
- `minecraft-plugin/src/main/java/com/umbrellaos/plugin/MessageTemplateManager.java`
- `minecraft-plugin/src/main/java/com/umbrellaos/plugin/CoreApiClient.java`
- `minecraft-plugin/src/main/resources/config.yml`

---

## Task 1 — Backend: Greeter + chat responder config endpoints

Read `umbrella-core-CURRENT/api/routers/settings.py` first.

Add these default settings seeds (INSERT ... ON CONFLICT DO NOTHING) alongside the Phase 16D seeds:
```
greeter.enabled = "true"
greeter.first_join_message = "Welcome to the server, $PLAYER! Join our Discord: $DISCORD_INVITE"
greeter.return_join_message = "Welcome back, $PLAYER!"
chat_responder.enabled = "true"
chat_responder.keywords = ["how to join","whats the ip","what's the ip","how do i rank up","discord link","how do i appeal","how do i verify","what are the rules"]
chat_responder.cooldown_seconds = "60"
chat_responder.reply_method = "chat"
chat_responder.response_style = "friendly and brief, 1-2 sentences max"
```

Store `chat_responder.keywords` as a JSON array string.

---

## Task 2 — Plugin: Greeter

**New file:** `minecraft-plugin/src/main/java/com/umbrellaos/plugin/GreeterListener.java`

Implements `Listener`. On `PlayerJoinEvent`:
1. Check `config.yml` key `greeter.enabled` (default: true) — skip if false
2. Call `GET /api/v1/players/{uuid}` via `CoreApiClient` to check if player is new
   - New player = `first_seen` within last 60 seconds of join time
   - On API failure, skip greeter silently (fail-open)
3. Fetch appropriate template from `MessageTemplateManager`:
   - New player: `greeter.first_join_message`
   - Returning player: `greeter.return_join_message` (if set and non-empty)
4. Substitute variables: `$PLAYER` = player name, `$DISCORD_INVITE` = `discord.invite_url` setting, `$SERVER` = server name from config
5. Send as:
   - Title + subtitle on screen (5 second display) for new players
   - Chat message for all players (prefix with empty line for visibility)
6. For returning players: chat message only, no title

Register in `UmbrellaPlugin.onEnable()`.

Add to `config.yml`:
```yaml
greeter:
  enabled: true
```

---

## Task 3 — Plugin: Chat Keyword Responder

**New file:** `minecraft-plugin/src/main/java/com/umbrellaos/plugin/ChatResponderListener.java`

Implements `Listener`. On `AsyncPlayerChatEvent`:
1. Check `config.yml` key `chat_responder.enabled` (default: true) — skip if false
2. Check per-player cooldown (use a `ConcurrentHashMap<UUID, Long>` in the class) — skip if within cooldown
3. Fetch keyword list from `MessageTemplateManager` (read `chat_responder.keywords` as JSON array)
4. Check if message contains any keyword (case-insensitive, substring match)
5. If matched:
   - Set cooldown for this player (`System.currentTimeMillis() + cooldown_seconds * 1000`)
   - Call `POST /api/v1/ai/copilot` via `CoreApiClient`:
     ```json
     {
       "message": "<player message>",
       "context": "Player asked this in Minecraft chat on server <server_name>. Answer briefly in 1-2 sentences. Be friendly."
     }
     ```
   - On success: reply in chat as `[Assistant] <response>` (use `Bukkit.broadcastMessage` or `player.sendMessage`)
   - On API failure: silently skip, log warning
6. The AI call must be async — use `Bukkit.getScheduler().runTaskAsynchronously()`

Add to `config.yml`:
```yaml
chat_responder:
  enabled: true
```

Register in `UmbrellaPlugin.onEnable()`.

---

## Task 4 — Dashboard: Greeter + chat responder settings section

Read `umbrella-dashboard-CURRENT/src/components/settings/SettingsView.tsx`.

Add a "Player Experience" section with:

**Greeter:**
- Toggle: enabled/disabled → `POST /api/v1/settings/greeter.enabled`
- Text area: first join message (variables: `$PLAYER`, `$DISCORD_INVITE`, `$SERVER`)
- Text area: return join message (variables: `$PLAYER`, `$SERVER`)

**Chat Keyword Responder:**
- Toggle: enabled/disabled → `POST /api/v1/settings/chat_responder.enabled`
- Tag input: keyword list (add/remove keywords) → `POST /api/v1/settings/chat_responder.keywords` (JSON array)
- Number input: cooldown seconds (default 60)
- Dropdown: reply method (Chat / DM)
- Text area: response style hint

---

## Commit Instructions

- `core: greeter + chat responder config seeds (P16E Task 1)`
- `plugin: GreeterListener — welcome new and returning players (P16E Task 2)`
- `plugin: ChatResponderListener — AI answers common questions in chat (P16E Task 3)`
- `dashboard: Player Experience settings section (P16E Task 4)`

When done write `dispatches/PHASE16E-GREETER-RESPONDER/SUBCHAT-HANDBACK.md`.
