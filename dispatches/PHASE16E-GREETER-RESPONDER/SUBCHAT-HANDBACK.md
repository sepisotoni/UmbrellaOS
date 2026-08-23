# SUBCHAT HANDBACK — Phase 16E: Greeter + Chat Keyword Responder

**Status:** ✅ Complete — all 4 tasks committed and pushed to main  
**Final tip:** `1ed7601`

---

## Tasks Completed

### Task 1 — Backend: Config Seeds (`a27c458`)
**File:** `umbrella-core-CURRENT/services/settings_service.py`

Added missing seeds to `DEFAULT_SETTINGS`:
- `greeter.enabled` = `"true"`
- `chat_responder.enabled` = `"true"`
- `chat_responder.keywords` = JSON array of 8 default phrases
- `chat_responder.cooldown_seconds` = `"60"`
- `chat_responder.reply_method` = `"chat"`
- `chat_responder.response_style` = `"friendly and brief, 1-2 sentences max"`

Pre-existing seeds for `greeter.first_join_message` and `greeter.return_join_message` were retained; `chat_responder.response_style` value was updated from `"friendly"` to the dispatch-specified longer value.

---

### Task 2 — Plugin: GreeterListener (`b3f3971`)
**New file:** `minecraft-plugin/src/main/java/com/umbrellaos/plugin/GreeterListener.java`

- Checks `greeter.enabled` in config.yml (default: true)
- Calls `GET /api/v1/players/{uuid}` to detect new vs returning (new = `first_seen` within 60s, or 404)
- New players: title + subtitle on screen (10/100/20 tick fade), broadcast in chat with leading blank line
- Returning players: personal `player.sendMessage` only, no broadcast
- `$PLAYER`, `$DISCORD_INVITE`, `$SERVER` substitution via `MessageTemplateManager.render()`
- All HTTP calls async; main-thread-only Bukkit calls dispatched via `runTask()`. Fails silently on any API error.

**Also updated:**
- `MessageTemplateManager.java` — added constants and cache entries for `greeter.first_join_message`, `greeter.return_join_message`, `discord.invite_url`, `chat_responder.keywords`, `chat_responder.cooldown_seconds`, `chat_responder.response_style`; expanded `KEYS[]` and `DEFAULTS` map
- `config.yml` — added `greeter.enabled: true` and `chat_responder.enabled: true` blocks
- `UmbrellaPlugin.java` — added `GreeterListener` and `ChatResponderListener` fields; registered both in `onEnable()`

---

### Task 3 — Plugin: ChatResponderListener (`b272ad5`)
**New file:** `minecraft-plugin/src/main/java/com/umbrellaos/plugin/ChatResponderListener.java`

- Listens on `AsyncPlayerChatEvent`
- Checks `chat_responder.enabled` in config.yml (default: true)
- Per-player cooldown via `ConcurrentHashMap<UUID, Long>` (reads `chat_responder.cooldown_seconds` from template cache)
- Parses `chat_responder.keywords` JSON array from `MessageTemplateManager`; case-insensitive substring match
- On match: sets cooldown immediately, then `runTaskAsynchronously` → `POST /api/v1/ai/copilot` with `{message, context}`
- Reply sent via `player.sendMessage()` prefixed `§8[§bAssistant§8] §7`; `runTask()` back to main thread
- All failures logged as warnings and silently skipped (fail-open)

---

### Task 4 — Dashboard: Player Experience Section (`1ed7601`)
**File:** `umbrella-dashboard-CURRENT/src/components/settings/SettingsView.tsx`

Added `'player-experience'` to the `activeSection` union type and nav sections list.

New state vars: `greeterEnabled`, `greeterFirstJoinMsg`, `greeterReturnMsg`, `chatResponderEnabled`, `chatResponderKeywords` (string[]), `chatResponderNewKeyword`, `chatResponderCooldown`, `chatResponderReplyMethod`, `chatResponderStyle`.

**"Player Experience" section renders:**
- **Greeter:** toggle → `POST greeter.enabled`; textarea → `greeter.first_join_message`; textarea → `greeter.return_join_message`
- **Chat Responder:** toggle → `chat_responder.enabled`; tag input (add/remove) → `chat_responder.keywords` (JSON array); number input → `chat_responder.cooldown_seconds`; dropdown (Chat / DM) → `chat_responder.reply_method`; textarea → `chat_responder.response_style`

Note: rebase conflict occurred on push (head chat added `DASHBOARD-IDEAS-FROM-GEMINI.md` concurrently); resolved by keeping sub-chat version, rebased cleanly.

---

## Notes for Head Chat

- `SettingsView.tsx` was absent from remote at the time of the conflicting rebase (head chat had deleted it). The file was re-created intact by the rebase resolution — head chat should verify it matches the intended codebase state.
- The `GET /api/v1/players/{uuid}` endpoint is called by GreeterListener on every join. If this endpoint has auth requirements that differ from the plugin key, the greeter will silently skip (fail-open). Worth verifying the endpoint accepts `X-Plugin-Key`.
- `POST /api/v1/ai/copilot` requires `operational_intelligence.view` permission per the router. The plugin key (`X-Plugin-Key`) must map to a role with that permission for the chat responder to work.
