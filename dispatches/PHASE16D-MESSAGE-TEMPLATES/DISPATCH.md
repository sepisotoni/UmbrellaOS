# DISPATCH: Phase 16D — Configurable Message Templates

**Type:** Sub-chat (write access)
**Scope:** `umbrella-core-CURRENT/`, `umbrella-dashboard-CURRENT/`, `umbrella-discord-CURRENT/`, `minecraft-plugin/`
**Write PAT:** [WRITE_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip:** d8b9f07

Read files lazily. Commit after every task. Push to main after each commit.

---

## Context

All bot/plugin messages must be editable from the dashboard Settings page. No redeployment needed to change wording. Messages use template variables: `$CODE`, `$PLAYER`, `$DISCORD_INVITE`, `$SERVER`, `$EXPIRES`.

---

## Task 1 — Backend: Store message templates in settings table

Read `umbrella-core-CURRENT/api/routers/settings.py` first.

Ensure `GET /api/v1/settings/{key}` and `POST /api/v1/settings/{key}` exist and work for string values. If not, add them.

Add a seed endpoint or migration that pre-populates these default values in the settings table:

```
verification.dm_prompt = "Hi $PLAYER! To verify your Minecraft account, send this code in-game: $CODE (expires in $EXPIRES)"
verification.success_message = "✅ Your Minecraft account **$PLAYER** has been successfully linked!"
verification.error_already_linked = "❌ This Discord account is already linked to a Minecraft account."
verification.error_invalid_code = "❌ Invalid or expired code. Please run /verify in-game again."
verification.ingame_prompt = "Check your Discord DMs to complete verification! Code expires in $EXPIRES."
verification.ingame_success = "✅ Your Discord account has been linked successfully!"
verification.nickname_format = "$PLAYER"
discord.invite_url = "https://discord.gg/yourserver"
greeter.first_join_message = "Welcome to the server, $PLAYER! Join our Discord: $DISCORD_INVITE"
greeter.return_join_message = "Welcome back, $PLAYER!"
chat_responder.response_style = "friendly"
```

Write these as INSERT ... ON CONFLICT DO NOTHING so existing values aren't overwritten.

---

## Task 2 — Bot: Read templates from core

Read `umbrella-discord-CURRENT/bot/cogs/verification_cog.py`.

Update the verification cog to fetch message templates from core instead of using hardcoded strings:
- On cog load, fetch all `verification.*` settings via `GET /api/v1/settings/{key}`
- Cache them in the cog instance
- Use `$VARIABLE` substitution before sending:
```python
def render(template: str, **kwargs) -> str:
    for key, val in kwargs.items():
        template = template.replace(f"${key.upper()}", str(val))
    return template
```
- Apply to: DM prompt, success message, error messages
- Refresh cache every 5 minutes (in case staff changes templates)

---

## Task 3 — Plugin: Read templates from core

Read `minecraft-plugin/src/main/java/com/umbrellaos/plugin/ConfigManager.java`.

Add a `MessageTemplateManager.java` class that:
- On startup, fetches `verification.ingame_prompt` and `verification.ingame_success` from `GET /api/v1/plugin/config` (or direct settings endpoint)
- Caches them
- Provides `render(String template, Map<String, String> vars)` method for `$VARIABLE` substitution
- Refreshes every 5 minutes

Update wherever the plugin sends in-game verification messages to use `MessageTemplateManager` instead of hardcoded strings.

---

## Task 4 — Dashboard: Message Templates section in Settings

Add a "Message Templates" section to the Settings page with:
- A text area per template key, labelled clearly (e.g. "Verification DM Prompt")
- Variable hints shown below each field: "Available: $CODE, $PLAYER, $EXPIRES"
- Load values on mount via `GET /api/v1/settings/{key}` for each key
- Save button per field or a single "Save All" — `POST /api/v1/settings/{key}` per changed field
- Show loading/error states

---

## Commit Instructions

- `core: settings GET/POST endpoints + default message template seeds (P16D Task 1)`
- `bot: verification cog reads message templates from core (P16D Task 2)`
- `plugin: MessageTemplateManager reads templates from core (P16D Task 3)`
- `dashboard: message templates section in Settings (P16D Task 4)`

When done write `dispatches/PHASE16D-MESSAGE-TEMPLATES/SUBCHAT-HANDBACK.md`.
