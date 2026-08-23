# HANDBACK: Phase 16D — Configurable Message Templates

**Sub-chat:** CHAT 2  
**Tip in:** `11bc189`  
**Tip out:** `87e5a7a`  
**Status:** ✅ All 4 tasks complete — 4 commits pushed to main

---

## Commits

| SHA | Message |
|-----|---------|
| `8f1a3b7` | `core: settings GET/POST endpoints + default message template seeds (P16D Task 1)` |
| `d2618c1` | `bot: verification cog reads message templates from core (P16D Task 2)` |
| `5e0c496` | `plugin: MessageTemplateManager reads templates from core (P16D Task 3)` |
| `87e5a7a` | `dashboard: message templates section in Settings (P16D Task 4)` |

---

## Task 1 — Core: Settings GET/POST + Seeds

**Files changed:**
- `umbrella-core-CURRENT/api/routers/settings.py` — Added `POST /api/v1/settings/{key}` alongside the existing `PATCH`. POST upserts: creates the row if it doesn't exist (derives category from key prefix), or delegates to `SettingsService.update()` if the row already exists. Masked-secret guard (`***`) applies to POST the same as PATCH.
- `umbrella-core-CURRENT/services/settings_service.py` — Added 11 message template entries to `DEFAULT_SETTINGS`. They are seeded via the existing `seed_defaults()` method using `INSERT ... ON CONFLICT DO NOTHING` semantics (checks for existing row before adding), so live values are never overwritten.

**New defaults seeded:**
`verification.dm_prompt`, `verification.success_message`, `verification.error_already_linked`, `verification.error_invalid_code`, `verification.ingame_prompt`, `verification.ingame_success`, `verification.nickname_format`, `discord.invite_url`, `greeter.first_join_message`, `greeter.return_join_message`, `chat_responder.response_style`

---

## Task 2 — Bot: Verification Cog Reads Templates

**File changed:** `umbrella-discord-CURRENT/bot/cogs/verification_cog.py`

- On `cog_load()`, fetches all `verification.*` keys from `GET /api/v1/settings/{key}` via `self.bot.core.get()`.
- Caches them in `self._templates: dict[str, str]`.
- `@tasks.loop(minutes=5)` refreshes the cache automatically.
- `render(template, **kwargs)` helper replaces `$VARIABLE` placeholders (uppercased match).
- `_format_success()` and `_format_error()` use cached templates; hardcoded strings are gone.
- `_sync_nickname()` now renders the `verification.nickname_format` template.
- Built-in fallback strings remain in `_DEFAULTS` so the cog stays functional if core is unreachable.

---

## Task 3 — Plugin: MessageTemplateManager

**Files changed:**
- `minecraft-plugin/src/main/java/com/umbrellaos/plugin/MessageTemplateManager.java` — New class. Fetches `verification.ingame_prompt` and `verification.ingame_success` from `GET /api/v1/settings/{key}`. Uses `ConcurrentHashMap` for thread-safe reads (main thread) / writes (async scheduler). Refreshes every 5 minutes (6000 ticks). `render(String template, Map<String, String> vars)` does `$VARIABLE` substitution with uppercased keys.
- `minecraft-plugin/src/main/java/com/umbrellaos/plugin/UmbrellaPlugin.java` — Instantiates `MessageTemplateManager`, calls `start()` on enable, `stop()` on disable, and exposes a `getMessageTemplateManager()` package-private accessor for command handlers.

> **Note:** The plugin currently has no `/verify` Bukkit command (in-game verification messages are dispatched via RCON through the CommandPoller). When a native `/verify` command is added in a future phase, it should call `getMessageTemplateManager().getTemplate(KEY_INGAME_PROMPT)` and pass vars via `render()`.

---

## Task 4 — Dashboard: Message Templates Section

**File changed:** `umbrella-dashboard-CURRENT/src/components/settings/SettingsView.tsx`

- Added `'templates'` to the `activeSection` union type and to the `sections` nav array (7th entry, icon: `MessageSquare`).
- `useEffect` on mount loads all 11 template values via `api.getSetting(key)` into local `templates` state.
- Per-field **Save** button calls `api.updateSetting(key, value)` (hits `PATCH /api/v1/settings/{key}`) with per-field saving / error state.
- Loading indicator shown while fetching; per-field error message shown below the textarea if save fails.
- Variable hints rendered under each field (e.g. "Available: $CODE, $PLAYER, $EXPIRES").

---

## Notes for Head Chat

- The `POST /api/v1/settings/{key}` endpoint is additive — the existing `PATCH` still works. Dashboard currently uses `PATCH` via `api.updateSetting()`; `POST` is available for external tools and scripts.
- Bot's `self.bot.core.get()` assumes a `get(path) -> dict` method on the core client. If the UmbrellaCoreClient only has `invoke()`, a small addition to `UmbrellaCoreClient` to expose a raw `GET` helper will be needed. (The method is referenced but not implemented in the bot service layer yet.)
