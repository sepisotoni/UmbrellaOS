# PHASE14-QUALITY-AUDIT.md
**UmbrellaOS Dashboard ↔ Backend Fit Audit**
**Repo:** sepisotoni/UmbrellaOS | **Tip:** 44f190bb
**Audited by:** Sub-chat (read-only) | **Date:** 2026-08-22

---

## Audit Method

Read every file in `umbrella-dashboard-CURRENT/src/` and all docs, then cross-referenced against every router in `umbrella-core-CURRENT/api/routers/` and `main.py`. All endpoint mapping, type mismatches, and backend gaps identified from source — nothing inferred.

---

## Section 1 — Page-by-Page Fit Assessment

### 1. Overview
**What it does:** Shows real-time server health (TPS, player counts, RAM/CPU), plugin heartbeat status, connection ping to backend, and a global broadcast widget.

**Backend fit:**
- `GET /api/v1/dashboard/servers` — ✅ exists. Returns server list from `PluginHeartbeat` table. However it only emits `tps`, `players`, `online_count`, `version`, `grim_connected`. It does **not** return `ramUsedMb`, `ramTotalMb`, or `cpu` — those fields are hardcoded to `0` in the router (`"ramUsedMb": 0, "ramTotalMb": 0, "cpu": 0`). Dashboard types and adapter both reference these fields; they'll always show zeros.
- `GET /health` — ✅ exists, dashboard polls it for connection latency.
- `POST /api/v1/bridge/message` — ✅ exists, used for global broadcast.
- `GET /api/v1/dashboard/plugins` — ✅ exists, feeds the plugin heartbeat status panel.

**Verdict:** ⚠️ Partial fit — core structure works, but RAM/CPU fields are permanently zero until the plugin starts sending them in the heartbeat payload.

---

### 2. Players
**What it does:** Lists player records with search, suspicion score, alt count, online status; links to ban/punish flow; shows player detail modal via `lookupPlayer`.

**Backend fit:**
- `GET /api/v1/players` — ✅ exists. Returns `uuid`, `username`, `first_seen`, `last_seen`, `playtime`, `joins`, `deaths`, `risk_score`, `suspicion_score`, `discord_id`.
- `GET /api/v1/players/{uuid}` — ✅ exists. Returns the above plus `ip_addresses[]`.
- **Missing:** `GET /api/v1/players/lookup?query=` — the dashboard's `lookupPlayer()` calls this, but there is no `/lookup` route on the players router. On failure it silently falls back to a fabricated response with a random UUID — the catch block literally calls `Math.random()`. This is a live bug.
- **Missing:** `GET /api/v1/players/online` — requested by `BACKEND_REQUIREMENTS.md` but never built.
- **Missing fields:** `PlayerRecord` in the dashboard expects `online`, `ipAddress`, `currentServer`, `pingMs`, `clientBrand`, `altAccountsCount`, `isVpn`, `warningCount`, `punishmentHistoryCount`, `rank`. The backend's `PlayerSchema` returns none of these — the adapter fills them all with defaults/zeros. The player list essentially shows every player as offline with no useful data beyond username and suspicion score.

**Verdict:** ⚠️ Partial fit — basic player list works, player detail is hollow, lookup is broken.

---

### 3. Topology (Nodes/Infrastructure)
**What it does:** Shows a node infrastructure map with CPU, RAM, disk, network, running containers, and assigned servers per node. Node drain/restart controls.

**Backend fit:**
- `GET /api/v1/infrastructure/nodes` — called by `api.getNodes()`. **Does not exist.** No such route in any router or main.py.
- The hosting capability system (`capabilities/hosting.py`) has `hosting.node.list` and `hosting.node.get`, reachable via `POST /api/v1/capabilities/hosting.node.list/invoke`. The dashboard doesn't call that endpoint.
- Node data (`NodeInfrastructure` type) — sourced from localStorage on init, never actually fetched.
- Server drain and daemon restart buttons — local toasts only, no backend call.

**Verdict:** ❌ Poor fit — the node infrastructure API doesn't exist at the REST path the dashboard calls. The dashboard's topology view is entirely a UI shell. The backend has node management functionality, just behind the capabilities router the dashboard doesn't know about.

---

### 4. Console (WebSocket Terminal)
**What it does:** Live server console with ANSI log streaming via WebSocket; multi-server selector; command input.

**Backend fit:**
- `WS /api/v1/hosting/servers/{server_id}/console` — ✅ exists (`hosting_console_ws.py`). Auth via `?token=` query param. Proxies to the node's umbrella-daemon.
- `POST /api/v1/hosting/servers/{id}/command` — called by `api.sendCommand()`. **Does not exist** as a REST route. The hosting_console_ws router only handles WebSocket; there is no separate HTTP command endpoint.
- HTTP server controls (`startServer`, `stopServer`, `restartServer`) call `/api/v1/hosting/servers/{id}/start|stop|restart`. **None of these routes exist.** `server_control.py` only exposes `POST /api/v1/server/control` with a body of `{server_id, action, enabled}`.

**Verdict:** ⚠️ Partial fit — the WebSocket console works if a daemon is connected. The HTTP command endpoint and power control REST paths don't exist.

---

### 5. Moderation (Punishments, Appeals, GrimAC, Alt Detection)
**What it does:** Active punishment ledger, issue/pardon actions, appeals desk with AI sentiment, alt cluster detection, GrimAC violation feed.

**Backend fit:**
- `GET /api/v1/punishments` — ✅ exists. Returns `id`, `player_uuid`, `staff_id`, `type`, `reason`, `created_at`, `expires_at`, `active`.
- `POST /api/v1/punishments/{id}/revoke` — called as PATCH. **The route is `POST /api/v1/punishments/{id}/revoke`**, not PATCH — the dashboard calls `PATCH /api/v1/punishments/{punishmentId}/revoke`, which will 405.
- `POST /api/v1/moderation/{type}` — ✅ exists for kick, warn, ban, unban, ipban, ipunban. But the dashboard calls `issuePunishment()` which calls `/api/v1/moderation/${endpoint}` — this pattern is correct.
- `GET /api/v1/appeals` — ✅ exists. But the backend `AppealSchema` only has `id`, `punishment_id`, `player_uuid`, `status`, `message`, `created_at`. Dashboard's `BackendAppeal` expects `playerUsername`, `type`, `originalReason`, `appealReason`, `aiSentimentScore`, `aiRecommendedAction`, `aiAnalysisSummary`, `assignedStaff` — **none of which exist in the backend schema**. The adapter papers over this with defaults.
- `PATCH /api/v1/appeals/{appealId}` — called with `{status, staff_note}`. Backend has `PATCH /api/v1/appeals/{id}` accepting `{status}` only. `staff_note` is silently ignored.
- `GET /api/v1/anticheat/violations` — **does not exist.** The anticheat router only has `POST /api/v1/anticheat/flag` (plugin ingest). There is no endpoint to query stored violations for the dashboard.
- `GET /api/v1/alts/flagged` and `GET /api/v1/alts/groups` — ✅ both exist in `alt_detection.py`.
- `POST /api/v1/alts/false-positive` — ✅ exists, body differs slightly but workable.

**Verdict:** ⚠️ Partial fit — punishment list and moderation actions mostly work. Appeals are schema-mismatched. GrimAC violation feed has no backend source endpoint.

---

### 6. AI Intelligence (Multi-provider Copilot, Crash Triage, Model Router)
**What it does:** Chat copilot interface, crash dump list, post-mortem generation, model router UI showing 6 providers with health/failover.

**Backend fit:**
- `GET /api/v1/ai/tasks` — ✅ exists. Returns AI review tasks (player review, appeal review).
- `POST /api/v1/ai/review/player/{uuid}` — ✅ exists.
- `POST /api/v1/ai/tasks/{id}/approve|deny` — ✅ exists (approve requires body `{action_taken, reviewed_by}` — dashboard sends no body, will 422).
- `GET /api/v1/diagnostics/crashes` — **does not exist.** Dashboard calls `api.getCrashReports()` to populate crash list. There is no crash report store or endpoint.
- `POST /api/v1/ai/diagnostics/crash` — **does not exist.** The dashboard's `triageCrashReport()` calls this; it returns nothing.
- `POST /api/v1/ai/providers/test` — **does not exist.** The AI provider test button calls this; the catch block silently returns a fake successful response.
- The copilot chat (`sendCopilotPrompt`) — completely local simulation. Calls `executeAITask('copilot', ...)` which resolves entirely in-browser with hardcoded "Operational analysis complete" strings. No backend call is made.
- The 6-provider AI engine with failover logs — **entirely client-side state**. Stored in localStorage, simulated in `DashboardContext.executeAITask()`. The real backend has a proper model router (`services/ai/model_router.py`) with real health tracking in DB, but it is never queried from the dashboard.

**Verdict:** ❌ Poor fit — only the AI task queue (player/appeal reviews) is real. Copilot chat, crash triage, provider testing, and the failover display are all local simulation with no backend connection.

---

### 7. Discord (Chat Bridge, Embed Builder, Slash Commands, Webhooks)
**What it does:** Live chat bridge between MC and Discord, embed builder UI, slash command management table, webhook config, bot status panel.

**Backend fit:**
- `POST /api/v1/bridge/message` — ✅ exists. Body is `{source, player_uuid, player_name, discord_id, message, channel_id}`. Dashboard's `broadcastGlobalMessage()` calls it with `{message, scope}` — the `source` field is missing from the call, and `scope` is not a field the backend accepts. Request will succeed (FastAPI ignores extra fields) but will likely be treated as an incomplete message.
- `GET /api/v1/bridge/messages` — ✅ exists. **Not used by the dashboard.** The chat bridge feed is entirely seeded from local player/GrimAC state data, not from real bridge history.
- `GET /api/v1/bridge/settings` and `PATCH /api/v1/bridge/settings` — ✅ exist. **Not used by the dashboard.**
- `POST /api/v1/discord/notify` — **does not exist.** The dashboard calls `api.sendDiscordNotification()` which hits this route; there is no `/api/v1/discord/` router in main.py.
- `POST /api/v1/discord/embed` — **does not exist** for the same reason.
- Slash command management — entirely local state. No backend endpoint.
- Bot status tab — hardcoded UI, no backend call.

**Verdict:** ⚠️ Partial fit — the bridge message route exists. Everything else (notify, embed, slash commands, bot status) has no backend support.

---

### 8. Plugins (Plugin Heartbeats, Upload, Enable/Disable)
**What it does:** Shows connected plugin heartbeats from backend, plugin catalog with install/enable/disable, plugin config hot-editor, upload .jar modal.

**Backend fit:**
- `GET /api/v1/dashboard/plugins` — ✅ exists. Powers the heartbeats tab. This is real.
- Plugin catalog (marketplace) — the `plugins` state is initialized from `EMPTY_PLUGINS` (empty array) and only populated via the upload flow or localStorage. There is a real marketplace backend (`capabilities/marketplace.py`, `services/plugins/marketplace_service.py`) but the dashboard never calls it.
- `togglePlugin`, `installPlugin`, `uninstallPlugin` — local state mutations only, no backend calls.
- `uploadPluginJar` — creates a local `PluginMeta` and `BackendPluginHeartbeat` entry in state. No actual file upload to backend. The real upload endpoint would be via the capabilities router (not called).
- Plugin config editing — local state mutation only.

**Verdict:** ⚠️ Partial fit — heartbeats tab is real and functional. The plugin catalog and management actions are disconnected from the backend marketplace system.

---

### 9. Snapshots (Server Checkpoints, Rollback)
**What it does:** Lists world snapshots, capture new snapshot, rollback to checkpoint.

**Backend fit:**
- `GET /api/v1/snapshots` — backend has `GET /api/v1/snapshots/players/{minecraft_uuid}` and `GET /api/v1/snapshots/{snapshot_id}`. There is **no** `GET /api/v1/snapshots` list-all endpoint. Dashboard calls `api.getSnapshots()` which calls `/api/v1/snapshots` — this will 404 or 405.
- `POST /api/v1/snapshots` — ✅ exists. But the backend expects `{minecraft_uuid, trigger, health, food, xp, inventory, armor, offhand, x, y, z, ...}` — **player state snapshots**, not world/server snapshots. Dashboard sends `{server_id, type, tags}`, which will 422.
- `POST /api/v1/snapshots/{id}/restore` — **does not exist.** The snapshot router has no restore/rollback endpoint.
- The `createSnapshot` and `rollbackToSnapshot` implementations in DashboardContext are local state mutations with no real API calls (try/catch swallows errors silently).

**Verdict:** ❌ Poor fit — fundamental concept mismatch. The backend snapshots are **player state** (inventory, position, health) for replay/rollback of player data, not world-level server checkpoints the dashboard describes. The page is building on a different mental model than what's built.

---

### 10. Staff (Discord Members, Roles, Permissions)
**What it does:** Staff directory showing Discord identity, role, permissions count; invite flow; promote/demote actions.

**Backend fit:**
- `GET /api/v1/staff` — **does not exist as a GET list.** The staff router has `POST /api/v1/staff/manage`, `POST /api/v1/staff/add`, and `GET /api/v1/staff/discord-members`. The dashboard calls `api.getStaff()` which calls `GET /api/v1/staff` — this will 404.
- `GET /api/v1/staff/discord-members` — ✅ exists. Makes a live call to the Discord API for guild members. Not called by the dashboard.
- `POST /api/v1/staff/invite` — **does not exist.** The dashboard calls this; the staff router has no `/invite` endpoint.
- `GET /api/v1/auth/users` — ✅ exists (lists all User records). This is what the dashboard should be calling to get the staff list, but it calls `/api/v1/staff` instead.
- The dashboard's `StaffView` correctly fetches via `api.getStaff()` on component mount — but since the route doesn't exist, the staff list will always be empty.

**Verdict:** ❌ Poor fit — the staff list route doesn't exist at the called path. The correct equivalent (`GET /api/v1/auth/users`) is available but not wired up.

---

### 11. Audit/Logs (Structured Log Viewer)
**What it does:** Live log stream with level/source/trace filters, combining audit events and application logs.

**Backend fit:**
- `GET /api/v1/logs` — ✅ exists. Supports `query`, `level`, `source`, `trace_id`, `limit` params. Returns structured log entries.
- `GET /api/v1/audit` — ✅ exists. Paginated audit log with `actor_type` filter.
- The `AuditView` actually calls `api.getLogs()` on mount and maps the result — this is one of the few views with genuine live data flow.
- Response shape: backend `logs` endpoint returns `{items: [...], total: int}` via the capability result model. Dashboard's `getLogs()` expects a plain array. If the backend wraps in `{items, total}`, the `Array.isArray(res)` check in the view will fail and show empty — need to verify the exact response shape from `platform.observability.search_logs`.

**Verdict:** ✅ Good fit — the underlying API exists and the view makes real calls. Minor response-shape risk to verify.

---

### 12. Verification (Discord ↔ MC Link Management)
**What it does:** Shows verified Discord↔Minecraft account pairs, pending verifications, unlink action, manual link creation.

**Backend fit:**
- `GET /api/v1/verification/pending` — ✅ exists. Used by the dashboard.
- `GET /api/v1/verification/links` — **does not exist.** The verification router has no list-all-links endpoint. Dashboard calls `api.getVerificationLinks()` which hits this — 404.
- `DELETE /api/v1/verification/unlink/{linkId}` — ✅ exists (via `DELETE /api/v1/verification/unlink/{discord_id}`). Should work.
- `POST /api/v1/verification/manual-link` — ✅ exists. Works as called.
- The `VerificationView` component uses hardcoded seed data (`lnk-1`, `lnk-2`, `lnk-3`) rather than fetching from backend. Real backend data never loads for the links table.

**Verdict:** ⚠️ Partial fit — pending list and manual actions work. The verified-links table has no backend fetch, just hardcoded seeds.

---

### 13. Translation (UI Locale/String Management)
**What it does:** Manages translation keys for in-game messages across locales; test translation scratchpad; sync to backend.

**Backend fit:**
- `POST /api/v1/translation/translate` — ✅ exists. Dashboard test scratchpad calls `api.translateText()` which hits this. Note: the backend endpoint takes `{text, target_language, player_uuid?}` but the dashboard sends `{text, targetLang}` — the parameter name is `targetLang` vs `target_language`. This will fail validation.
- `POST /api/v1/translation/sync` — **does not exist.** The dashboard's sync button calls this; no such route in the translation router.
- The translation key store (the table of message keys and their locale strings) is entirely local hardcoded data — there's no backend endpoint to load or persist the translation key table itself.
- The backend translation system is for **player chat** auto-translation, not UI locale string management. These are different concepts entirely.

**Verdict:** 🔄 Redesign candidate — the backend's translation system auto-translates player chat messages and stores player language preferences. The dashboard's Translation page is a UI locale/i18n key editor for in-game message strings — a different and unsupported use case. The test scratchpad is the closest overlap but has a param name mismatch.

---

### 14. Automation (Cron Jobs, Scheduled Tasks)
**What it does:** Lists scheduled cron tasks, create/toggle/delete/run-now actions, self-healing rule toggles.

**Backend fit:**
- `GET /api/v1/cron/jobs` — **does not exist.** No `/cron/` prefix routes anywhere in `main.py`. The backend has `automation.schedule.list` via the capabilities router at `POST /api/v1/capabilities/automation.schedule.list/invoke`. Dashboard calls the non-existent REST path.
- `POST /api/v1/cron/jobs` — **does not exist** for same reason.
- `PATCH /api/v1/cron/jobs/{id}` — **does not exist.**
- `POST /api/v1/cron/jobs/{id}/run` — **does not exist.**
- All cron state is managed locally via `createCronTask`, `toggleCronTask`, etc. in DashboardContext — local state mutations, no backend persistence.
- Self-healing rule toggles (auto-restart on TPS drop, GC threshold, GrimAC strict mode) — local state only.

**Verdict:** ❌ Poor fit — there is no `/cron/` REST API. The backend has a real automation scheduler accessible via the capabilities system, but it's at a completely different URL the dashboard doesn't know about.

---

### 15. API Hub (Webhooks, API Keys)
**What it does:** API endpoint tester (interactive API explorer), webhook subscription management, API key creation and revocation.

**Backend fit:**
- `GET /api/v1/webhooks` — **does not exist** as a direct REST route. Webhooks are managed via `POST /api/v1/capabilities/webhooks.subscription.list/invoke`. Dashboard calls `/api/v1/webhooks` — 404.
- `POST /api/v1/webhooks` — same issue.
- `POST /api/v1/webhooks/{id}/test` — same issue.
- `GET /api/v1/auth/keys` — **does not exist.** API keys are managed via the identity capability system. Dashboard calls this — 404.
- `POST /api/v1/auth/keys` — same issue.
- `DELETE /api/v1/auth/keys/{id}` — same issue.
- The API endpoint tester (the interactive explorer) does make real calls for the listed endpoints — `getServers()`, `getConnectedPlugins()`, `getPunishments()`, etc. This part actually works.

**Verdict:** ⚠️ Partial fit — the API explorer tab is functional. Webhook management and API key management have no backend endpoints at the called paths.

---

### 16. Settings (Backend Config, Feature Flags, AI Keys)
**What it does:** Backend API URL config, admin key entry, feature flag toggles with rollout percentages, AI provider key/config management, theme preferences.

**Backend fit:**
- `GET /api/v1/settings/{key}` and `PATCH /api/v1/settings/{key}` — ✅ both exist. Work as expected.
- `GET /api/v1/feature-flags` and `PATCH /api/v1/feature-flags/{name}` — ✅ both exist. The feature flag toggle flow works.
- Note: backend `PATCH /api/v1/feature-flags/{name}` doesn't exist — the backend has `POST /api/v1/feature-flags` (upsert) and `DELETE /api/v1/feature-flags/{name}`. There is no PATCH route. The toggle will 404 or 405.
- AI provider configuration panel — **entirely local state** (stored in localStorage as `umb_ai_config`). No backend endpoint is called to store or retrieve AI API keys/provider config from the server.

**Verdict:** ⚠️ Partial fit — settings and feature flag display work. Feature flag toggle is method-mismatched (PATCH vs POST). AI config is local-only.

---

### 17. Login
**What it does:** Discord OAuth initiation, admin key entry, backend connection status display.

**Backend fit:**
- `POST /api/v1/auth/discord/authorize` — ✅ exists. Discord OAuth flow works.
- `POST /api/v1/auth/discord/callback` — ✅ exists.
- `GET /api/v1/auth/me` — ✅ exists. Returns user data.
- `POST /api/v1/auth/logout` — ✅ exists.
- The admin key path (direct CRUD access without OAuth) — ✅ wired correctly via `X-Admin-Key` header.

**Verdict:** ✅ Good fit — auth flow is solid and complete.

---

## Section 2 — Genuine Bloat or Wrong-Fit

### 1. 6-Provider AI Engine Matrix (Settings → AI tab, AI Intelligence page)
**Why it's wrong-fit:** The dashboard implements a complete multi-provider AI routing system (6 providers: Gemini, Anthropic, OpenAI, DeepSeek, OpenRouter, Ollama; failover logs; rate-limit simulation; per-task assignment table) — all as client-side localStorage simulation. The backend has a real AI model router (`services/ai/model_router.py`) with proper health tracking in DB. The two systems have nothing to do with each other. The dashboard's AI config will never actually influence which model the backend uses.

**Recommendation:** Cut the dashboard's multi-provider config panel. Replace with a single "AI Settings" section that reads/writes the real backend AI model config via the capabilities API. The failover log simulation and rate-limit testing UI should be removed — the backend has real health tracking.

---

### 2. Snapshots — World Checkpoint Concept
**Why it's wrong-fit:** The dashboard presents "Time-Travel Snapshots" as world-level server checkpoints with `sizeMb`, `blockChangesCount`, `playerStatesCount`, `retentionDays`. The backend's snapshot system is player inventory/position snapshots for replay and rollback — not world saves. The API doesn't support create-by-server-id, list-all-snapshots, or server rollback. This page is building the wrong thing.

**Recommendation:** Redesign the Snapshots page to match what the backend actually does: show a player's state history, allow restoring a player to a prior state. Or defer it entirely until a real world-snapshot system is built.

---

### 3. Topology Node Infrastructure
**Why it's wrong-fit:** The topology page shows baremetal/VPS nodes with CPU cores, RAM, disk, running containers, Docker version, network throughput — a Pterodactyl/Pterodactyl-style infra view. The backend has node records but they contain `name`, `daemon_url`, `status`, `labels` only. There's no host-level telemetry (CPU, RAM, disk) because the project runs on ACLClouds managed hosting where you don't have that visibility. The page describes infrastructure you don't control.

**Recommendation:** Simplify to show registered nodes (name, daemon URL, status, assigned servers) with a link to restart the daemon. Remove all the hardware telemetry columns that will never be populated.

---

### 4. Automation Self-Healing Rules (AutomationView)
**Why it's wrong-fit:** The "Self-Healing Rules" panel has toggles for auto-restart on TPS drop, GC threshold %, GrimAC strict mode on raid detection. These are local state only and have no backend effect. The backend scheduler can be configured but not via these specific shortcuts.

**Recommendation:** Remove or defer. If kept, wire to the actual automation.schedule API. Don't show toggles that do nothing.

---

### 5. Discord Slash Command Management Table
**Why it's wrong-fit:** The slash commands tab shows a table of commands with enable/disable toggles and usage counts. There is no backend API for this — slash commands are registered at bot startup via the py-cord bot's cog system and aren't dynamically manageable via REST. This is an operator concern, not a runtime dashboard concern for a single-server network.

**Recommendation:** Cut it. Show bot status and maybe a list of registered commands as read-only reference, but not editable.

---

## Section 3 — Useful Backend Features Not Exposed in Dashboard

The backend has substantial functionality the dashboard ignores entirely.

| Feature | Backend endpoint/capability | Why it's useful |
|---|---|---|
| **Replay sessions** | `GET/POST /api/v1/replay/sessions`, `POST .../events` | Review what a player was doing before a ban; anticheat evidence gathering. Very useful for a moderation-focused network. |
| **Operational intelligence — crash risk** | `operational_intelligence.crash_risk.assess` via capabilities | Predictive TPS degradation warning before a server crashes. Directly actionable for a small team. |
| **NL operational query** | `operational_intelligence.nl_query.answer` | "How many players were online yesterday at 8pm" style queries answered by the AI layer. Genuinely useful, already built. |
| **Security events** | `GET /api/v1/security/events` | WAF hits, rate-limit breaches, anomalous request patterns recorded by Phase 9 threat detection. Good for knowing if someone is probing the API. |
| **Bridge message history** | `GET /api/v1/bridge/messages` | The Discord↔MC chat bridge already stores messages. The Discord view ignores this and uses hardcoded seeds — real message history is sitting in the DB unused. |
| **Bridge settings** | `GET/PATCH /api/v1/bridge/settings` | Toggle MC→Discord and Discord→MC bridge modes, show avatars, set channel ID — all from the dashboard. Wired and ready. |
| **Alt detection — check** | `POST /api/v1/alts/check` | Manual alt check for a specific player UUID/IP on demand, triggered from the player detail view. Useful for moderation workflow. |
| **Player risk scores** | `risk_score` and `suspicion_score` already in `GET /api/v1/players` | These are real backend fields already returned. The dashboard adapter maps them but the Players view UI doesn't prominently surface the risk score as an actionable ranking. |
| **Post-mortem drafting** | `operational_intelligence.postmortem.draft` | AI-generated incident post-mortem from server data. The dashboard has a button for this that currently calls a local simulation; the real capability exists. |
| **API key management** | `capabilities/identity.py` — `identity.api_key.*` | Real API key creation/revocation via the capabilities router. Dashboard has the UI but calls wrong REST paths. |
| **Webhook management** | `capabilities/webhooks.py` — `webhooks.subscription.*` | Real webhook CRUD via capabilities router. Dashboard has the UI but calls wrong REST paths. |
| **Anticheat violation history** | Backend stores Grim flags in the DB via `anticheat_service.handle_cheat_flag` | There's no GET endpoint to query stored flags. This data is being written but never surfaced to the dashboard. A simple `GET /api/v1/anticheat/violations` would make the Moderation view's GrimAC tab functional. |

---

## Section 4 — AI Capabilities Reality Check

### What the backend AI system actually has

The backend has a real, production-grade AI layer:
- **Three concrete providers:** Anthropic (`anthropic_provider.py`), Gemini (`gemini_provider.py`), OpenRouter (`openrouter_provider.py`).
- **Model router** (`services/ai/model_router.py`): DB-backed health tracking, consecutive-failure counting, half-open cooldown retry, priority ordering.
- **Orchestrator** (`services/ai/orchestrator.py`): Optional dual-review (two models must agree or escalate), constitution/system-prompt injection, decision logging to `AIDecisionLog`.
- **Capabilities that call it:** `moderation_intelligence` (player review, appeal analysis), `operational_intelligence` (crash risk, NL query, post-mortem), `investigation` (player investigation).

### What the dashboard's AI view assumes exists that doesn't

1. `POST /api/v1/ai/providers/test` — endpoint to test a provider API key live. **Doesn't exist.**
2. `GET /api/v1/ai/tasks` — ✅ exists, but the dashboard expects `taskType: 'CRASH_TRIAGE' | 'ANOMALY_CHECK'` in the response. The backend only produces `player_review` and `appeal_review` task types.
3. `POST /api/v1/ai/diagnostics/crash` — crash triage endpoint. **Doesn't exist** as a REST route. The crash prevention logic is in `operational_intelligence.crash_risk.assess` via capabilities.
4. `GET /api/v1/diagnostics/crashes` — crash report list endpoint. **Doesn't exist** at all.
5. The 6-provider dashboard config (Ollama local, DeepSeek, OpenAI) — the backend has 3 real providers. The other 3 from the spec doc are aspirational.

### Gap between spec doc and reality

`docs/AI_DIAGNOSTICS_CAPABILITIES.md` describes:
- `POST /api/v1/ai/triage` — not built at this path
- `POST /api/v1/ai/grim-analysis` — not built
- `POST /api/v1/ai/translate` — not built (translation uses a different path/mechanism)
- `POST /api/v1/ai/tps-forecast` — not built
- 6 providers — only 3 exist

The spec doc is aspirational, not descriptive of current state. It was likely written as a requirements document, not a what's-built document.

### What's realistic to build vs. aspirational

**Realistic now (backend structure exists):**
- `POST /api/v1/ai/providers/test` — a thin wrapper around `ProviderFactory.get_provider(name).generate(test_prompt)` with a latency timer.
- Crash risk surface — `GET /api/v1/ai/crash-risk/{server_id}` wrapping the existing `operational_intelligence.crash_risk.assess` capability.
- Real copilot chat — route the dashboard's chat prompt through `orchestrator.run()` and return the result.

**Aspirational:**
- GrimAC pattern analysis (true confidence scoring, 60s telemetry windows).
- Autonomous TPS self-healing (sending commands back to the server).
- 6-provider parity (OpenAI, DeepSeek, Ollama need providers built).

---

## Section 5 — Discord Features Reality Check

### Dashboard Discord view vs. real bot cogs

The bot has 11 cogs (from project history). Crossreferencing against the Discord view tabs:

| Dashboard tab | Real bot cog | Status |
|---|---|---|
| Chat Bridge (send/receive MC↔Discord) | Bridge cog (uses `/api/v1/bridge/message`) | ✅ Real — bridge is wired. The tab shows hardcoded seeds though, not live. |
| Embed Builder | No cog — embeds sent ad-hoc via dashboard | ⚠️ The send button calls `/api/v1/discord/embed` which doesn't exist |
| Slash Commands | Slash command cogs (registered at startup) | ❌ No runtime management API; the table is purely cosmetic |
| Webhooks config | No Discord-specific webhook cog | ⚠️ Uses the general webhook system — not Discord-specific |
| Bot Status | Relies on the bot reporting health | ❌ No bot health endpoint in core; the status panel is hardcoded |

### What the bot does that the dashboard doesn't expose

From the Discord bot's known cog structure:
- **Verification cog** — manages the Discord↔MC link flow via bot commands. The dashboard has a Verification page but it's disconnected from bridge history.
- **Moderation cog** — ban/mute commands via Discord. The dashboard's moderation and the bot's moderation are separate — double-issuing punishments is possible.
- **Staff commands** — promote/demote via Discord. Again, no sync signal to the dashboard.

---

## Section 6 — Schema Mismatches

Specific, concrete mismatches between what the dashboard calls and what the backend returns or expects:

| # | Dashboard call | Backend reality | Impact |
|---|---|---|---|
| 1 | `PATCH /api/v1/punishments/{id}/revoke` with body `{reason}` | Backend route is `POST /api/v1/punishments/{id}/revoke` | 405 Method Not Allowed on pardon |
| 2 | `PATCH /api/v1/feature-flags/{name}` with `{enabled}` | Backend has `POST /api/v1/feature-flags` (upsert) — no PATCH | 405 on feature flag toggle |
| 3 | `api.approveAITask(taskId)` sends no body | Backend `POST /api/v1/ai/tasks/{id}/approve` requires `{action_taken: str, reviewed_by: str}` | 422 Unprocessable Entity |
| 4 | `POST /api/v1/translation/translate` with `{text, targetLang}` | Backend expects `{text, target_language, player_uuid?}` | 422 — field name mismatch (`targetLang` vs `target_language`) |
| 5 | `BackendAppeal` type: expects `playerUsername`, `type`, `originalReason`, `appealReason`, `aiSentimentScore`, `aiRecommendedAction`, `aiAnalysisSummary`, `assignedStaff` | Backend `AppealSchema` returns only `id`, `punishment_id`, `player_uuid`, `status`, `message`, `created_at` | All appeal enrichment fields are missing; adapter defaults used |
| 6 | `GET /api/v1/players/lookup?query=` | No such route — players router has only `GET /` and `GET /{uuid}` | 404 — falls back to fabricated random UUID (silent bug) |
| 7 | `BackendServer` type: `ramUsedMb`, `ramTotalMb`, `cpu` | Backend dashboard/servers route hardcodes these to `0` | Permanently zero RAM/CPU display |
| 8 | `GET /api/v1/staff` | No GET list route — only `POST /manage`, `POST /add`, `GET /discord-members` | 404 — staff list always empty |
| 9 | `GET /api/v1/snapshots` (list all) | No such route — backend has by-player and by-id only | 404 — snapshot list never loads |
| 10 | `POST /api/v1/snapshots` with `{server_id, type, tags}` | Backend expects `{minecraft_uuid, trigger, health, food, ...}` (player state fields) | 422 — completely different schema |
| 11 | `POST /api/v1/auth/discord/callback` with `{code, state}` via POST from dashboard | Backend `POST /discord/callback` takes same shape but `code` and `state` — ✅ this one is fine | OK |
| 12 | `PlayerSchema` (backend) has no `online` field | `adaptBackendPlayer` sets `online: Boolean(raw.online)` → always false | All players show as offline |
| 13 | `PATCH /api/v1/appeals/{id}` with `{status, staff_note}` | Backend `AppealUpdateRequest` only accepts `{status}` | `staff_note` silently dropped |

---

## Section 7 — Priority Ranking

### 🔴 Blockers — Fix before first real use

1. **`PATCH` → `POST` for punishment revoke** (`/api/v1/punishments/{id}/revoke`) — pardoning punishments is a core moderation action. Method mismatch makes it always fail.
2. **`PATCH` → `POST/upsert` for feature flag toggle** — the Settings page feature flag panel will 405 on every toggle.
3. **`approveAITask` missing required body** — AI task approval sends no body, gets 422. Add `{action_taken, reviewed_by}` to the call.
4. **Player lookup fallback uses `Math.random()` UUID** — when a lookup fails, the catch block fabricates a UUID. If this UUID gets passed to moderation actions, it silently bans nobody. Remove the fake-UUID fallback, show an error.
5. **`GET /api/v1/staff` 404** — staff list never loads. Wire to `GET /api/v1/auth/users` or add a list route to the staff router.
6. **Translation param name mismatch** (`targetLang` vs `target_language`) — test scratchpad always fails validation.

### 🟡 High-value — Significantly better with these

7. **Surface real bridge message history** — the backend stores all MC↔Discord messages at `GET /api/v1/bridge/messages`. Replace the seeded hardcoded chat feed in the Discord view with real data.
8. **Add `GET /api/v1/anticheat/violations`** — the GrimAC flag data is being written to the DB on every flag from the plugin. There's no read endpoint. One route would make the GrimAC tab in Moderation functional.
9. **Snapshots page redesign** — replace the world-checkpoint concept with what's actually built: player state snapshots. Show a player's inventory/position history. Or defer the page entirely.
10. **Replace copilot chat simulation with real AI call** — the orchestrator exists and has three real providers. Route the copilot prompt through it. This is the most impactful UX improvement and requires minimal new backend code (one endpoint wrapping `orchestrator.run()`).
11. **Wire real webhook/API key management** — both systems exist behind the capabilities router. Add thin REST facades (e.g. `GET /api/v1/webhooks` → delegate to `webhooks.subscription.list`), or update dashboard to call the capabilities invoke endpoint.
12. **Expose crash risk via REST** — `operational_intelligence.crash_risk.assess` is built. Add `GET /api/v1/ai/crash-risk/{server_id}` wrapping it, and connect the AI page's crash section to it.

### 🟢 Nice-to-have — Lower priority

13. **Surface `GET /api/v1/bridge/settings`** — show and edit bridge mode (MC→Discord, Discord→MC, show avatars, channel ID) from the Discord settings section.
14. **Add `GET /api/v1/verification/links`** — so the Verification page shows real account pairs instead of hardcoded seeds.
15. **Surface replay sessions** — the replay system is fully built. A "Player Replay" tab in the moderation or player detail view would be useful for evidence gathering.
16. **Surface `GET /api/v1/security/events`** — WAF hits and threat detection signals, useful for the admin.
17. **Fix `source` field in bridge message POST** — dashboard calls `broadcastGlobalMessage()` without the required `source` field. Add it.
18. **Topology simplification** — replace the hardware telemetry node view with a real node list from `hosting.node.list`. Remove columns you can never populate.

### ⛔ Cut or defer

19. **AI 6-provider config matrix** — remove the client-side provider config panel with failover simulation. The backend has a real model config system; consider a simple "AI status" panel showing what models are active, read from the DB.
20. **Slash command management table** — py-cord registers commands at startup; they're not runtime-manageable via REST. Remove the tab. Show a static reference list if needed.
21. **Automation self-healing rules** (TPS auto-restart toggle, GC threshold) — local state with no backend effect. Remove until wired to the real scheduler.
22. **Bot status panel** — no backend supports it. Either build a bot health check endpoint in core, or remove the tab.
23. **Crash dump list and `POST /api/v1/diagnostics/crashes`** — there's no crash storage system. Either build one or remove the page section.

---

## Summary

The dashboard is well-structured and covers the right problem space. The auth flow, server health display, punishment list, appeals, and audit/logs are the strongest sections — they're either fully functional or one small fix away. The biggest systemic issues are:

1. **~8 endpoints the dashboard calls simply don't exist** at the paths it calls them — they need either new routes or updated frontend calls.
2. **The AI Intelligence and Snapshots pages are built on wrong assumptions** — the copilot is a local simulation and the snapshot model is a concept mismatch.
3. **Several fields the dashboard displays (RAM/CPU, player online status, appeal enrichment) will always be empty** because the backend doesn't return them in the relevant schemas.
4. **The capabilities router system** (which manages webhooks, API keys, automation, nodes, marketplace) is largely invisible to the dashboard — it calls non-existent simple REST paths instead.

None of this is catastrophic. Most of the data flows are the right shape and in the right places; the issues are surgical endpoint mismatches and a few concept gaps, not architectural problems.

---

*Sub-chat handback. This document is read-only output — no changes were made to the repo.*
