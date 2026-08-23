# DISPATCH: Phase 16C+E Finish — AI Config + Player Experience Settings

**Type:** Sub-chat (write access)
**Scope:** `umbrella-core-CURRENT/` and `umbrella-dashboard-CURRENT/`
**Write PAT:** [WRITE_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip:** b272ad5

Read files lazily — only what you need. Commit after every task.

---

## Context

16C Task 1 and 16E Tasks 1-3 are done. Three tasks remain:

---

## Task 1 — Core: AI orchestrator reads task config (16C Task 2)

Read `umbrella-core-CURRENT/services/ai/` — find the orchestrator/router file.

Update it so when executing a task it:
1. Calls `settings_service.get("ai.task_config")` to get the JSON config
2. Parses the task's primary + failover provider
3. Tries primary provider first
4. On failure, tries failover if set
5. If both fail, raises 503

Keep changes minimal — just add config lookup before provider selection. If the service already has provider selection logic, add the config read at the top of that function only.

---

## Task 2 — Dashboard: AI Configuration section in Settings (16C Task 3)

Read `umbrella-dashboard-CURRENT/src/components/settings/SettingsView.tsx` — find where to add the new section.

Add "AI Configuration" section:
- Card per task: Player Review, Appeal Review, Copilot, Crash Risk, Chat Responder
- Each card: Primary model dropdown + Failover dropdown (includes "None")
- Providers: Gemini, Claude, OpenAI, DeepSeek, OpenRouter
- On mount: `GET /api/v1/ai/config` — populate dropdowns
- Save button per card: `POST /api/v1/ai/config` body `{task, primary, failover}`
- Loading + error states

---

## Task 3 — Dashboard: Player Experience settings section (16E Task 4)

Same file as Task 2.

Add "Player Experience" section:
- **Greeter:** enabled toggle, first join message textarea, return join message textarea
- **Chat Keyword Responder:** enabled toggle, keyword tag input (add/remove), cooldown number input, reply method dropdown (Chat/DM)
- All saved via `POST /api/v1/settings/{key}`
- Load on mount via `GET /api/v1/settings/{key}` for each key
- Variable hints shown below textareas

---

## Commit Instructions

- `core: AI orchestrator reads task config for provider selection (16C Task 2)`
- `dashboard: AI model config section in Settings (16C Task 3)`
- `dashboard: Player Experience settings section (16E Task 4)`

When done write `dispatches/PHASE16CE-FINISH/SUBCHAT-HANDBACK.md` and push.
