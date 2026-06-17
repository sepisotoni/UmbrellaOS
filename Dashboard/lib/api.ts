// Umbrella Core API service abstraction.
//
// Every call goes through `request()`. When NEXT_PUBLIC_UMBRELLA_API_URL is set,
// requests hit the live FastAPI backend. Otherwise we resolve from local mock
// data so the dashboard is fully explorable without a backend.

import {
  analytics,
  appeals,
  audit,
  dashboard,
  players,
  plugins,
  punishments,
  roles,
  servers,
  settings,
  staff,
  systemMetrics,
} from './mock-data'
import type {
  AnalyticsData,
  Appeal,
  AuditEntry,
  BridgeSettings,
  DashboardData,
  FlaggedPlayer,
  MinecraftServer,
  Player,
  Plugin,
  Punishment,
  RoleDefinition,
  ReplaySession,
  ReplayEvent,
  PlayerSnapshot,
  ServerSummary,
  SettingsCategory,
  StaffMember,
  SuspicionEvent,
  SystemMetrics,
  VerificationCode,
  AITask,
} from './types'

const BASE_URL = process.env.NEXT_PUBLIC_UMBRELLA_API_URL
const ADMIN_KEY = process.env.NEXT_PUBLIC_UMBRELLA_ADMIN_KEY

async function delay<T>(data: T, ms = 350): Promise<T> {
  await new Promise((r) => setTimeout(r, ms))
  return data
}

async function request<T>(path: string, mock: () => T, options?: RequestInit): Promise<T> {
  if (!BASE_URL) {
    return delay(mock())
  }
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  }
  
  // Try Bearer token from localStorage first (session auth)
  const token = typeof window !== 'undefined' ? localStorage.getItem('umbrella_token') : null
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  // Fall back to X-Admin-Key for plugin auth
  if (ADMIN_KEY) {
    headers['X-Admin-Key'] = ADMIN_KEY
  }
  
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  })
  
  // Redirect to login on 401
  if (res.status === 401 && typeof window !== 'undefined') {
    window.location.href = '/login'
    throw new Error('Unauthorized - redirecting to login')
  }
  
  if (!res.ok) {
    throw new Error(`Umbrella Core request failed: ${res.status} ${path}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  getDashboard: () => request<DashboardData>('/api/v1/stats', () => dashboard),
  getPlayers: () => request<Player[]>('/api/v1/players', () => players),
  getPlayer: (uuid: string) =>
    request<Player | undefined>(`/api/v1/players/${uuid}`, () =>
      players.find((p) => p.uuid === uuid),
    ),
  getPunishments: () => request<Punishment[]>('/api/v1/punishments', () => punishments),
  getPlayerPunishments: (uuid: string) =>
    request<Punishment[]>(`/api/v1/punishments?player_uuid=${uuid}`, () =>
      punishments.filter((p) => p.playerUuid === uuid),
    ),
  revokePunishment: (id: string) =>
    request<Punishment>(`/api/v1/punishments/${id}/revoke`, () => {
      const p = punishments.find((p) => p.id === id)
      if (p) return { ...p, status: 'revoked' }
      throw new Error('Punishment not found')
    }, { method: 'POST' }),
  getAppeals: () => request<Appeal[]>('/api/v1/appeals', () => appeals),
  getPlayerAppeals: (uuid: string) =>
    request<Appeal[]>(`/api/v1/appeals?player_uuid=${uuid}`, () =>
      appeals.filter((a) => a.playerUuid === uuid),
    ),
  updateAppeal: (id: string, status: string) =>
    request<Appeal>(`/api/v1/appeals/${id}`, () => {
      const a = appeals.find((a) => a.id === id)
      if (a) return { ...a, status: status as any }
      throw new Error('Appeal not found')
    }, { method: 'PATCH', body: JSON.stringify({ status }) }),
  getStaff: () => request<StaffMember[]>('/api/v1/auth', () => staff),
  getRoles: () => request<RoleDefinition[]>('/api/v1/roles', () => roles),
  getPlugins: () => request<Plugin[]>('/api/v1/plugins', () => plugins),
  getServers: () => request<MinecraftServer[]>('/api/v1/servers', () => servers),
  getAnalytics: () => request<AnalyticsData>('/api/v1/analytics', () => analytics),
  getSettings: () => request<SettingsCategory[]>('/api/v1/settings', () => settings),
  getAudit: () => request<AuditEntry[]>('/api/v1/audit', () => audit),
  getSystemHealth: () =>
    request<SystemMetrics>('/api/v1/system/health', () => systemMetrics),
  getBridgeSettings: () => request<BridgeSettings>('/api/v1/bridge/settings', () => ({
    mode: 'off',
    mc_to_discord: true,
    discord_to_mc: true,
    show_avatars: true,
    discord_channel_id: '',
  })),
  updateBridgeSettings: (settings: Partial<BridgeSettings>) =>
    request<BridgeSettings>('/api/v1/bridge/settings', () => ({
      mode: 'off',
      mc_to_discord: true,
      discord_to_mc: true,
      show_avatars: true,
      discord_channel_id: '',
    }), { method: 'PATCH', body: JSON.stringify(settings) }),
  getPendingVerifications: () => request<VerificationCode[]>('/api/v1/verification/pending', () => []),
  revokeVerification: (player_uuid: string) =>
    request<{ success: boolean }>('/api/v1/verification/revoke', () => ({ success: true }), { method: 'POST', body: JSON.stringify({ player_uuid }) }),
  getFlaggedPlayers: (skip = 0, limit = 50) => request<FlaggedPlayer[]>(`/api/v1/alts/flagged?skip=${skip}&limit=${limit}`, () => []),
  getPlayerSuspicion: (uuid: string) => request<{ score: number, events: SuspicionEvent[], alt_groups: any[] }>(`/api/v1/alts/player/${uuid}`, () => ({ score: 0, events: [], alt_groups: [] })),
  markFalsePositive: (event_id: number, reviewed_by: string) =>
    request<{ success: boolean }>('/api/v1/alts/false-positive', () => ({ success: true }), { method: 'POST', body: JSON.stringify({ event_id, reviewed_by }) }),
  createAltGroup: (player_uuids: string[], notes?: string, confirmed = false) =>
    request<any>('/api/v1/alts/group', () => ({ id: 0 }), { method: 'POST', body: JSON.stringify({ player_uuids, notes, confirmed }) }),
  getAltGroups: () => request<any[]>('/api/v1/alts/groups', () => []),
  postAnalyticsEvent: (payload: { event_type: string, minecraft_uuid?: string, data?: any }) =>
    request<any>('/api/v1/analytics/events', () => ({ id: '' }), { method: 'POST', body: JSON.stringify(payload) }),
  getAnalyticsEvents: (params?: { limit?: number, event_type?: string, minecraft_uuid?: string }) => {
    const query = new URLSearchParams()
    if (params?.limit) query.append('limit', params.limit.toString())
    if (params?.event_type) query.append('event_type', params.event_type)
    if (params?.minecraft_uuid) query.append('minecraft_uuid', params.minecraft_uuid)
    return request<any[]>(`/api/v1/analytics/events?${query.toString()}`, () => [])
  },
  getPlayerStats: (uuid: string, period = 'alltime') => request<any[]>(`/api/v1/analytics/players/${uuid}?period=${period}`, () => []),
  getServerSummary: () => request<ServerSummary>('/api/v1/analytics/summary', () => ({ joins: 0, leaves: 0, deaths: 0, kills: 0, chat_volume: 0, playtime_seconds: 0 })),
  createReplaySession: (payload: { trigger: string, triggered_by: string, minecraft_uuid: string, incident_at: string, started_at?: string, notes?: string }) =>
    request<ReplaySession>('/api/v1/replay/sessions', () => ({ id: '', trigger: '', triggered_by: '', minecraft_uuid: '', started_at: '', incident_at: '', ended_at: null, event_count: 0, created_at: '', notes: null }), { method: 'POST', body: JSON.stringify(payload) }),
  listReplaySessions: (params?: { minecraft_uuid?: string, trigger?: string, limit?: number, offset?: number }) => {
    const query = new URLSearchParams()
    if (params?.minecraft_uuid) query.append('minecraft_uuid', params.minecraft_uuid)
    if (params?.trigger) query.append('trigger', params.trigger)
    if (params?.limit) query.append('limit', params.limit.toString())
    if (params?.offset) query.append('offset', params.offset.toString())
    return request<ReplaySession[]>(`/api/v1/replay/sessions?${query.toString()}`, () => [])
  },
  getReplaySession: (replayId: string) => request<ReplaySession>(`/api/v1/replay/sessions/${replayId}`, () => null),
  getReplayEvents: (replayId: string, params?: { event_type?: string, minecraft_uuid?: string, limit?: number, offset?: number }) => {
    const query = new URLSearchParams()
    if (params?.event_type) query.append('event_type', params.event_type)
    if (params?.minecraft_uuid) query.append('minecraft_uuid', params.minecraft_uuid)
    if (params?.limit) query.append('limit', params.limit.toString())
    if (params?.offset) query.append('offset', params.offset.toString())
    return request<ReplayEvent[]>(`/api/v1/replay/sessions/${replayId}/events?${query.toString()}`, () => [])
  },
  finalizeReplaySession: (replayId: string) =>
    request<ReplaySession>(`/api/v1/replay/sessions/${replayId}/finalize`, () => null, { method: 'POST' }),
  createSnapshot: (payload: { minecraft_uuid: string, trigger?: string, health?: number | null, food?: number | null, xp?: number | null, inventory?: Record<string, any> | null, armor?: Record<string, any> | null, offhand?: Record<string, any> | null, x?: number | null, y?: number | null, z?: number | null, yaw?: number | null, pitch?: number | null, world?: string | null, dimension?: string | null, replay_id?: string | null, timestamp?: string | null }) =>
    request<PlayerSnapshot>('/api/v1/snapshots', () => ({ id: '', minecraft_uuid: '', timestamp: '', trigger: '', health: null, food: null, xp: null, inventory_json: null, armor_json: null, offhand_json: null, x: null, y: null, z: null, yaw: null, pitch: null, world: null, dimension: null, replay_id: null }), { method: 'POST', body: JSON.stringify(payload) }),
  listSnapshots: (uuid: string, params?: { limit?: number, offset?: number, trigger?: string, since?: string, until?: string }) => {
    const query = new URLSearchParams()
    if (params?.limit) query.append('limit', params.limit.toString())
    if (params?.offset) query.append('offset', params.offset.toString())
    if (params?.trigger) query.append('trigger', params.trigger)
    if (params?.since) query.append('since', params.since)
    if (params?.until) query.append('until', params.until)
    return request<PlayerSnapshot[]>(`/api/v1/snapshots/players/${uuid}?${query.toString()}`, () => [])
  },
  getLatestSnapshot: (uuid: string) => request<PlayerSnapshot>(`/api/v1/snapshots/players/${uuid}/latest`, () => null),
  getSnapshot: (snapshotId: string) => request<PlayerSnapshot>(`/api/v1/snapshots/${snapshotId}`, () => null),
  getSnapshotsNearReplay: (replayId: string, params?: { window_minutes?: number }) => {
    const query = new URLSearchParams()
    if (params?.window_minutes) query.append('window_minutes', params.window_minutes.toString())
    return request<PlayerSnapshot[]>(`/api/v1/snapshots/replay/${replayId}?${query.toString()}`, () => [])
  },
  getAITasks: (params?: { status?: string, task_type?: string, skip?: number, limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.status) query.append('status', params.status)
    if (params?.task_type) query.append('task_type', params.task_type)
    if (params?.skip) query.append('skip', params.skip.toString())
    if (params?.limit) query.append('limit', params.limit.toString())
    return request<AITask[]>(`/api/v1/ai/tasks?${query.toString()}`, () => [])
  },
  getAITask: (taskId: number) => request<AITask>(`/api/v1/ai/tasks/${taskId}`, () => null as AITask | null),
  approveAITask: (taskId: number, payload: { action_taken: string, reviewed_by: string }) =>
    request<AITask>(`/api/v1/ai/tasks/${taskId}/approve`, () => null as AITask | null, { method: 'POST', body: JSON.stringify(payload) }),
  denyAITask: (taskId: number, payload: { reviewed_by: string, reason?: string }) =>
    request<AITask>(`/api/v1/ai/tasks/${taskId}/deny`, () => null as AITask | null, { method: 'POST', body: JSON.stringify(payload) }),
  triggerPlayerReview: (uuid: string) =>
    request<AITask>(`/api/v1/ai/review/player/${uuid}`, () => null as AITask | null, { method: 'POST' }),
  triggerAppealReview: (appealId: string) =>
    request<AITask>(`/api/v1/ai/review/appeal/${appealId}`, () => null as AITask | null, { method: 'POST' }),
}
