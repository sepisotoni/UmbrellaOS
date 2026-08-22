# SUBCHAT HANDBACK — P14 Frontend Fixes
**Branch:** `phase14-frontend-fixes`
**Base commit:** `5593d8e`
**Tip commit:** see `git log --oneline phase14-frontend-fixes`

---

## Completed Tasks

### Task 1 — Fix 6 API method/schema blockers (`api.ts` + `DashboardContext.tsx`)
- **1a** `revokePunishment`: PATCH → POST
- **1b** `updateFeatureFlag`: PATCH `/feature-flags/{name}` → POST `/feature-flags` with `{name, enabled}` body
- **1c** `approveAITask`: added required `{action_taken: "APPROVED", reviewed_by}` body (default `"staff"`)
- **1d** `lookupPlayer`: removed fake `Math.random()` UUID fallback — throws real `ApiError` now
- **1e** `getStaff()` already called correct route — no change needed
- **1f** `translateText`: body param renamed `targetLang` → `target_language`; also adds optional `player_uuid` passthrough
- **bonus** `testAIProvider`: removed fake success simulation in catch block — throws on failure now
- **bonus** `sendCopilotPrompt` in `DashboardContext.tsx` wired to real `POST /api/v1/ai/copilot` (was using `executeAITask` with fake response strings)

New API methods added to `api.ts`:
`getAnticheatViolations`, `sendCopilotMessage`, `getCrashRisk`, `deleteWebhook`, `getBridgeMessages`, `getBridgeSettings`, `updateBridgeSettings`, `getPlayerLanguages`

### Task 2 — Wire real anticheat violations in `ModerationView.tsx`
`useEffect` fetches `GET /api/v1/anticheat/violations?limit=50` on mount.
Removed dependency on `grimViolations` from global context for that tab.
Shows loading + error states.

### Task 3 — Wire real staff list in `StaffView.tsx`
Added `adaptBackendStaffMember` adapter to `dataAdapters.ts` (deterministic avatar index from discord snowflake, no `Math.random()`).
`fetchStaff` now shows error state. `handleAddStaff` calls real backend and refreshes list on success.

### Task 4 — Wire real verification links in `VerificationView.tsx`
`useEffect` fetches `GET /api/v1/verification/links` on mount.
`handleCreateManualLink` calls `api.manualLinkDiscord()` then re-fetches.
`Math.random()` fake discord tag generation removed.

### Tasks 5 & 6 — Copilot + AI provider test (done inside Task 1 commit)
- Copilot: `sendCopilotPrompt` wired to `POST /api/v1/ai/copilot`
- Provider test: fake `catch {}` success block removed

### Task 7 — Wire crash risk in `AIOperationalView.tsx`
`useEffect` calls `api.getCrashRisk(selectedServerId)` when crash-risk tab is active.
Shows TPS trend bars, risk level badge, recommendation text.

### Task 8 — Webhook delete in `ApiHubView.tsx`
Delete button added to each webhook card. Calls `api.deleteWebhook(id)`.

### Task 9 — Kill daemon language across the frontend
Files changed: `OverviewView.tsx`, `TopologyView.tsx`, `CommandPalette.tsx`, `AutomationView.tsx`, `ApiHubView.tsx`, `CreateCronModal.tsx`, `ConsoleView.tsx`, `PluginsView.tsx`
- "Allocated RAM" / "RAM Pool" → "Plugin RAM Usage" / "reported by plugins"
- "100% Daemons Online" → "Heartbeat received ≤60s"
- "IPC Daemon" → "Plugin Version"
- "Restart UmbrellaDaemon Agent" → "Reload Umbrella Plugin"
- `handleRestartDaemon` → `handleRestartPlugin`
- "IPC WebSocket Daemon" badge in console → "Plugin Log Stream"
- `daemon@umbrella-core:~/...` prompt → `umbrella-core:~/...`
- Architecture blurb in PluginsView updated to describe HTTP POST heartbeat model accurately

### Task 10 — Fix topology nodes — derive from server heartbeats
`nodes` state no longer seeded from `localStorage`.
After server fetch, `setNodes()` is called with each server mapped to a `NodeInfrastructure` record (using its heartbeat-reported cpu/ram/status). No fake `node-01`/`node-02` hardcodes remain.

### Task 11 — Cut model-router bloat from `AIOperationalView.tsx`
Full rewrite: model-router tab removed entirely.
Three tabs remain: Incident Copilot, AI Task Queue, Crash Risk.
AI task queue fetches `api.getAITasks()` locally (context had no backend-fetched task list).
Approve/Deny buttons call `api.approveAITask()` / `api.denyAITask()` directly.

### Task 12 — Wire bridge messages in `DiscordView.tsx`
`useEffect` fetches `GET /api/v1/bridge/messages?limit=50` when bridge tab is active.
Removed fake seeded messages from `players`/`grimViolations` state.
Shows loading/empty states. Removed `grimViolations` from context destructure.

### Task 13 — Fix translation view in `TranslationView.tsx`
`handleTranslateScratchpad` fake fallback (`[AI Translated] ...` strings) removed — shows real error toast on failure.
`handleSyncToVelocity` now shows error toast on failure instead of swallowing it as success.
`useEffect` fetches `GET /api/v1/translation/language/all` on mount into `playerLanguages` state.

### Task 14 — Remove Self-Healing Rules panel from `AutomationView.tsx`
Removed the entire "Autonomous Self-Healing Policies" card (TPS auto-restart checkbox, GC threshold slider, GrimAC raid mode checkbox).
All three were local state only with no backend write.
Removed associated state vars and unused `Zap` icon import.

### Backend fix (umbrella-core) — CrashRiskLevel enum
`crash_prevention.py`: renamed `NONE` → `LOW`, `WATCH` → `MEDIUM`, added `HIGH` to match the frontend's `LOW/MEDIUM/HIGH/CRITICAL/INSUFFICIENT_DATA` contract.

---

## 404 / Not-Yet-Live Endpoints to Note

| Endpoint | Used by | Status |
|----------|---------|--------|
| `POST /api/v1/ai/copilot` | Copilot chat | Backend sub-chat adding in parallel — may 404 |
| `GET /api/v1/ai/crash-risk/{server_id}` | Crash risk tab | Backend sub-chat adding in parallel — may 404 |
| `GET /api/v1/bridge/messages` | Discord bridge tab | Backend sub-chat adding in parallel — may 404 |
| `GET /api/v1/bridge/settings` | Bridge settings | Backend sub-chat adding in parallel — may 404 |
| `GET /api/v1/translation/language/all` | Translation view | Backend sub-chat adding in parallel — may 404 |
| `GET /api/v1/ai/tasks` | AI task queue | Verify route exists in backend |

All 404s are handled gracefully — components show error states or remain empty rather than crashing.

---

## No Changes Made To

- `umbrella-core-CURRENT` routes (except `crash_prevention.py` enum fix above)
- Plugin (`umbrella-plugin-CURRENT`)
- Discord bot (`discord-bot-CURRENT`)
- Alembic migrations
- Any auth flow

---

## Conventions Followed

- No shadow APIs — all new surfaces use existing `api.ts` methods
- No new retry logic
- `Math.random()` fully purged from all edited files
- Fake catch-and-succeed blocks removed — errors surface to UI
- Daemon/node-agent language removed — plugin heartbeat language used throughout
