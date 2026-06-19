import { API_ROOT, API_V1, authHeaders } from './api-config'
import {
  mapAppeal, mapAudit, mapHealth, mapPlayer, mapPlugin, mapPunishment,
  mapRoles, mapServer, mapSettings, mapStaff, buildDashboard, appealStatusToApi,
} from './transforms'
import type {
  Appeal, AuditEntry, BridgeSettings, DashboardData, FlaggedPlayer,
  MinecraftServer, Player, Plugin, Punishment, ReplayEvent, ReplaySession,
  RoleDefinition, ServerSummary, SettingsCategory, StaffMember, PlayerSnapshot,
  SystemMetrics, VerificationCode, AITask,
} from './types'

function requireApi() {
  if (!API_V1) throw new Error('NEXT_PUBLIC_UMBRELLA_API_URL is not configured')
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  requireApi()
  const res = await fetch(`${API_V1}${path}`, {
    ...options,
    headers: authHeaders(options?.headers as Record<string, string>),
  })
  if (res.status === 401 && typeof window !== 'undefined' && window.location.pathname !== '/login') {
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

async function rootRequest<T>(path: string): Promise<T> {
  requireApi()
  const res = await fetch(`${API_ROOT}${path}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json() as Promise<T>
}

export const api = {
  checkConnection: () => rootRequest<{ status: string }>('/health'),

  getDashboard: async (): Promise<DashboardData> => {
    const [punishments, appeals, summary] = await Promise.all([
      request<Record<string, unknown>[]>('/punishments?active_only=false&limit=100').then((d) => d.map(mapPunishment)),
      request<Record<string, unknown>[]>('/appeals?limit=100').then((d) => d.map(mapAppeal)),
      request<ServerSummary>('/analytics/summary'),
    ])
    return buildDashboard(punishments, appeals, summary)
  },

  getPlayers: () => request<Record<string, unknown>[]>('/players?limit=100').then((d) => d.map(mapPlayer)),
  getPlayer: (uuid: string) => request<Record<string, unknown>>(`/players/${uuid}`).then(mapPlayer),
  getPunishments: () => request<Record<string, unknown>[]>('/punishments?active_only=false&limit=100').then((d) => d.map(mapPunishment)),
  getPlayerPunishments: (uuid: string) =>
    request<Record<string, unknown>[]>(`/punishments?player_uuid=${uuid}&active_only=false`).then((d) => d.map(mapPunishment)),
  createPunishment: (body: { player_uuid: string; type: string; reason: string; expires_at?: string }) =>
    request<Record<string, unknown>>('/punishments', { method: 'POST', body: JSON.stringify(body) }).then(mapPunishment),
  revokePunishment: (id: string) =>
    request<Record<string, unknown>>(`/punishments/${id}/revoke`, { method: 'POST' }).then(mapPunishment),

  getAppeals: () => request<Record<string, unknown>[]>('/appeals?limit=100').then((d) => d.map(mapAppeal)),
  getPlayerAppeals: (uuid: string) =>
    request<Record<string, unknown>[]>(`/appeals?player_uuid=${uuid}`).then((d) => d.map(mapAppeal)),
  updateAppeal: (id: string, status: string) =>
    request<Record<string, unknown>>(`/appeals/${id}`, {
      method: 'PATCH', body: JSON.stringify({ status: appealStatusToApi(status) }),
    }).then(mapAppeal),

  getStaff: async () => {
    const [users, roles] = await Promise.all([
      request<Record<string, unknown>[]>('/auth?limit=100'),
      request<Record<string, unknown>[]>('/roles'),
    ])
    return mapStaff(users, roles)
  },
  getRoles: () => request<Record<string, unknown>[]>('/roles').then(mapRoles),
  getPlugins: () => request<Record<string, unknown>[]>('/dashboard/plugins').then((d) => d.map(mapPlugin)),
  getServers: () => request<Record<string, unknown>[]>('/dashboard/servers').then((d) => d.map(mapServer)),

  serverControl: (body: { server_id: string; action: 'power' | 'restart' | 'maintenance'; enabled?: boolean }) =>
    request<{ success: boolean; action: string; maintenance?: boolean }>('/server/control', {
      method: 'POST', body: JSON.stringify(body),
    }),

  manageStaff: (body: { user_id: string; action: 'promote' | 'demote' }) =>
    request<{ user_id: string; username: string; previous_role: string; new_role: string }>('/staff/manage', {
      method: 'POST', body: JSON.stringify(body),
    }),

  getSettings: () => request<Record<string, unknown>[]>('/settings').then(mapSettings),
  updateSetting: (key: string, value: string) =>
    request(`/settings/${encodeURIComponent(key)}`, { method: 'PATCH', body: JSON.stringify({ value }) }),

  getAudit: () => request<{ entries: Record<string, unknown>[] }>('/audit?limit=100').then(mapAudit),
  getSystemHealth: () => rootRequest<Record<string, unknown>>('/health').then(mapHealth),

  getBridgeSettings: () => request<BridgeSettings>('/bridge/settings'),
  updateBridgeSettings: (settings: Partial<BridgeSettings>) =>
    request<BridgeSettings>('/bridge/settings', { method: 'PATCH', body: JSON.stringify(settings) }),

  getAnnouncementChannel: async () => {
    const settings = await request<Record<string, unknown>[]>('/settings')
    const ch = settings.find((s) => s.key === 'discord.announcements_channel')
    return ch?.value ? String(ch.value) : null
  },

  getPendingVerifications: () => request<VerificationCode[]>('/verification/pending'),
  revokeVerification: (player_uuid: string) =>
    request('/verification/revoke', { method: 'POST', body: JSON.stringify({ player_uuid }) }),

  getFlaggedPlayers: (skip = 0, limit = 50) =>
    request<FlaggedPlayer[]>(`/alts/flagged?skip=${skip}&limit=${limit}`),
  getPlayerSuspicion: (uuid: string) =>
    request<{ score: number; events: unknown[]; alt_groups: unknown[] }>(`/alts/player/${uuid}`),
  markFalsePositive: (event_id: number, reviewed_by: string) =>
    request('/alts/false-positive', { method: 'POST', body: JSON.stringify({ event_id, reviewed_by }) }),
  createAltGroup: (player_uuids: string[], notes?: string, confirmed = false) =>
    request('/alts/group', { method: 'POST', body: JSON.stringify({ player_uuids, notes, confirmed }) }),
  getAltGroups: () => request<unknown[]>('/alts/groups'),

  getAnalyticsEvents: (params?: { limit?: number; event_type?: string; minecraft_uuid?: string }) => {
    const q = new URLSearchParams()
    if (params?.limit) q.set('limit', String(params.limit))
    if (params?.event_type) q.set('event_type', params.event_type)
    if (params?.minecraft_uuid) q.set('minecraft_uuid', params.minecraft_uuid)
    return request<unknown[]>(`/analytics/events?${q}`)
  },
  getPlayerStats: (uuid: string, period = 'alltime') =>
    request<unknown[]>(`/analytics/players/${uuid}?period=${period}`),
  getServerSummary: () => request<ServerSummary>('/analytics/summary'),

  listReplaySessions: (params?: { minecraft_uuid?: string; trigger?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams()
    if (params?.minecraft_uuid) q.set('minecraft_uuid', params.minecraft_uuid)
    if (params?.trigger) q.set('trigger', params.trigger)
    if (params?.limit) q.set('limit', String(params.limit))
    if (params?.offset) q.set('offset', String(params.offset))
    return request<ReplaySession[]>(`/replay/sessions?${q}`)
  },
  getReplaySession: (id: string) => request<ReplaySession>(`/replay/sessions/${id}`),
  getReplayEvents: (id: string, params?: { limit?: number; offset?: number }) => {
    const q = new URLSearchParams()
    if (params?.limit) q.set('limit', String(params.limit))
    if (params?.offset) q.set('offset', String(params.offset))
    return request<ReplayEvent[]>(`/replay/sessions/${id}/events?${q}`)
  },
  finalizeReplaySession: (id: string) =>
    request<ReplaySession>(`/replay/sessions/${id}/finalize`, { method: 'POST' }),

  listSnapshots: (uuid: string, params?: { limit?: number }) => {
    const q = new URLSearchParams()
    if (params?.limit) q.set('limit', String(params.limit))
    return request<PlayerSnapshot[]>(`/snapshots/players/${uuid}?${q}`)
  },
  getSnapshot: (id: string) => request<PlayerSnapshot>(`/snapshots/${id}`),
  getLatestSnapshot: (uuid: string) => request<PlayerSnapshot>(`/snapshots/players/${uuid}/latest`),
  getSnapshotsNearReplay: (replayId: string, params?: { window_minutes?: number }) => {
    const q = new URLSearchParams()
    if (params?.window_minutes) q.set('window_minutes', String(params.window_minutes))
    const qs = q.toString()
    return request<PlayerSnapshot[]>(`/snapshots/replay/${replayId}${qs ? `?${qs}` : ''}`)
  },

  getAITasks: (params?: { status?: string; task_type?: string; limit?: number }) => {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    if (params?.task_type) q.set('task_type', params.task_type)
    if (params?.limit) q.set('limit', String(params.limit))
    return request<AITask[]>(`/ai/tasks?${q}`)
  },
  getAITask: (id: number) => request<AITask>(`/ai/tasks/${id}`),
  approveAITask: (id: number, payload: { action_taken: string; reviewed_by: string }) =>
    request<AITask>(`/ai/tasks/${id}/approve`, { method: 'POST', body: JSON.stringify(payload) }),
  denyAITask: (id: number, payload: { reviewed_by: string; reason?: string }) =>
    request<AITask>(`/ai/tasks/${id}/deny`, { method: 'POST', body: JSON.stringify(payload) }),

  getPlayerLanguages: () => request<unknown[]>('/translation/language/all'),
  setPlayerLanguage: (player_uuid: string, language_code: string, language_name: string) =>
    request('/translation/language', {
      method: 'POST', body: JSON.stringify({ player_uuid, language_code, language_name }),
    }),

  requestAIConfig: (action_type: string, natural_language: string) =>
    request('/ai/config/request', {
      method: 'POST', body: JSON.stringify({ action_type, natural_language }),
    }),
  getPendingAIConfigs: () => request<unknown[]>('/ai/config/pending'),
  approveAIConfig: (id: number) => request(`/ai/config/${id}/approve`, { method: 'POST' }),
  rejectAIConfig: (id: number) => request(`/ai/config/${id}/reject`, { method: 'POST' }),
}
