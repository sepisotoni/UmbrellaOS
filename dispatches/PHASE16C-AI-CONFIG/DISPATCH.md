# DISPATCH: Phase 16C — AI Task Model Configuration

**Type:** Sub-chat (write access)
**Scope:** `umbrella-core-CURRENT/` and `umbrella-dashboard-CURRENT/`
**Write PAT:** [WRITE_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip:** d8b9f07

Read files lazily. Commit after every task. Push to main after each commit.

---

## Context

Staff need to configure which AI model handles which task from the dashboard Settings page. The backend already has `api/routers/ai_config.py` — read it first to understand what's there before adding anything.

Supported providers: `gemini`, `anthropic`, `openai`, `deepseek`, `openrouter`

Tasks that need per-model config:
- `player_review` — AI review of a player's anticheat history
- `appeal_review` — AI review of a ban appeal
- `copilot` — Staff copilot chat
- `crash_risk` — Server crash risk analysis
- `chat_responder` — In-game keyword/question responder

---

## Task 1 — Backend: AI task config endpoints

Read `umbrella-core-CURRENT/api/routers/ai_config.py` first.

If `GET /api/v1/ai/config` and `POST /api/v1/ai/config` don't exist or don't support per-task model assignment, add:

```
GET /api/v1/ai/config
Response: {
  "player_review": { "primary": "gemini", "failover": "openrouter" },
  "appeal_review": { "primary": "anthropic", "failover": "gemini" },
  "copilot": { "primary": "gemini", "failover": "openrouter" },
  "crash_risk": { "primary": "gemini", "failover": null },
  "chat_responder": { "primary": "openrouter", "failover": null }
}

POST /api/v1/ai/config
Body: { "task": "player_review", "primary": "anthropic", "failover": "openrouter" }
Response: updated config
```

Store in the existing `settings` table as JSON under key `ai.task_config`. If settings table doesn't support JSON values, store as a JSON string.

---

## Task 2 — Backend: AI orchestrator reads task config

Read `umbrella-core-CURRENT/services/ai/` directory.

Update the AI orchestrator/router so when executing a task (player_review, appeal_review etc.) it:
1. Reads the task config via the settings table
2. Uses the configured primary provider
3. On failure, falls back to the failover provider if set
4. If both fail, returns 503

Keep changes minimal — just add config lookup before provider selection.

---

## Task 3 — Dashboard: AI Configuration section in Settings

Read `umbrella-dashboard-CURRENT/src/components/settings/SettingsView.tsx` (or wherever settings are).

Add an "AI Configuration" section with:
- A card per task (Player Review, Appeal Review, Copilot, Crash Risk, Chat Responder)
- Each card has: Primary model dropdown, Failover model dropdown (optional, includes "None")
- Dropdown options: Gemini, Claude (Anthropic), OpenAI, DeepSeek, OpenRouter
- Save button per card — calls `POST /api/v1/ai/config`
- Load current config on mount — `GET /api/v1/ai/config`
- Show loading/error states

---

## Commit Instructions

- `core: add GET/POST /api/v1/ai/config per-task model assignment (P16C Task 1)`
- `core: AI orchestrator reads task config for provider selection (P16C Task 2)`
- `dashboard: AI model config section in Settings (P16C Task 3)`

When done write `dispatches/PHASE16C-AI-CONFIG/SUBCHAT-HANDBACK.md`.
