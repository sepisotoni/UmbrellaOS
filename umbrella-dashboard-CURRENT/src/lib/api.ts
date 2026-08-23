/**
 * src/lib/api.ts — Single API client for all backend calls.
 *
 * All requests go to VITE_UMBRELLA_CORE_URL (overridable via localStorage key
 * "umbrella_core_url_override"). Auth token is passed as Authorization Bearer
 * header and stored only in React context — never in localStorage.
 */

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export function getBaseUrl(): string {
  const override = localStorage.getItem('umbrella_core_url_override')
  if (override) return override.replace(/\/$/, '')
  return (import.meta.env.VITE_UMBRELLA_CORE_URL ?? 'http://localhost:8000').replace(/\/$/, '')
}

async function request<T>(
  path: string,
  options: RequestInit & { token?: string; adminKey?: string } = {},
): Promise<T> {
  const { token, adminKey, ...init } = options
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> | undefined),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (adminKey) headers['X-Admin-Key'] = adminKey

  const res = await fetch(`${getBaseUrl()}${path}`, { ...init, headers })

  if (!res.ok) {
    let body: unknown
    try { body = await res.json() } catch { body = await res.text() }
    const msg =
      typeof body === 'object' && body !== null && 'detail' in body
        ? String((body as { detail: unknown }).detail)
        : `HTTP ${res.status}`
    throw new ApiError(res.status, msg, body)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface UserSchema {
  id: string
  discord_id: string
  username: string
  email: string | null
  role_id: string | null
  role: string | null
  permissions: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SessionResponse {
  token: string
  user: UserSchema
  expires_in: number
}

export const auth = {
  discordAuthorize: (redirectUri: string) =>
    request<{ authorize_url: string; state: string }>('/api/v1/auth/discord/authorize', {
      method: 'POST',
      body: JSON.stringify({ redirect_uri: redirectUri }),
    }),

  discordCallback: (state: string, code: string, redirectUri: string) =>
    request<SessionResponse>('/api/v1/auth/discord/callback', {
      method: 'POST',
      body: JSON.stringify({ state, code, redirect_uri: redirectUri }),
    }),

  me: (token: string) =>
    request<UserSchema>('/api/v1/auth/me', { token }),

  // POST /api/v1/auth/logout?session_token=...
  logout: (token: string) =>
    request<{ success: boolean }>(`/api/v1/auth/logout?session_token=${encodeURIComponent(token)}`, {
      method: 'POST',
      token,
    }),
}

// ─── Health ───────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
  version: string
  database: string
  redis: string
  service: string
}

export const health = {
  get: () => request<HealthResponse>('/health'),
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export interface ServerRecord {
  id: string
  name: string
  status: string   // "online" | "offline" | "maintenance"
  tps: number
  players: number
  maxPlayers: number
  ramUsedMb: number
  ramTotalMb: number
  cpu: number
  version: string
  pluginsConnected: number
  pluginsTotal: number
}

export interface PluginRecord {
  id: string
  name: string
  version: string
  server: string
  status: string
  heartbeatMs: number
  lastSeen: string
}

export const dashboard = {
  servers: (token: string) =>
    request<ServerRecord[]>('/api/v1/dashboard/servers', { token }),
  plugins: (token: string) =>
    request<PluginRecord[]>('/api/v1/dashboard/plugins', { token }),
}

// ─── Players ──────────────────────────────────────────────────────────────────

export interface PlayerSchema {
  uuid: string
  username: string
  first_seen: string
  last_seen: string
  playtime: number
  joins: number
  deaths: number
  risk_score: number
  suspicion_score: number
  discord_id: string | null
}

export interface FullProfileResponse {
  player: {
    uuid: string
    username: string
    first_seen: string
    last_seen: string
    playtime: number
    current_server: string | null
    risk_score: number
    suspicion_score: number
  }
  verification: {
    discord_id: string
    discord_username: string | null
    linked_at: string | null
    status: string
  } | null
  punishment_history: Array<{
    id: string
    type: string
    reason: string
    staff_id: string | null
    created_at: string
    expires_at: string | null
    active: boolean
    appeal_id: string | null
  }>
  anticheat_history: {
    total_flags: number
    by_check: Record<string, { count: number; avg_vl: number; max_vl: number }>
    timeline: Array<{
      check_name: string
      vl: number
      verbose: string | null
      timestamp: string
    }>
  }
  appeal_history: Array<{
    id: string
    punishment_id: string
    status: string
    created_at: string
    action_taken: string | null
    handled_by: string | null
    ai_recommendation: string | null
  }>
  alt_accounts: Array<{
    uuid: string
    username: string | null
    confidence: string | null
    cluster_type: string | null
  }>
}

export const players = {
  list: (token: string, params: { username?: string; skip?: number; limit?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.username) q.set('username', params.username)
    if (params.skip !== undefined) q.set('skip', String(params.skip))
    if (params.limit !== undefined) q.set('limit', String(params.limit))
    return request<PlayerSchema[]>(`/api/v1/players?${q}`, { token })
  },
  get: (token: string, uuid: string) =>
    request<PlayerSchema & { ip_addresses: Array<{ id: string; ip_address: string; first_seen: string; last_seen: string }> }>(
      `/api/v1/players/${uuid}`, { token },
    ),
  fullProfile: (token: string, uuid: string) =>
    request<FullProfileResponse>(`/api/v1/players/${uuid}/full-profile`, { token }),
}

// ─── Punishments ──────────────────────────────────────────────────────────────

export interface PunishmentSchema {
  id: string
  player_uuid: string
  staff_id: string | null
  type: string
  reason: string
  created_at: string
  expires_at: string | null
  active: boolean
}

export const punishments = {
  list: (token: string, params: { player_uuid?: string; active_only?: boolean; skip?: number; limit?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.player_uuid) q.set('player_uuid', params.player_uuid)
    if (params.active_only !== undefined) q.set('active_only', String(params.active_only))
    if (params.skip !== undefined) q.set('skip', String(params.skip))
    if (params.limit !== undefined) q.set('limit', String(params.limit))
    return request<PunishmentSchema[]>(`/api/v1/punishments?${q}`, { token })
  },
  create: (token: string, body: { player_uuid: string; type: string; reason: string; expires_at?: string; staff_id?: string }) =>
    request<PunishmentSchema>('/api/v1/punishments', {
      method: 'POST', token, body: JSON.stringify(body),
    }),
  // POST /api/v1/punishments/{id}/revoke — no body required
  revoke: (token: string, id: string) =>
    request<PunishmentSchema>(`/api/v1/punishments/${id}/revoke`, { method: 'POST', token }),
}

// ─── Appeals ──────────────────────────────────────────────────────────────────

export interface AppealSchema {
  id: string
  punishment_id: string
  player_uuid: string
  status: string
  message: string
  created_at: string
  action_taken: string | null
  handled_by: string | null
  case_summary: string | null
  closed_at: string | null
  ai_review_status: string | null
}

export const appeals = {
  list: (token: string, params: { status?: string; player_uuid?: string; skip?: number; limit?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.status) q.set('status', params.status)
    if (params.player_uuid) q.set('player_uuid', params.player_uuid)
    if (params.skip !== undefined) q.set('skip', String(params.skip))
    if (params.limit !== undefined) q.set('limit', String(params.limit))
    return request<AppealSchema[]>(`/api/v1/appeals?${q}`, { token })
  },
  // POST /api/v1/appeals/{id}/close — action: ACCEPT|REDUCE_SENTENCE|REJECT|ESCALATE|SCHEDULE_REVIEW
  close: (token: string, id: string, body: { action: string; staff_note?: string; new_expiry?: string }) =>
    request<AppealSchema>(`/api/v1/appeals/${id}/close`, {
      method: 'POST', token, body: JSON.stringify(body),
    }),
}

// ─── Anticheat ────────────────────────────────────────────────────────────────

export interface ViolationRecord {
  id: string
  player_uuid: string
  player_name: string
  server_id: string | null
  check_name: string
  verbose: string
  vl: number
  created_at: string
}

export const anticheat = {
  violations: (token: string, params: { player_uuid?: string; server_id?: string; check_name?: string; limit?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.player_uuid) q.set('player_uuid', params.player_uuid)
    if (params.server_id) q.set('server_id', params.server_id)
    if (params.check_name) q.set('check_name', params.check_name)
    if (params.limit !== undefined) q.set('limit', String(params.limit))
    return request<ViolationRecord[]>(`/api/v1/anticheat/violations?${q}`, { token })
  },
}

// ─── Staff ────────────────────────────────────────────────────────────────────

export interface StaffMemberSchema {
  id: string
  discord_id: string
  username: string
  discriminator: string
  avatar_url: string | null
  role: string | null
  permissions: string[]
  email: string | null
  linked_minecraft_uuid: string | null
  linked_minecraft_username: string | null
}

export interface StaffManageResponse {
  user_id: string
  username: string
  previous_role: string
  new_role: string
  action: string
}

export const staff = {
  list: (token: string) =>
    request<StaffMemberSchema[]>('/api/v1/staff', { token }),
  manage: (token: string, body: { user_id: string; action: 'promote' | 'demote' }) =>
    request<StaffManageResponse>('/api/v1/staff/manage', {
      method: 'POST', token, body: JSON.stringify(body),
    }),
  add: (token: string, body: { discord_id: string; role: string; username?: string }) =>
    request<StaffManageResponse>('/api/v1/staff/add', {
      method: 'POST', token, body: JSON.stringify(body),
    }),
}

// ─── Verification ─────────────────────────────────────────────────────────────

export interface VerificationLinkSchema {
  id: number
  discord_id: string
  discord_username: string | null
  minecraft_uuid: string | null
  minecraft_username: string | null
  linked_at: string | null
  verified_by: string
  status: string
}

export interface VerificationCodeSchema {
  id: number
  player_uuid: string
  player_username: string
  code: string
  created_at: string
  expires_at: string
  used: boolean
  ip_address: string | null
}

export const verification = {
  links: (token: string, params: { limit?: number; offset?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.limit !== undefined) q.set('limit', String(params.limit))
    if (params.offset !== undefined) q.set('offset', String(params.offset))
    return request<VerificationLinkSchema[]>(`/api/v1/verification/links?${q}`, { token })
  },
  pending: (token: string) =>
    request<VerificationCodeSchema[]>('/api/v1/verification/pending', { token }),
  // DELETE /api/v1/verification/unlink/{discord_id}
  unlink: (token: string, discordId: string) =>
    request<{ success: boolean }>(`/api/v1/verification/unlink/${discordId}`, {
      method: 'DELETE', token,
    }),
}

// ─── Alt Detection ────────────────────────────────────────────────────────────

export interface FlaggedPlayerSchema {
  uuid: string
  username: string
  suspicion_score: number
  first_seen: string
}

export interface AltGroupSchema {
  id: number
  created_at: string
  notes: string | null
  confirmed: boolean
}

export const alts = {
  // Players with suspicion_score >= 80
  flagged: (token: string, params: { skip?: number; limit?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.skip !== undefined) q.set('skip', String(params.skip))
    if (params.limit !== undefined) q.set('limit', String(params.limit))
    return request<FlaggedPlayerSchema[]>(`/api/v1/alts/flagged?${q}`, { token })
  },
  // Only returns confirmed=true groups
  groups: (token: string) =>
    request<AltGroupSchema[]>('/api/v1/alts/groups', { token }),
  // Marks most recent suspicion event for player as false positive
  falsePositive: (token: string, body: { event_id?: number; player_uuid?: string; reviewed_by: string }) =>
    request<{ success: boolean }>('/api/v1/alts/false-positive', {
      method: 'POST', token, body: JSON.stringify(body),
    }),
}

// ─── AI Tasks ─────────────────────────────────────────────────────────────────

export interface AITaskRecord {
  id: number
  task_type: string
  status: string    // "pending" | "approved" | "denied"
  player_uuid: string | null
  created_at: string
  expires_at: string
  ai_summary: string | null
  ai_recommendation: string | null
  ai_confidence: number | null
  reviewed_by: string | null
  reviewed_at: string | null
  action_taken: string | null
}

export const aiTasks = {
  list: (token: string, params: { status?: string; task_type?: string; skip?: number; limit?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.status) q.set('status', params.status)
    if (params.task_type) q.set('task_type', params.task_type)
    if (params.skip !== undefined) q.set('skip', String(params.skip))
    if (params.limit !== undefined) q.set('limit', String(params.limit))
    return request<AITaskRecord[]>(`/api/v1/ai/tasks?${q}`, { token })
  },
  // Both action_taken and reviewed_by are required by the backend
  approve: (token: string, taskId: number, body: { action_taken: string; reviewed_by: string }) =>
    request<AITaskRecord>(`/api/v1/ai/tasks/${taskId}/approve`, {
      method: 'POST', token, body: JSON.stringify(body),
    }),
  deny: (token: string, taskId: number, body: { reviewed_by: string; reason?: string }) =>
    request<AITaskRecord>(`/api/v1/ai/tasks/${taskId}/deny`, {
      method: 'POST', token, body: JSON.stringify(body),
    }),
  // Triggers on-demand AI review — returns 503 on AI failure (not 400)
  reviewPlayer: (token: string, uuid: string) =>
    request<AITaskRecord>(`/api/v1/ai/review/player/${uuid}`, { method: 'POST', token }),
  reviewAppeal: (token: string, appealId: string) =>
    request<AITaskRecord & { ai_review_status?: string; ai_result?: unknown }>(
      `/api/v1/ai/review/appeal/${appealId}`, { method: 'POST', token },
    ),
}

// ─── AI Copilot & Crash Risk ──────────────────────────────────────────────────

export interface CopilotResponse {
  response: string
  model_used: string
  latency_ms: number
}

export interface CrashRiskResponse {
  server_id: string
  // Real enum values from crash_prevention.py: INSUFFICIENT_DATA | NONE | WATCH | CRITICAL
  risk_level: 'INSUFFICIENT_DATA' | 'NONE' | 'WATCH' | 'CRITICAL' | string
  tps_trend: number | null
  mspt_avg: number | null   // always null — MSPT not tracked in current schema
  recommendation: string
  assessed_at: string
}

export const ai = {
  copilot: (token: string, body: { message: string; context?: string }) =>
    request<CopilotResponse>('/api/v1/ai/copilot', {
      method: 'POST', token, body: JSON.stringify(body),
    }),
  crashRisk: (token: string, serverId: string) =>
    request<CrashRiskResponse>(`/api/v1/ai/crash-risk/${serverId}`, { token }),
}

// ─── AI Config (per-task model assignments) ───────────────────────────────────

export interface TaskModelAssignment {
  primary: string       // "gemini" | "anthropic" | "openai" | "deepseek" | "openrouter"
  failover: string | null
}

export interface TaskConfigResponse {
  player_review: TaskModelAssignment
  appeal_review: TaskModelAssignment
  copilot: TaskModelAssignment
  crash_risk: TaskModelAssignment
  chat_responder: TaskModelAssignment
}

export const aiConfig = {
  // GET /api/v1/ai/config/tasks — per-task model assignments
  getTasks: (token: string) =>
    request<TaskConfigResponse>('/api/v1/ai/config/tasks', { token }),
  // POST /api/v1/ai/config/tasks — update one task's provider
  updateTask: (token: string, body: { task: string; primary: string; failover?: string | null }) =>
    request<TaskConfigResponse>('/api/v1/ai/config/tasks', {
      method: 'POST', token, body: JSON.stringify(body),
    }),
  // POST /api/v1/ai/providers/test — live key validation
  testProvider: (token: string, body: { provider: string; api_key?: string }) =>
    request<{ success: boolean; latency_ms: number; message: string; model: string }>(
      '/api/v1/ai/providers/test', { method: 'POST', token, body: JSON.stringify(body) },
    ),
}

// ─── Audit ────────────────────────────────────────────────────────────────────

export interface AuditEntry {
  id: string
  actor: string
  actor_type: string
  action: string
  target: string | null
  details_json: string | null
  created_at: string
  trace_id: string | null
}

// Audit returns {items, total} dict from the capability registry
export interface AuditResponse {
  items: AuditEntry[]
  total: number
}

export const audit = {
  list: (token: string, params: { limit?: number; offset?: number; actor_type?: string } = {}) => {
    const q = new URLSearchParams()
    if (params.limit !== undefined) q.set('limit', String(params.limit))
    if (params.offset !== undefined) q.set('offset', String(params.offset))
    if (params.actor_type) q.set('actor_type', params.actor_type)
    return request<AuditResponse>(`/api/v1/audit?${q}`, { token })
  },
}

// ─── Feature Flags ────────────────────────────────────────────────────────────

export interface FeatureFlagRecord {
  id: string
  name: string
  enabled: boolean
  description: string
}

export const featureFlags = {
  list: (token: string) =>
    request<FeatureFlagRecord[]>('/api/v1/feature-flags', { token }),
  // POST /api/v1/feature-flags — upsert by name, returns 200 (not 201)
  upsert: (token: string, body: { name: string; enabled: boolean; description: string }) =>
    request<FeatureFlagRecord>('/api/v1/feature-flags', {
      method: 'POST', token, body: JSON.stringify(body),
    }),
}

// ─── Settings ─────────────────────────────────────────────────────────────────

export interface SettingRecord {
  key: string
  value: string
  sensitive: boolean
  category: string
  description: string
}

export const settings = {
  list: (token: string) =>
    request<SettingRecord[]>('/api/v1/settings', { token }),
  get: (token: string, key: string) =>
    request<SettingRecord>(`/api/v1/settings/${encodeURIComponent(key)}`, { token }),
  // POST /api/v1/settings/{key} — upsert (creates if not exists)
  update: (token: string, key: string, value: string) =>
    request<SettingRecord>(`/api/v1/settings/${encodeURIComponent(key)}`, {
      method: 'POST', token, body: JSON.stringify({ value }),
    }),
}

// ─── WebSocket Console ────────────────────────────────────────────────────────

export function openConsoleWebSocket(serverId: string, token: string): WebSocket {
  const base = getBaseUrl().replace(/^http/, 'ws')
  // Token travels as query param — standard pattern for browser WebSocket auth
  // (browsers can't set arbitrary headers on WebSocket connections)
  return new WebSocket(`${base}/api/v1/hosting/servers/${serverId}/console?token=${encodeURIComponent(token)}`)
}
