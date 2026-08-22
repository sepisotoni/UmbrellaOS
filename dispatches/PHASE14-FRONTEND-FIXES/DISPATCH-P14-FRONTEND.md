# CRITICAL CONTEXT — Read before anything else

## No Daemon Layer
This dashboard has NO daemon layer. There is no node agent, no infrastructure manager, no daemon process. The stack is:
- **umbrella-core** (FastAPI on Render) — the only backend, everything goes through here
- **Minecraft plugin** — pushes heartbeats, TPS, player counts, GrimAC flags TO core via HTTP POST
- **Discord bot** — talks to core via HTTP

Anywhere the dashboard shows "Daemons Online", "RAM Pool", "Allocated RAM", "Infrastructure nodes" — that data doesn't exist. When you hit those in Tasks 9-10, replace daemon language with plugin heartbeat language. "Servers Online" = servers that sent a heartbeat in the last 60 seconds via `GET /api/v1/dashboard/servers`.

## Task 1 is already done — start from Task 2
Task 1 (6 method/schema blockers) was completed in a previous session. Do NOT redo it. Start from Task 2.

## Before Task 2 — one quick backend fix first
In `umbrella-core-CURRENT`, find the crash risk endpoint added by the backend sub-chat and change the risk level enum from `NONE/WATCH/CRITICAL/INSUFFICIENT_DATA` to `LOW/MEDIUM/HIGH/CRITICAL/INSUFFICIENT_DATA`. Commit it (`core: fix crash risk levels to LOW/MEDIUM/HIGH/CRITICAL`), push, then start Task 2.

## Commit after EVERY task
Commit and push after completing each task before moving to the next. Use the format: `dashboard: <what you did> (P14 Task N)`. If you hit the token limit mid-session, committed work is safe. Do NOT batch commits at the end.

## Read files lazily
Only read the specific function or section you need — not the whole file. DashboardContext.tsx and api.ts are large. Search for the relevant function, read only that part. This preserves your context window.

## Error and empty states
Every metric card, banner, and data table must have proper error/loading/empty states. Never show a healthy indicator when data is missing or core is unreachable. Known issue: `0/0 Infrastructure` currently shows "100% Daemons Online" — this is wrong and must be fixed when you reach the Overview/Topology tasks.

---

# DISPATCH: Phase 14 — Frontend Fixes & Page Redesigns

**Type:** Sub-chat (write access)
**Scope:** `umbrella-dashboard-CURRENT/` only — do NOT touch `umbrella-core-CURRENT/`
**Write PAT:** [WRITE_PAT — see head chat]
**Read-only PAT:** [READ_ONLY_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip at dispatch time:** db986b8

---

## Context

Read these first before touching any code:
- `PHASE14-QUALITY-AUDIT.md` — the full audit. Every task below comes from it.
- `umbrella-dashboard-CURRENT/src/lib/api.ts` — the API client
- `umbrella-dashboard-CURRENT/src/context/DashboardContext.tsx` — all data fetching and state
- `umbrella-dashboard-CURRENT/src/services/dataAdapters.ts` — backend→UI data transforms
- `umbrella-dashboard-CURRENT/src/types/dashboard.ts` — TypeScript types

The dashboard is a **React + Vite + TypeScript SPA**. Dark navy/purple theme. All API calls go through `src/lib/api.ts`. All shared state lives in `DashboardContext.tsx`. Match existing code style exactly.

**Important:** The backend sub-chat is running in parallel adding new endpoints. Assume the following will exist by the time this is wired:
- `GET /api/v1/anticheat/violations`
- `GET /api/v1/staff` (list)
- `GET /api/v1/verification/links`
- `POST /api/v1/ai/copilot`
- `POST /api/v1/ai/providers/test`
- `GET /api/v1/ai/crash-risk/{server_id}`
- `GET /api/v1/webhooks`, `POST /api/v1/webhooks`, `DELETE /api/v1/webhooks/{id}`
- `GET /api/v1/auth/keys`, `POST /api/v1/auth/keys`, `DELETE /api/v1/auth/keys/{id}`

---

## Tasks

### Task 1 — Fix the 6 method/schema blockers (do these first)

These are broken right now and affect core moderation workflows.

**1a. Punishment revoke: PATCH → POST**
File: `src/lib/api.ts` — find `revokePunishment()`, change `PATCH` to `POST`.

**1b. Feature flag toggle: PATCH → POST**
File: `src/lib/api.ts` — find the feature flag update call, change `PATCH /api/v1/feature-flags/{name}` to `POST /api/v1/feature-flags` with body `{name, enabled}`.

**1c. AI task approval: add required body**
File: `src/lib/api.ts` or `DashboardContext.tsx` — find `approveAITask()`, add body `{action_taken: "APPROVED", reviewed_by: currentUser?.username ?? "staff"}`.

**1d. Player lookup: remove fake UUID fallback**
File: `src/lib/api.ts` — find `lookupPlayer()` or equivalent. Remove the `Math.random()` UUID fallback in the catch block. On failure, throw the error — let the UI show it. Never fabricate a UUID.

**1e. Staff list: fix route**
File: `src/lib/api.ts` — find `getStaff()`. Change `GET /api/v1/staff` call — this is already correct since the backend sub-chat will add this route. Just make sure the call exists and is wired.

**1f. Translation param name**
File: `src/components/translation/TranslationView.tsx` or `src/lib/api.ts` — find `translateText()`. Change `targetLang` to `target_language` in the request body.

---

### Task 2 — Wire real anticheat violations feed

**File:** `src/components/moderation/ModerationView.tsx` and `src/lib/api.ts`

The GrimAC violations tab currently uses `grimViolations` from context (local state seeded from `initialState.ts`).

- Add `getAnticheatViolations(params?: {player_uuid?: string, server_id?: string, check_name?: string, limit?: number})` to `api.ts` → `GET /api/v1/anticheat/violations`
- In `ModerationView.tsx`, fetch violations from the real endpoint on mount (use `useEffect` + `useState`, keep it local to this component — don't add to global context)
- Show a loading state while fetching, error state on failure
- Keep the existing UI shape — just replace the data source

---

### Task 3 — Wire real staff list

**File:** `src/components/staff/StaffView.tsx` and `src/lib/api.ts`

- Add `getStaff()` to `api.ts` → `GET /api/v1/staff`
- In `StaffView.tsx`, fetch on mount, replace the empty/hardcoded state
- Map the backend response fields (`discord_id`, `username`, `role`, `linked_minecraft_username`) to the existing `StaffMember` type — add a data adapter in `dataAdapters.ts`

---

### Task 4 — Wire real verification links

**File:** `src/components/verification/VerificationView.tsx` and `src/lib/api.ts`

- Add `getVerificationLinks()` to `api.ts` → `GET /api/v1/verification/links`
- Replace the hardcoded `lnk-1`, `lnk-2`, `lnk-3` seed data with a real fetch on mount
- Keep existing UI shape — just swap the data source

---

### Task 5 — Wire real copilot chat

**File:** `src/components/ai/AIOperationalView.tsx` and `src/context/DashboardContext.tsx`

The `sendCopilotPrompt()` function currently simulates a response locally with hardcoded strings.

- Add `sendCopilotMessage(message: string, context?: string)` to `api.ts` → `POST /api/v1/ai/copilot`
- In `DashboardContext.tsx`, update `sendCopilotPrompt()` to call the real endpoint
- On response, add the assistant message to `copilotMessages` as before
- On error (503 from backend), show an error toast and add an error message to the chat: "Copilot unavailable — AI backend returned an error."
- Keep the existing chat UI unchanged

---

### Task 6 — Wire real AI provider test

**File:** `src/components/ai/AIOperationalView.tsx` or wherever the provider test button lives

- Add `testAIProvider(provider: string, apiKey?: string)` to `api.ts` → `POST /api/v1/ai/providers/test`
- Replace the fake successful response in the catch block with the real call
- Show real latency and model name in the test result UI

---

### Task 7 — Wire crash risk endpoint

**File:** `src/components/ai/AIOperationalView.tsx`

The crash reports section currently calls `api.getCrashReports()` which hits a non-existent endpoint.

- Add `getCrashRisk(serverId: string)` to `api.ts` → `GET /api/v1/ai/crash-risk/{server_id}`
- In the AI view, replace the crash dump list with a crash risk assessment card per server
- Show: server name, risk level (colour-coded badge: LOW=green, MEDIUM=yellow, HIGH=orange, CRITICAL=red), TPS trend, recommendation text
- Fetch for `selectedServerId` from context, refetch when server selection changes

---

### Task 8 — Wire webhooks and API keys

**File:** `src/components/api-hub/ApiHubView.tsx` and `src/lib/api.ts`

Webhooks:
- Add `getWebhooks()` → `GET /api/v1/webhooks`
- Add `createWebhook(data)` → `POST /api/v1/webhooks`
- Add `deleteWebhook(id)` → `DELETE /api/v1/webhooks/{id}`
- Add `testWebhook(id)` → `POST /api/v1/webhooks/{id}/test`
- Wire these into `ApiHubView.tsx` replacing the local state

API Keys:
- Add `getApiKeys()` → `GET /api/v1/auth/keys`
- Add `createApiKey(data)` → `POST /api/v1/auth/keys`
- Add `revokeApiKey(id)` → `DELETE /api/v1/auth/keys/{id}`
- Wire these into `ApiHubView.tsx` replacing the local state

---

### Task 9 — Redesign Snapshots page

**File:** `src/components/snapshots/SnapshotsView.tsx`

The current page describes "world checkpoints" but the backend does player state snapshots (inventory, position, health). Redesign the page to match reality.

New design:
- Player UUID/username search input at the top
- On search: `GET /api/v1/snapshots/players/{uuid}` → list that player's state snapshots
- Each snapshot shows: trigger type, timestamp, health/food, XP level
- "Restore" button per snapshot: `POST /api/v1/snapshots/{id}/restore` (if this route doesn't exist from the backend sub-chat, show a disabled button with tooltip "Restore endpoint pending")
- Remove all server-level checkpoint language, `sizeMb`, `blockChangesCount`, `playerStatesCount`
- Keep the same visual card style

---

### Task 10 — Redesign Topology page (simplify)

**File:** `src/components/topology/TopologyView.tsx`

The current page shows baremetal node hardware telemetry (CPU cores, disk, Docker version, network throughput) that will never be populated from the backend.

Simplify to show what's real:
- Node list from `GET /api/v1/dashboard/servers` (server list is what's actually available)
- Each node card: name, status badge, daemon URL, assigned servers list, last heartbeat
- Remove: CPU usage bars, RAM bars, disk usage, network in/out, running containers count, Docker version
- Keep: server list within each node, status badge, restart daemon button (keep as a toast-only action for now since the backend endpoint isn't confirmed)
- The visual layout can stay similar, just remove the hardware telemetry rows

---

### Task 11 — Cut bloat from AI Intelligence page

**File:** `src/components/ai/AIOperationalView.tsx`

Remove the following from the AI page (they're local simulation with no backend):
- The 6-provider engine matrix / model router tab — the entire "Model Router" section showing Gemini/Claude/OpenAI/DeepSeek/OpenRouter/Ollama cards with failover logs
- The failover event log table
- The "Rate Limit Simulation" section if it exists

Keep:
- Copilot chat tab (now wired to real backend in Task 5)
- AI task queue tab (already real)
- Crash risk tab (now wired in Task 7)

If the model router tab removal leaves the tab bar with only 2-3 tabs, that's fine — it's better than showing fake data.

---

### Task 12 — Cut bloat from Discord page

**File:** `src/components/discord/DiscordView.tsx`

Remove:
- Slash command management table/tab (no backend support, not runtime-manageable)
- Bot status panel (no backend endpoint — hardcoded data)

Keep:
- Chat bridge tab (wire to real message history: add `getBridgeMessages()` → `GET /api/v1/bridge/messages` and seed from real data instead of local state)
- Embed builder tab (keep UI, fix the send button to call `POST /api/v1/bridge/message` correctly — add `source: "DASHBOARD"` to the request body, rename `scope` to whatever the backend actually accepts)
- Webhooks tab (now wired in Task 8)

Also add:
- Bridge settings section: fetch `GET /api/v1/bridge/settings`, show toggles for MC→Discord enabled, Discord→MC enabled, show avatars, channel ID. Save via `PATCH /api/v1/bridge/settings`.

---

### Task 13 — Redesign Translation page

**File:** `src/components/translation/TranslationView.tsx`

The current page is a UI locale/i18n key editor which has no backend support. The backend's translation system is for **player chat** auto-translation.

Redesign:
- Remove the translation key table entirely
- New design: two sections
  1. **Player Language Preferences** — `GET /api/v1/translation/language/all` — table showing player UUID, detected language, confidence, last updated
  2. **Test Translation** — text input + language selector + `POST /api/v1/translation/translate` (fix `targetLang` → `target_language`) → show result inline
- Keep the same dark card visual style

---

### Task 14 — Clean up Automation page

**File:** `src/components/automation/AutomationView.tsx`

Remove:
- "Self-Healing Rules" panel (TPS auto-restart, GC threshold, GrimAC strict mode toggles) — local state only, no backend effect

Keep:
- Cron task list (keep the UI but note these are local state pending backend wiring — add a subtle "Local only — backend sync pending" badge or note)
- Create/toggle/delete/run-now buttons (keep as local state for now)

This is a partial clean — just removing the self-healing section that's actively misleading.

---

## Code Standards

- Keep the dark navy/purple theme and existing component patterns
- All new API calls go in `src/lib/api.ts`
- Data shape transforms go in `src/services/dataAdapters.ts`
- Loading states: use existing spinner/skeleton patterns from other views
- Error states: use existing error card pattern — red border card with error message
- Do NOT add new npm dependencies
- Do NOT change `src/types/dashboard.ts` types unless absolutely necessary — prefer adapters

---

## Commit Instructions

- One commit per task: `dashboard: fix 6 method/schema blockers (P14 Task 1)`
- Push to `main` after each commit
- Do NOT touch anything outside `umbrella-dashboard-CURRENT/`
- When all tasks done, write `dispatches/PHASE14-FRONTEND-FIXES/SUBCHAT-HANDBACK.md` with:
  - All commits (SHA + message)
  - Tasks that couldn't be completed and why
  - Any backend endpoints you expected (from the parallel sub-chat) that weren't there yet
  - Any UI decisions the head chat should review

## Verification before handback

- No hardcoded fake data or `Math.random()` calls remain in data paths
- No local-only state mutations for things that should persist to backend
- All removed sections are fully gone — no dead code left behind
- The 6 blockers from Task 1 are all fixed
