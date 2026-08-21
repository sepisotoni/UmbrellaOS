# PHASE14-AUDIT.md

**Read-only deep audit. No code changes were made. All findings are from source inspection only.**

Audited: `umbrella-dashboard-CURRENT/` (all files) and `umbrella-core-CURRENT/api/routers/` (all 29 router files) plus `main.py`, `registry/adapters/rest.py`, and capability file listing.

---

## 1. Every API Call the Dashboard Makes

### 1.1 Direct REST calls (`backend.get` / `backend.post`)

These bypass the capability registry and call raw router endpoints.

| Method | Path | Request Body | Expected Response | Source file |
|--------|------|--------------|-------------------|-------------|
| `GET` | `/api/v1/auth/me` | — | `UserSchema` (`id`, `discord_id`, `username`, `email`, `role_id`, `role`, `permissions[]`, `is_active`, `created_at`, `updated_at`) | `lib/session.ts` |
| `POST` | `/api/v1/auth/discord/authorize` | `{ redirect_uri: string }` | `{ authorize_url: string, state: string }` | `app/api/auth/start/route.ts` |
| `POST` | `/api/v1/auth/discord/callback` | `{ code: string, state: string, redirect_uri: string }` | `{ token: string, user: UserSchema, expires_in: number }` | `app/api/auth/callback/route.ts` |
| `POST` | `/api/v1/auth/logout?session_token=<token>` | `{}` | `{ success: boolean, message: string }` | `app/api/auth/logout/route.ts` |
| `GET` | `/api/v1/players?username=<q>&limit=8` | — | `Array<{ uuid: string, username: string }>` | `lib/search.ts` (players source) |

### 1.2 Capability invocations (`POST /api/v1/capabilities/{name}/invoke`)

All go through the single generic invoke route. Listed by capability name:

#### Auth / Session
| Capability | Params sent | Expected result | Source |
|-----------|-------------|-----------------|--------|
| *(none — auth uses direct routes only)* | | | |

#### Marketplace
| Capability | Params sent | Expected result | Source |
|-----------|-------------|-----------------|--------|
| `marketplace.install.dashboard_slots` | `{ slot: "sidebar.tools" \| "sidebar.moderation" \| "dashboard.widgets" }` | `DashboardSlot[]` — each with `{ plugin_id, slot, label, capability_name, render_as }` | `lib/widgets.ts::fetchSlots` |
| `marketplace.listing.list` | `{}` | `PluginListing[]` — `{ plugin_id, name, author, description, latest_version }` | `lib/marketplace-listings.ts`, `lib/search.ts` |
| `marketplace.listing.versions` | `{ plugin_id: string }` | `PluginVersion[]` — `{ plugin_id, version, sha256_hash, published_at }` | `lib/marketplace-listings.ts::fetchPluginVersions` |
| `marketplace.install.list` | `{}` | `PluginInstall[]` — `{ plugin_id, installed_version, registered_capability_names[] }` | `lib/marketplace-listings.ts`, `lib/topology.ts` |
| `marketplace.install.install` | `{ plugin_id: string, version: string }` | `PluginInstall` | `lib/marketplace-listings.ts::installPlugin` |
| `marketplace.install.uninstall` | `{ plugin_id: string }` | `{ uninstalled: boolean }` | `lib/marketplace-listings.ts::uninstallPlugin` |
| `marketplace.install.pages` | `{}` | `PageNav[]` — `{ plugin_id, nav_label, nav_icon }` | `lib/marketplace-pages.ts::fetchPluginNavEntries` |
| `marketplace.install.page_layout` | `{ plugin_id: string }` | `PageLayout` — `{ plugin_id, nav_label, nav_icon, widgets: PageWidget[] }` | `lib/marketplace-pages.ts::fetchPageLayout` |
| `marketplace.install.configurable_plugins` | `{}` | `ConfigurablePlugin[]` — `{ plugin_id, plugin_name, field_count }` | `lib/plugin-config.ts::fetchConfigurablePlugins` |
| `marketplace.install.dashboard_slots` | `{ slot }` | *(see above)* | *(used by multiple)* |

#### Dashboard Layout
| Capability | Params sent | Expected result | Source |
|-----------|-------------|-----------------|--------|
| `dashboard.layout.get` | `{ page_id: string }` | `DashboardLayoutResult` — `{ page_id, widgets: LayoutWidgetEntry[] \| null }` | `lib/dashboard-layout.ts::fetchLayout` |
| `dashboard.layout.set` | `{ page_id: string, widgets: LayoutWidgetEntry[] }` | *(any — result ignored)* | `lib/dashboard-layout.ts::saveLayout` |
| `dashboard.layout.reset` | `{ page_id: string }` | *(any — result ignored)* | `lib/dashboard-layout.ts::resetLayout` |

#### Hosting / Fleet
| Capability | Params sent | Expected result | Source |
|-----------|-------------|-----------------|--------|
| `hosting.node.list` | `{}` | `HostingNode[]` — `{ id, name, daemon_url, status, labels }` | `lib/fleet.ts`, `lib/topology.ts` |
| `hosting.server.list` | `{}` | `HostingServer[]` — `{ id, name, node_id, template_id, template_version, status, memory_bytes, cpu_cores }` | `lib/fleet.ts`, `lib/topology.ts` |
| `hosting.server.stats` | `{ server_id: string }` | `ServerStats` — `{ timestamp, cpu_percent, memory_used_bytes, memory_limit_bytes, network_rx_bytes, network_tx_bytes }` | `lib/fleet.ts::fetchServerStats` |

#### Platform / System
| Capability | Params sent | Expected result | Source |
|-----------|-------------|-----------------|--------|
| `platform.audit.search` | `{ limit, offset, actor_type \| null, action \| null }` | `AuditSearchResult` — `{ entries: AuditEntry[], total, limit, offset }` | `lib/activity.ts::fetchAuditLog` |

#### Observability / Logs
| Capability | Params sent | Expected result | Source |
|-----------|-------------|-----------------|--------|
| `platform.observability.search_logs` | `{ query, limit: 5 }` | `{ entries: Array<{ id, level, logger_name, message }> }` | `lib/search.ts` (logs source) |

#### Knowledge
| Capability | Params sent | Expected result | Source |
|-----------|-------------|-----------------|--------|
| `knowledge.entry.search` | `{ query: string, limit: 5 }` | `{ entries: Array<{ id, channel_name, content }> }` | `lib/search.ts` (knowledge source) |

#### Plugin Sandbox
| Capability | Params sent | Expected result | Source |
|-----------|-------------|-----------------|--------|
| `plugin.sandbox.execution_history` | `{ limit, offset, plugin_id?, outcome? }` | `PluginExecutionHistoryResult` — `{ entries: PluginExecutionEntry[], total, limit, offset }` | `lib/plugin-sandbox.ts::fetchExecutionHistory` |
| `plugin.sandbox.execution_detail` | `{ execution_id: string }` | `PluginExecutionDetail` — extends `PluginExecutionEntry` + `error_detail` | `lib/plugin-sandbox.ts::fetchExecutionDetail` |
| `plugin.sandbox.profile` | `{ window_hours: number, plugin_id? }` | `PluginExecutionProfile[]` — `{ plugin_id, execution_count, avg_wall_time_ms, p95_wall_time_ms, avg_peak_memory_bytes, error_rate, window_hours }` | `lib/plugin-sandbox.ts::fetchProfile` |
| `plugin.sandbox.limits` | `{}` | `PluginSandboxLimits` — `{ cpu_seconds, memory_bytes, wall_timeout_seconds }` | `lib/plugin-sandbox.ts::fetchSandboxLimits` |

#### Per-plugin Dynamic Capabilities
| Capability pattern | Params sent | Expected result | Source |
|-------------------|-------------|-----------------|--------|
| `plugin.<plugin_id>.config.get` | `{}` | `ConfigGetResult` — `{ values: ConfigFieldValue[] }` where each is `{ key, label, type: "boolean", value: boolean }` | `lib/plugin-config.ts::fetchPluginConfigValues` |
| `plugin.<plugin_id>.config.set` | `{ key: string, value: boolean }` | *(any — result ignored)* | `lib/plugin-config.ts::setPluginConfigValue` |
| `<any capability_name>` | `{}` | `WidgetData` (`Record<string,unknown>` or `unknown[]`) | `lib/widgets.ts::fetchWidgetData` |

### 1.3 Same-origin API routes (browser → Next.js → core)

These are the Next.js route handlers the browser calls. They forward to core internally.

| Method | Next.js path | Body / Query | Forwards to core | Source |
|--------|-------------|--------------|-----------------|--------|
| `GET` | `/api/auth/start?next=<path>` | — | `POST /api/v1/auth/discord/authorize` | `app/api/auth/start/route.ts` |
| `GET` | `/api/auth/callback?code&state` | — | `POST /api/v1/auth/discord/callback` | `app/api/auth/callback/route.ts` |
| `POST` | `/api/auth/logout` | — | `POST /api/v1/auth/logout?session_token=...` | `app/api/auth/logout/route.ts` |
| `GET` | `/api/search?q=<query>` | — | Federated: `GET /api/v1/players`, + multiple capability invocations | `app/api/search/route.ts` |
| `POST` | `/api/dashboard-layout` | `{ page_id, widgets: LayoutWidgetEntry[] }` | `dashboard.layout.set` capability | `app/api/dashboard-layout/route.ts` |
| `DELETE` | `/api/dashboard-layout?page_id=<id>` | — | `dashboard.layout.reset` capability | `app/api/dashboard-layout/route.ts` |
| `POST` | `/api/marketplace-install` | `{ plugin_id, version }` | `marketplace.install.install` capability | `app/api/marketplace-install/route.ts` |
| `DELETE` | `/api/marketplace-install?plugin_id=<id>` | — | `marketplace.install.uninstall` capability | `app/api/marketplace-install/route.ts` |
| `POST` | `/api/plugin-config` | `{ plugin_id, key, value: boolean }` | `plugin.<id>.config.set` capability | `app/api/plugin-config/route.ts` |

---

## 2. Every Route the Core Exposes

### 2.1 `GET /health` — Health Router
Returns: `{ status, version, database, redis, service }`

### 2.2 `GET /metrics` — Metrics Router
Returns: Prometheus exposition text. Auth: admin key or session.

### 2.3 Auth Router (`/api/v1/auth`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `GET` | `/api/v1/auth` | `roles.manage` OR `players.view` | `UserSchema[]` |
| `GET` | `/api/v1/auth/users/{user_id}` | Admin key | `UserSchema` |
| `POST` | `/api/v1/auth/users` | Admin key | `UserSchema` (201) |
| `PATCH` | `/api/v1/auth/users/{user_id}` | Admin key | `UserSchema` |
| `DELETE` | `/api/v1/auth/users/{user_id}` | Admin key | 204 |
| `POST` | `/api/v1/auth/discord/authorize` | None | `{ authorize_url, state }` |
| `POST` | `/api/v1/auth/discord/callback` | None | `{ token, user: UserSchema, expires_in }` |
| `POST` | `/api/v1/auth/logout?session_token=` | None (token in query) | `{ success, message }` |
| `GET` | `/api/v1/auth/me` | Bearer session or `?session_token=` | `UserSchema` |

### 2.4 Settings Router (`/api/v1/settings`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `GET` | `/api/v1/settings` | Owner | `list[dict]` |
| `GET` | `/api/v1/settings/{key}` | Owner | `dict` |
| `PATCH` | `/api/v1/settings/{key}` | Owner | `dict` |

### 2.5 Roles Router (`/api/v1/roles`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `GET` | `/api/v1/roles` | `roles.manage` OR `players.view` | `list[dict]` |
| `GET` | `/api/v1/roles/permissions` | `roles.manage` OR `players.view` | `list[dict]` |

### 2.6 Audit Router (`/api/v1/audit`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `GET` | `/api/v1/audit` | `audit.view` | `dict` (delegates to `platform.audit.search`) |
| `GET` | `/api/v1/audit/{action}` | `audit.view` | `dict` + `action` field |

### 2.7 Plugin Router (`/api/v1/plugin`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `GET` | `/api/v1/plugin/health` | Plugin key | `{ status, version, database, service, client }` |
| `POST` | `/api/v1/plugin/heartbeat` | Plugin key | `{ ok, server_id }` |
| `GET` | `/api/v1/plugin/config` | Plugin key | `{ settings: dict, by_category: dict }` |
| `GET` | `/api/v1/plugin/punishments/{player_uuid}/active` | Plugin key | `{ banned: bool, punishment?: ActivePunishmentSchema }` |
| `POST` | `/api/v1/plugin/control` | Plugin key | `{ ok, command_id }` |

### 2.8 Players Router (`/api/v1/players`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `GET` | `/api/v1/players` | `players.view` | `PlayerSchema[]` (supports `?username=&skip=&limit=`) |
| `GET` | `/api/v1/players/{uuid}` | `players.view` | `PlayerDetailSchema` |

### 2.9 Punishments Router (`/api/v1/punishments`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `GET` | `/api/v1/punishments` | `punishments.view` | `PunishmentSchema[]` |
| `POST` | `/api/v1/punishments` | `punishments.create` | `PunishmentSchema` (201) |
| `PATCH` | `/api/v1/punishments/{id}` | `punishments.create` | `PunishmentSchema` |
| `POST` | `/api/v1/punishments/{id}/revoke` | `punishments.revoke` | `PunishmentSchema` |

### 2.10 Appeals Router (`/api/v1/appeals`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `GET` | `/api/v1/appeals` | `appeals.view` | `AppealSchema[]` |
| `POST` | `/api/v1/appeals` | None | `AppealSchema` (201) |
| `PATCH` | `/api/v1/appeals/{id}` | `appeals.manage` | `AppealSchema` |

### 2.11 Moderation Router (`/api/v1/moderation`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/moderation/kick` | `moderation.kick` | `{ success, player_uuid, action, reason }` |
| `POST` | `/api/v1/moderation/warn` | `moderation.warn` | `ModerationResponseSchema` (201) |
| `POST` | `/api/v1/moderation/ban` | `moderation.ban` | `ModerationResponseSchema` (201) |
| `POST` | `/api/v1/moderation/unban` | `moderation.ban` | `ModerationResponseSchema` |
| `POST` | `/api/v1/moderation/ipban` | `moderation.ipban` | `{ success, ip_address, reason, punishment_id }` (201) |
| `POST` | `/api/v1/moderation/ipunban` | `moderation.ipban` | `{ success, ip_address, action }` |
| `GET` | `/api/v1/moderation/active/{player_uuid}` | `punishments.view` | `ModerationResponseSchema[]` |

### 2.12 Bridge Router (`/api/v1/bridge`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/bridge/message` | Admin key | `BridgeMessageResponse` |
| `GET` | `/api/v1/bridge/messages` | `players.view` | `ChatMessageSchema[]` |
| `GET` | `/api/v1/bridge/settings` | `settings.view` | `BridgeSettingsResponse` |
| `PATCH` | `/api/v1/bridge/settings` | `settings.manage` | `BridgeSettingsResponse` |

### 2.13 Verification Router (`/api/v1/verification`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/verification/request` | Admin key | `VerificationRequestResponse` |
| `POST` | `/api/v1/verification/confirm` | Admin key | `VerificationConfirmResponse` |
| `POST` | `/api/v1/verification/status` | Admin key | `VerificationStatusResponse` |
| `GET` | `/api/v1/verification/pending` | `players.view` | `VerificationCodeSchema[]` |
| `POST` | `/api/v1/verification/revoke` | `players.manage` | `{ success: true }` |
| `POST` | `/api/v1/verification/manual-link` | Admin key | `{ success, message }` |
| `DELETE` | `/api/v1/verification/unlink/{discord_id}` | Admin key | `{ success: true }` |
| `POST` | `/api/v1/verification/resolve-pending` | Admin key | `{ resolved: bool, discord_id? }` |

### 2.14 Alt Detection Router (`/api/v1/alts`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/alts/check` | Admin key | `AltCheckResponse` |
| `GET` | `/api/v1/alts/flagged` | `players.view` | `FlaggedPlayerSchema[]` |
| `GET` | `/api/v1/alts/player/{uuid}` | `players.view` | `{ score, events, alt_groups }` |
| `POST` | `/api/v1/alts/false-positive` | `players.manage` | `{ success: true }` |
| `POST` | `/api/v1/alts/group` | `players.manage` | `AltGroupSchema` |
| `GET` | `/api/v1/alts/groups` | `players.view` | `AltGroupSchema[]` |

### 2.15 Analytics Router (`/api/v1/analytics`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/analytics/events` | Admin key | `AnalyticsEventResponse` (201) |
| `GET` | `/api/v1/analytics/events` | `players.view` | Event list |
| `GET` | `/api/v1/analytics/players/{uuid}` | `players.view` | Player stats |
| `GET` | `/api/v1/analytics/summary` | `players.view` | Server-wide totals |

### 2.16 Replay Router (`/api/v1/replay`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/replay/sessions` | Admin key | Session dict (201) |
| `GET` | `/api/v1/replay/sessions` | `players.view` | Session list |
| `GET` | `/api/v1/replay/sessions/{id}` | `players.view` | Session dict |
| `POST` | `/api/v1/replay/sessions/{id}/events` | Admin key | `{ inserted: int }` |
| `POST` | `/api/v1/replay/sessions/{id}/finalize` | Admin key | Session dict |
| `GET` | `/api/v1/replay/sessions/{id}/events` | `players.view` | Event list |

### 2.17 Snapshot Router (`/api/v1/snapshots`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/snapshots` | Admin key | Snapshot dict (201) |
| `GET` | `/api/v1/snapshots/players/{uuid}` | `players.view` | Snapshot list |
| `GET` | `/api/v1/snapshots/players/{uuid}/latest` | `players.view` | Snapshot dict |
| `GET` | `/api/v1/snapshots/{id}` | `players.view` | Snapshot dict |
| `GET` | `/api/v1/snapshots/replay/{replay_id}` | `players.view` | Snapshot list |

### 2.18 MC Commands Router (`/api/v1/mc`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/mc/command` | Admin key | `MCCommandResponse` (201) |
| `GET` | `/api/v1/mc/commands/pending` | Plugin key | `MCCommandResponse[]` |
| `POST` | `/api/v1/mc/commands/{id}/complete` | Plugin key | `{ status: "ok", message }` |

### 2.19 Translation Router (`/api/v1/translation`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/translation/language` | Admin key | `PlayerLanguageResponse` |
| `GET` | `/api/v1/translation/language/all` | `players.view` | `PlayerLanguageResponse[]` |
| `GET` | `/api/v1/translation/language/{uuid}` | `players.view` | `PlayerLanguageResponse` |
| `POST` | `/api/v1/translation/translate` | Admin key | `TranslateResponse` |

### 2.20 AI Config Router (`/api/v1/ai/config`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/ai/config/request` | `settings.manage` | `AIConfigResponse` |
| `GET` | `/api/v1/ai/config/pending` | `settings.manage` | `AIConfigResponse[]` |
| `POST` | `/api/v1/ai/config/{id}/approve` | `settings.manage` | `AIConfigResponse` |
| `POST` | `/api/v1/ai/config/{id}/reject` | `settings.manage` | `AIConfigResponse` |

### 2.21 AI Tasks Router (`/api/v1/ai`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/ai/review/player/{uuid}` | Admin key | AITask dict (201) |
| `POST` | `/api/v1/ai/review/appeal/{id}` | Admin key | AITask dict (201) |
| `GET` | `/api/v1/ai/tasks` | `punishments.view` | AITask list |
| `GET` | `/api/v1/ai/tasks/{id}` | `punishments.view` | AITask dict |
| `POST` | `/api/v1/ai/tasks/{id}/approve` | `punishments.create` | AITask dict |
| `POST` | `/api/v1/ai/tasks/{id}/deny` | `punishments.create` | AITask dict |

### 2.22 Anticheat Router (`/api/v1/anticheat`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/anticheat/flag` | Plugin key | `{ ... }` |

### 2.23 Dashboard Router (`/api/v1/dashboard`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `GET` | `/api/v1/dashboard/servers` | `players.view` | `list[dict]` — server status from heartbeat table |
| `GET` | `/api/v1/dashboard/plugins` | `players.view` | `list[dict]` — plugin status from heartbeat table |

### 2.24 Server Control Router (`/api/v1/server`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/server/control` | `server.control` | `dict` |

### 2.25 Staff Router (`/api/v1/staff`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `POST` | `/api/v1/staff/manage` | `roles.manage` | `StaffManageResponse` |
| `POST` | `/api/v1/staff/add` | `roles.manage` | `StaffManageResponse` |
| `GET` | `/api/v1/staff/discord-members` | `roles.manage` | `list[dict]` |

### 2.26 Logs Router (`/api/v1/logs`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `GET` | `/api/v1/logs` | `observability.logs.view` | `dict` (delegates to `platform.observability.search_logs`) |

### 2.27 Security Router (`/api/v1/security`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `GET` | `/api/v1/security/events` | `security.events.view` | `dict` (delegates to `platform.security.list_events`) |

### 2.28 Feature Flags Router (`/api/v1/feature-flags`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `GET` | `/api/v1/feature-flags` | `feature_flags.view` | `FeatureFlagResponse[]` |
| `GET` | `/api/v1/feature-flags/{name}` | `feature_flags.view` | `FeatureFlagResponse` |
| `POST` | `/api/v1/feature-flags` | `feature_flags.manage` | `FeatureFlagResponse` |
| `DELETE` | `/api/v1/feature-flags/{name}` | `feature_flags.manage` | `{ deleted: true }` |

### 2.29 Capabilities REST Adapter (`/api/v1/capabilities`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `GET` | `/api/v1/capabilities` | None stated | `CapabilitySummary[]` |
| `POST` | `/api/v1/capabilities/{name}/invoke` | Session, admin key, or API key | Capability-specific |

### 2.30 Hosting Console WebSocket (`/api/v1/hosting`)

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| `WS` | `/api/v1/hosting/servers/{server_id}/console?token=` | Session token in query | WebSocket proxy to daemon |

---

## 3. Gap Table

**Legend:** Dashboard calls the capability invoke path (`POST /api/v1/capabilities/{name}/invoke`) for all of these unless noted as direct REST.

| Dashboard calls | Core has | Status |
|----------------|----------|--------|
| `GET /api/v1/auth/me` (direct REST) | `GET /api/v1/auth/me` | ✅ Match |
| `POST /api/v1/auth/discord/authorize` | `POST /api/v1/auth/discord/authorize` | ✅ Match |
| `POST /api/v1/auth/discord/callback` → returns `{ token, user, expires_in }` | Returns `DiscordOAuthCallbackResponse { token, user: UserSchema, expires_in }` | ✅ Match |
| `POST /api/v1/auth/logout?session_token=<token>` | `POST /api/v1/auth/logout` — **accepts `session_token` as a query param** | ✅ Match |
| `GET /api/v1/players?username=&limit=8` | `GET /api/v1/players?username=&limit=` | ✅ Match (uses `skip` not `offset`, but `skip=0` is the default) |
| Capability `marketplace.install.dashboard_slots` | Exists in `capabilities/marketplace.py` | ✅ Match (verified shape in STEP0 doc) |
| Capability `marketplace.listing.list` | Exists in `capabilities/marketplace.py` | ✅ Match |
| Capability `marketplace.listing.versions` | Exists in `capabilities/marketplace.py` | ✅ Match |
| Capability `marketplace.install.list` | Exists in `capabilities/marketplace.py` | ✅ Match |
| Capability `marketplace.install.install` | Exists in `capabilities/marketplace.py` | ✅ Match |
| Capability `marketplace.install.uninstall` | Exists in `capabilities/marketplace.py` | ✅ Match |
| Capability `marketplace.install.pages` | Exists in `capabilities/marketplace.py` | ✅ Match |
| Capability `marketplace.install.page_layout` | Exists in `capabilities/marketplace.py` | ✅ Match |
| Capability `marketplace.install.configurable_plugins` | Exists in `capabilities/marketplace.py` | ✅ Match |
| Capability `dashboard.layout.get` | Exists in `capabilities/dashboard_layout.py` | ✅ Match |
| Capability `dashboard.layout.set` | Exists in `capabilities/dashboard_layout.py` | ✅ Match |
| Capability `dashboard.layout.reset` | Exists in `capabilities/dashboard_layout.py` | ✅ Match |
| Capability `hosting.node.list` | Exists in `capabilities/hosting.py` | ✅ Match |
| Capability `hosting.server.list` | Exists in `capabilities/hosting.py` | ✅ Match |
| Capability `hosting.server.stats` | Exists in `capabilities/hosting.py` | ✅ Match |
| Capability `platform.audit.search` | Exists in `capabilities/system.py` | ✅ Match |
| Capability `platform.observability.search_logs` | Exists in `capabilities/observability.py` | ✅ Match |
| Capability `knowledge.entry.search` | Exists in `capabilities/knowledge.py` | ✅ Match |
| Capability `plugin.sandbox.execution_history` | Exists in `capabilities/plugin_sandbox.py` | ✅ Match |
| Capability `plugin.sandbox.execution_detail` | Exists in `capabilities/plugin_sandbox.py` | ✅ Match |
| Capability `plugin.sandbox.profile` | Exists in `capabilities/plugin_sandbox.py` | ✅ Match |
| Capability `plugin.sandbox.limits` | Exists in `capabilities/plugin_sandbox.py` | ✅ Match |
| Capability `plugin.<plugin_id>.config.get` | Registered dynamically by `services/plugins/registration.py` on install | ✅ Match |
| Capability `plugin.<plugin_id>.config.set` | Registered dynamically by `services/plugins/registration.py` on install | ✅ Match |
| Generic `<capability_name>` invocation for widget data | Any registered capability via `POST /api/v1/capabilities/{name}/invoke` | ✅ Match |
| Search `href: /players/${p.uuid}` | Route `/players/[uuid]` — no page exists in dashboard | ⚠️ Path mismatch: search results link to `/players/{uuid}` but dashboard has no `/players/` route. Only `GET /api/v1/players/{uuid}` exists on core, but no UI page to render it. |
| Search `href: /knowledge/${e.id}` | No `/knowledge/` route in dashboard, no knowledge viewer page | ❌ Missing from dashboard frontend: knowledge search result links go to a non-existent page |
| Search `href: /observability/logs?trace=${e.id}` | No `/observability/` route in dashboard | ❌ Missing from dashboard frontend: log search result links go to a non-existent page |
| `lib/session.ts::getSession` calls `GET /api/v1/auth/me` with `Bearer <token>` header | Core's `/auth/me` accepts `Authorization: Bearer <token>` | ✅ Match |
| `lib/dashboard-layout.ts` invokes `dashboard.layout.get` with `{ page_id }` | `capabilities/dashboard_layout.py` — shape exactly matches `DashboardLayoutResult` in `lib/types.ts` | ✅ Match |
| `lib/types.ts::User` has field `role: string \| null` | `UserSchema` in `api/routers/auth.py` has `role: str \| None = None` | ✅ Match |
| Dashboard expects `DashboardLayoutResult.widgets` to be `LayoutWidgetEntry[] \| null` | Core returns `null` for no saved layout | ✅ Match |
| Dashboard `lib/fleet.ts` expects `HostingServer.template_id` and `template_version` | `HostingServer` type in `lib/types.ts` — **these fields come from `capabilities/hosting.py` which this audit cannot directly verify (not a router file)** | ⚠️ Cannot verify without reading `capabilities/hosting.py` — flagged as unverified field dependency |
| `app/api/auth/logout/route.ts` sends `POST /api/v1/auth/logout?session_token=<token>` with empty body `{}` | Core's `/auth/logout` takes `session_token` as a query param, body is ignored | ✅ Match — but note: body `{}` is sent unnecessarily; harmless |

---

## 4. New Backend Work Required

### 4.1 Navigation / Page Routing (Frontend-only but backend-adjacent)

No new backend endpoints are **strictly** required to unblock Phase 14. However, the search system links to three pages that do not exist in the dashboard frontend.

### 4.2 AI Feature Area

The core exposes AI endpoints (`/api/v1/ai/*`, `/api/v1/ai/config/*`) that the dashboard **never calls**. These are real implemented features with no dashboard UI whatsoever.

**Missing endpoints that need dashboard wiring (not new backend work — backend already exists):**

| Feature | Backend endpoint | What the dashboard needs |
|---------|-----------------|--------------------------|
| AI Moderation tasks queue | `GET /api/v1/ai/tasks` | A `/ai-tasks` or `/moderation` page to show the queue |
| AI task review | `POST /api/v1/ai/tasks/{id}/approve`, `/deny` | Approve/deny buttons on the above page |
| AI player review trigger | `POST /api/v1/ai/review/player/{uuid}` | Action in player detail UI |
| AI appeal review trigger | `POST /api/v1/ai/review/appeal/{id}` | Action in appeals UI |
| AI config request | `POST /api/v1/ai/config/request` | NL config input UI |
| AI config approval | `POST /api/v1/ai/config/{id}/approve`, `/reject` | Pending config approval UI |

### 4.3 Moderation Feature Area

Core has a full moderation router (`/api/v1/moderation/`) and punishments router (`/api/v1/punishments/`). Dashboard has no moderation UI at all — no player detail page, no ban/kick/warn interface.

**Missing from dashboard (backend exists):**

| Feature | Backend endpoint | Missing dashboard component |
|---------|-----------------|----------------------------|
| Player list / search UI | `GET /api/v1/players?username=` | No `/players` page — search results link there but page is absent |
| Player detail UI | `GET /api/v1/players/{uuid}` | No `/players/[uuid]` page |
| Issue ban | `POST /api/v1/moderation/ban` | No moderation action UI |
| Issue kick | `POST /api/v1/moderation/kick` | No moderation action UI |
| Issue warn | `POST /api/v1/moderation/warn` | No moderation action UI |
| Unban | `POST /api/v1/moderation/unban` | No moderation action UI |
| View active punishments | `GET /api/v1/moderation/active/{uuid}`, `GET /api/v1/punishments` | No punishment list UI |
| Appeals queue | `GET /api/v1/appeals` | No appeals UI |
| Review appeal | `PATCH /api/v1/appeals/{id}` | No appeals UI |

### 4.4 Translation Feature Area

Core has a translation router (`/api/v1/translation/`). Dashboard makes no calls to it.

**Missing from dashboard (backend exists):**

| Feature | Backend endpoint | Missing dashboard component |
|---------|-----------------|----------------------------|
| View player language prefs | `GET /api/v1/translation/language/{uuid}` | No translation/language UI |
| All language preferences | `GET /api/v1/translation/language/all` | No list view |

### 4.5 Hosting / Server Control Feature Area

Core exposes `POST /api/v1/server/control` and the dashboard lists a Fleet overview. However:

**Missing from dashboard (backend exists):**

| Feature | Backend endpoint | Missing dashboard component |
|---------|-----------------|----------------------------|
| Server power/restart/maintenance control | `POST /api/v1/server/control` | Fleet page has no action buttons — read-only view only |
| Hosting WebSocket console | `WS /api/v1/hosting/servers/{id}/console?token=` | No console UI in dashboard |

### 4.6 Staff Management Feature Area

Core has `POST /api/v1/staff/manage`, `/staff/add`, `GET /api/v1/staff/discord-members`. Dashboard has no staff management UI.

**Missing from dashboard (backend exists):**

| Feature | Backend endpoint | Missing dashboard component |
|---------|-----------------|----------------------------|
| Staff roster and promote/demote | `POST /api/v1/staff/manage`, `/add`, `GET /api/v1/staff/discord-members` | No staff management page |
| User management | `GET /api/v1/auth`, CRUD on `/api/v1/auth/users/` | No user admin UI |

### 4.7 Analytics / Bridge Feature Area

**Missing from dashboard (backend exists):**

| Feature | Backend endpoint | Missing dashboard component |
|---------|-----------------|----------------------------|
| Chat bridge logs | `GET /api/v1/bridge/messages` | No bridge viewer |
| Bridge settings | `GET/PATCH /api/v1/bridge/settings` | No bridge config UI |
| Player analytics | `GET /api/v1/analytics/players/{uuid}`, `/summary` | No analytics UI |

### 4.8 Alt Detection / Security Feature Area

**Missing from dashboard (backend exists):**

| Feature | Backend endpoint | Missing dashboard component |
|---------|-----------------|----------------------------|
| Flagged players list | `GET /api/v1/alts/flagged` | No alt detection UI |
| Player suspicion detail | `GET /api/v1/alts/player/{uuid}` | No suspicion viewer |
| Mark false positive | `POST /api/v1/alts/false-positive` | No review UI |
| Security events | `GET /api/v1/security/events` | No security events page |

### 4.9 Observability / Logs Feature Area

Core exposes `GET /api/v1/logs` (delegates to `platform.observability.search_logs`). The search system already invokes this capability, but results link to `/observability/logs?trace=...` which doesn't exist.

**New backend work required — none.** The capability and router both exist. What's needed:

| Feature | Missing dashboard component |
|---------|----------------------------|
| Logs viewer page at `/observability/logs` | No page — search results link there but it doesn't exist |

### 4.10 Feature Flags Feature Area

Core has full CRUD on `/api/v1/feature-flags`. Dashboard has no feature flags management UI.

**Missing from dashboard (backend exists):**

| Feature | Backend endpoint | Missing dashboard component |
|---------|-----------------|----------------------------|
| Feature flag management | `GET/POST/DELETE /api/v1/feature-flags/*` | No feature flags UI |

### 4.11 Replay / Snapshot Feature Area

Core has full replay and snapshot endpoints. Dashboard has no replay/snapshot viewer.

**Missing from dashboard (backend exists):**

| Feature | Backend endpoint | Missing dashboard component |
|---------|-----------------|----------------------------|
| Replay viewer | `GET /api/v1/replay/sessions`, `/events` | No replay UI |
| Snapshot viewer | `GET /api/v1/snapshots/players/{uuid}` | No snapshot UI |

### 4.12 Truly Missing from Core (Capability Registry Gaps)

The following capabilities are referenced by the dashboard search system as **search sources with real hrefs**, but the linked destinations exist neither in the dashboard nor as obvious capability wrappers:

| Search source | Capability invoked | Links to | Gap |
|--------------|-------------------|----------|-----|
| `knowledge` | `knowledge.entry.search` ✅ | `/knowledge/{id}` | ❌ No `/knowledge/` page in dashboard; no knowledge entry viewer |
| `logs` | `platform.observability.search_logs` ✅ | `/observability/logs?trace={id}` | ❌ No `/observability/logs` page in dashboard |
| `players` | `GET /api/v1/players` (direct REST) ✅ | `/players/{uuid}` | ❌ No `/players/[uuid]` page in dashboard |

---

## 5. Frontend Wiring Fixes Required

### 5.1 Dead Links from the Search / Command Palette

**File:** `umbrella-dashboard-CURRENT/lib/search.ts`

Three of the four search sources produce `href` values that go to pages that don't exist in the dashboard:

| Source | Generated href | Issue |
|--------|---------------|-------|
| `players` | `/players/${p.uuid}` | No `/players/` route exists in `app/(dashboard)/`. The middleware in `middleware.ts` also doesn't protect this path. |
| `knowledge` | `/knowledge/${e.id}` | No `/knowledge/` route exists anywhere in the dashboard. |
| `logs` | `/observability/logs?trace=${e.id}` | No `/observability/` route exists anywhere in the dashboard. |

**Impact:** Clicking any player, knowledge, or log result in the command palette navigates to a Next.js 404 page.

**Fix options (head chat decision required):**
- Option A: Stub placeholder pages at those routes (preferred to stop 404s)
- Option B: Remove the broken sources from the search until pages exist
- Option C: Re-route player links to `/marketplace/` or a relevant existing page (wrong semantics)

### 5.2 Middleware Missing Protected Routes

**File:** `umbrella-dashboard-CURRENT/middleware.ts`

The middleware only guards three prefix patterns: `/dashboard/:path*`, `/marketplace/:path*`, `/topology/:path*`.

Missing from `PROTECTED_PREFIXES` (routes that do session-check in their page component but aren't bounced at the edge):
- `/activity` — does `redirect("/login")` in the page but no edge check
- `/fleet` — same
- `/settings` — same
- `/plugin-sandbox` — same

**Impact:** Users without cookies can attempt to load these pages; they get bounced from the server component (correct), but the edge-level redirect (faster UX on mobile/slow connections) is absent. Not a security issue — the server component always re-checks — but it means an extra round trip for unauthenticated visitors.

**Fix:** Add `/activity/:path*`, `/fleet/:path*`, `/settings/:path*`, `/plugin-sandbox/:path*` to the middleware matcher config.

### 5.3 Auth Logout Body

**File:** `umbrella-dashboard-CURRENT/app/api/auth/logout/route.ts`

The route sends `await backend.post('/api/v1/auth/logout?session_token=...', {})`. The backend's `logout` endpoint takes `session_token` as a query param only; the body `{}` is ignored. This works correctly but sends unnecessary JSON. Minor — no functional impact.

### 5.4 TypeScript Strict Mode Suppressed

**File:** `umbrella-dashboard-CURRENT/next.config.mjs`

```js
typescript: { ignoreBuildErrors: true }
```

This means type errors in the dashboard are silently ignored at build time. The type contracts in `lib/types.ts` cannot be enforced by CI. Any schema drift between core responses and the dashboard's assumed shapes will compile and deploy silently.

**Fix:** Remove `ignoreBuildErrors: true` and resolve all resulting type errors before Phase 14 lands. This is not optional if the dashboard is supposed to be production-grade.

### 5.5 Env Var Coverage

**File:** `umbrella-dashboard-CURRENT/.env.example`

Only two env vars are documented:
- `UMBRELLA_CORE_API_URL` — used in `lib/api.ts`
- `DASHBOARD_OAUTH_REDIRECT_URI` — used in auth start/callback routes

**Not documented but referenced implicitly:** No additional env vars were found. The dashboard intentionally has a minimal config surface — all auth secrets (Discord client ID/secret) live in umbrella-core's settings table, not the dashboard's env. This is by design and correct.

**No action required** on env vars unless a Phase 14 feature introduces new ones.

### 5.6 Schema Mismatches: `UserSchema` vs `lib/types.ts::User`

**Core:** `UserSchema` in `api/routers/auth.py`  
**Dashboard:** `User` in `lib/types.ts`

Comparing field-by-field:

| Field | Core `UserSchema` | Dashboard `User` | Status |
|-------|------------------|-----------------|--------|
| `id` | `str` | `string` | ✅ |
| `discord_id` | `str` | `string` | ✅ |
| `username` | `str` | `string` | ✅ |
| `email` | `str \| None` | `string \| null` | ✅ |
| `role_id` | `str \| None` | `string \| null` | ✅ |
| `role` | `str \| None = None` | `string \| null` | ✅ |
| `permissions` | `list[str] = []` | `string[]` | ✅ |
| `is_active` | `bool` | `boolean` | ✅ |
| `created_at` | `datetime` | `string` | ✅ (serialized to ISO string) |
| `updated_at` | `datetime` | `string` | ✅ |

No mismatches.

### 5.7 Schema Mismatches: `DiscordOAuthCallbackResponse` vs `Session`

**Core:** Returns `{ token: str, user: UserSchema, expires_in: int }`  
**Dashboard:** `lib/types.ts::Session` = `{ token: string, user: User, expires_in: number }`

✅ Match.

### 5.8 `DashboardLayoutResult` Widget Nullability

**Core:** `capabilities/dashboard_layout.py` — the `lib/dashboard-layout.ts` comment documents that `null` means no saved layout (not an empty array). This is a runtime contract, not a schema mismatch, and `applyLayout` handles it correctly. ✅

### 5.9 Logout Endpoint Method Mismatch — **Critical**

**Dashboard (`app/api/auth/logout/route.ts`):**
```ts
await backend.post(`/api/v1/auth/logout?session_token=${encodeURIComponent(token)}`, {});
```

**Core (`api/routers/auth.py`):**
```python
@router.post("/logout")
async def logout(session_token: str = Query(...))
```

✅ Both are `POST`. No mismatch here despite the query-param style.

---

## Summary of Critical Findings

1. **Three search result hrefs are dead links** — `/players/{uuid}`, `/knowledge/{id}`, `/observability/logs` — no dashboard pages exist at those destinations. Every matching search result in the command palette currently 404s.

2. **`typescript.ignoreBuildErrors: true`** in `next.config.mjs` means type-level schema drift between core and the dashboard will never be caught at build time.

3. **~80% of core's implemented functionality has no dashboard UI.** The dashboard currently only surfaces: capability-driven plugin widgets (WidgetGrid), marketplace browse/install, plugin settings toggles, activity/audit timeline, fleet status (read-only), topology graph, and plugin sandbox profiler. Every other feature area — moderation, punishments, appeals, AI review queue, staff management, analytics, bridge logs, alt detection, security events, feature flags, replay/snapshots, knowledge, observability — has backend support but no frontend surface.

4. **`middleware.ts` only guards 3 route prefixes** out of 7 dashboard routes that check session. Not a security issue (server components re-check), but an unnecessary extra round trip for unauthenticated visitors on the unguarded routes.

5. **No new backend endpoints are required for Phase 14.** Every feature area that needs UI has functioning backend endpoints and (for capability-backed features) registered capabilities already. Phase 14 work is entirely dashboard-side: new pages, new API route handlers forwarding to existing core endpoints, and removing dead search links.
