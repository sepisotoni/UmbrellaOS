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
  ActivityPoint,
  AnalyticsData,
  Appeal,
  AppealPoint,
  AuditEntry,
  BridgeSettings,
  DashboardData,
  FlaggedPlayer,
  MinecraftServer,
  Player,
  Plugin,
  Punishment,
  PunishmentPoint,
  RoleDefinition,
  ReplaySession,
  ReplayEvent,
  PlayerSnapshot,
  ServerSummary,
  SettingsCategory,
  StaffMember,
  StatCard,
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
    console.warn('UMBRELLA: No API URL set, using mock data')
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

// Helper function to compose dashboard data from real endpoints
async function fetchLiveDashboard(): Promise<DashboardData> {
  try {
    // Fetch real data from existing endpoints
    const [punishmentsData, appealsData, serverSummary] = await Promise.all([
      request<Punishment[]>('/punishments', () => punishments),
      request<Appeal[]>('/appeals', () => appeals),
      request<ServerSummary>('/analytics/summary', () => ({ joins: 0, leaves: 0, deaths: 0, kills: 0, chat_volume: 0, playtime_seconds: 0 })),
    ])
    
    // Derive daily punishment counts
    const punishmentCounts: Record<string, PunishmentPoint> = {}
    punishmentsData.forEach(p => {
      const day = p.createdAt.slice(5, 10) // MM-DD format
      if (!punishmentCounts[day]) {
        punishmentCounts[day] = { day, warns: 0, mutes: 0, tempbans: 0, bans: 0 }
      }
      if (p.type === 'warn') punishmentCounts[day].warns++
      else if (p.type === 'mute') punishmentCounts[day].mutes++
      else if (p.type === 'tempban') punishmentCounts[day].tempbans++
      else if (p.type === 'ban') punishmentCounts[day].bans++
    })
    
    // Derive daily appeal counts
    const appealCounts: Record<string, AppealPoint> = {}
    appealsData.forEach(a => {
      const day = a.createdAt.slice(5, 10)
      if (!appealCounts[day]) {
        appealCounts[day] = { day, open: 0, accepted: 0, denied: 0 }
      }
      if (a.status === 'open') appealCounts[day].open++
      else if (a.status === 'accepted') appealCounts[day].accepted++
      else if (a.status === 'denied') appealCounts[day].denied++
    })
    
    // Generate stat cards from real data
    const activePunishments = punishmentsData.filter(p => p.status === 'active').length
    const openAppeals = appealsData.filter(a => a.status === 'open').length
    
    const cards: StatCard[] = [
      { 
        id: 'punishments', 
        label: 'Active Punishments', 
        value: activePunishments.toString(), 
        rawValue: activePunishments, 
        changePct: 0, 
        trend: 'flat', 
        spark: Array(16).fill(activePunishments),
        intent: activePunishments > 50 ? 'danger' : activePunishments > 20 ? 'warning' : 'success'
      },
      { 
        id: 'appeals', 
        label: 'Open Appeals', 
        value: openAppeals.toString(), 
        rawValue: openAppeals, 
        changePct: 0, 
        trend: 'flat', 
        spark: Array(16).fill(openAppeals),
        intent: openAppeals > 10 ? 'danger' : openAppeals > 5 ? 'warning' : 'success'
      },
      {
        id: 'joins',
        label: 'Total Joins',
        value: serverSummary.joins.toString(),
        rawValue: serverSummary.joins,
        changePct: 0,
        trend: 'flat',
        spark: Array(16).fill(serverSummary.joins),
      },
      {
        id: 'deaths',
        label: 'Total Deaths',
        value: serverSummary.deaths.toString(),
        rawValue: serverSummary.deaths,
        changePct: 0,
        trend: 'flat',
        spark: Array(16).fill(serverSummary.deaths),
      },
    ]
    
    // Generate activity points (simplified - using server summary as base)
    const activity: ActivityPoint[] = Array.from({ length: 24 }).map((_, h) => ({
      hour: `${h.toString().padStart(2, '0')}:00`,
      joins: Math.round(serverSummary.joins / 24),
      leaves: Math.round(serverSummary.leaves / 24),
      peak: Math.round(serverSummary.joins / 10),
    }))
    
    // Convert punishment counts to array and sort by date
    const punishments: PunishmentPoint[] = Object.values(punishmentCounts).sort((a, b) => a.day.localeCompare(b.day))
    
    // Convert appeal counts to array and sort by date
    const appeals: AppealPoint[] = Object.values(appealCounts).sort((a, b) => a.day.localeCompare(b.day))
    
    return { cards, activity, punishments, appeals }
  } catch (error) {
    // Fall back to mock data if real fetch fails
    console.error('UMBRELLA: fetchLiveDashboard failed')
    console.error('UMBRELLA: BASE_URL:', BASE_URL)
    console.error('UMBRELLA: Tried to fetch from:', `${BASE_URL}/punishments`, `${BASE_URL}/appeals`, `${BASE_URL}/analytics/summary`)
    console.error('UMBRELLA: Full error:', error)
    console.error('UMBRELLA: Error details:', error instanceof Error ? error.message : String(error))
    console.error('UMBRELLA FALLBACK: Returning mock dashboard data')
    return dashboard
  }
}

export const api = {
  getDashboard: () => {
    if (!BASE_URL) {
      console.warn('UMBRELLA: BASE_URL not set, using mock data')
      return Promise.resolve(dashboard)
    }
    return fetchLiveDashboard()
  },
  getPlayers: () => request<Player[]>('/players', () => players),
  getPlayer: (uuid: string) =>
    request<Player | undefined>(`/players/${uuid}`, () =>
      players.find((p) => p.uuid === uuid),
    ),
  getPunishments: () => request<Punishment[]>('/punishments', () => punishments),
  getPlayerPunishments: (uuid: string) =>
    request<Punishment[]>(`/punishments?player_uuid=${uuid}`, () =>
      punishments.filter((p) => p.playerUuid === uuid),
    ),
  revokePunishment: (id: string) =>
    request<Punishment>(`/punishments/${id}/revoke`, () => {
      const p = punishments.find((p) => p.id === id)
      if (p) return { ...p, status: 'revoked' }
      throw new Error('Punishment not found')
    }, { method: 'POST' }),
  getAppeals: () => request<Appeal[]>('/appeals', () => appeals),
  getPlayerAppeals: (uuid: string) =>
    request<Appeal[]>(`/appeals?player_uuid=${uuid}`, () =>
      appeals.filter((a) => a.playerUuid === uuid),
    ),
  updateAppeal: (id: string, status: string) =>
    request<Appeal>(`/appeals/${id}`, () => {
      const a = appeals.find((a) => a.id === id)
      if (a) return { ...a, status: status as any }
      throw new Error('Appeal not found')
    }, { method: 'PATCH', body: JSON.stringify({ status }) }),
  getStaff: () => request<StaffMember[]>('/auth', () => staff),
  getRoles: () => request<RoleDefinition[]>('/roles', () => roles),
  getPlugins: () => request<Plugin[]>('/plugins', () => plugins),
  getServers: () => request<MinecraftServer[]>('/servers', () => servers),
  getAnalytics: () => request<AnalyticsData>('/analytics', () => analytics),
  getSettings: () => request<SettingsCategory[]>('/settings', () => settings),
  getAudit: () => request<AuditEntry[]>('/audit', () => audit),
  getSystemHealth: () =>
    request<SystemMetrics>('/system/health', () => systemMetrics),
  getBridgeSettings: () => request<BridgeSettings>('/bridge/settings', () => ({
    mode: 'off',
    mc_to_discord: true,
    discord_to_mc: true,
    show_avatars: true,
    discord_channel_id: '',
  })),
  updateBridgeSettings: (settings: Partial<BridgeSettings>) =>
    request<BridgeSettings>('/bridge/settings', () => ({
      mode: 'off',
      mc_to_discord: true,
      discord_to_mc: true,
      show_avatars: true,
      discord_channel_id: '',
    }), { method: 'PATCH', body: JSON.stringify(settings) }),
  getPendingVerifications: () => request<VerificationCode[]>('/verification/pending', () => []),
  revokeVerification: (player_uuid: string) =>
    request<{ success: boolean }>('/verification/revoke', () => ({ success: true }), { method: 'POST', body: JSON.stringify({ player_uuid }) }),
  getFlaggedPlayers: (skip = 0, limit = 50) => request<FlaggedPlayer[]>(`/alts/flagged?skip=${skip}&limit=${limit}`, () => []),
  getPlayerSuspicion: (uuid: string) => request<{ score: number, events: SuspicionEvent[], alt_groups: any[] }>(`/alts/player/${uuid}`, () => ({ score: 0, events: [], alt_groups: [] })),
  markFalsePositive: (event_id: number, reviewed_by: string) =>
    request<{ success: boolean }>('/alts/false-positive', () => ({ success: true }), { method: 'POST', body: JSON.stringify({ event_id, reviewed_by }) }),
  createAltGroup: (player_uuids: string[], notes?: string, confirmed = false) =>
    request<any>('/alts/group', () => ({ id: 0 }), { method: 'POST', body: JSON.stringify({ player_uuids, notes, confirmed }) }),
  getAltGroups: () => request<any[]>('/alts/groups', () => []),
  postAnalyticsEvent: (payload: { event_type: string, minecraft_uuid?: string, data?: any }) =>
    request<any>('/analytics/events', () => ({ id: '' }), { method: 'POST', body: JSON.stringify(payload) }),
  getAnalyticsEvents: (params?: { limit?: number, event_type?: string, minecraft_uuid?: string }) => {
    const query = new URLSearchParams()
    if (params?.limit) query.append('limit', params.limit.toString())
    if (params?.event_type) query.append('event_type', params.event_type)
    if (params?.minecraft_uuid) query.append('minecraft_uuid', params.minecraft_uuid)
    return request<any[]>(`/analytics/events?${query.toString()}`, () => [])
  },
  getPlayerStats: (uuid: string, period = 'alltime') => request<any[]>(`/analytics/players/${uuid}?period=${period}`, () => []),
  getServerSummary: () => request<ServerSummary>('/analytics/summary', () => ({ joins: 0, leaves: 0, deaths: 0, kills: 0, chat_volume: 0, playtime_seconds: 0 })),
  createReplaySession: (payload: { trigger: string, triggered_by: string, minecraft_uuid: string, incident_at: string, started_at?: string, notes?: string }) =>
    request<ReplaySession>('/replay/sessions', () => ({ id: '', trigger: '', triggered_by: '', minecraft_uuid: '', started_at: '', incident_at: '', ended_at: null, event_count: 0, created_at: '', notes: null }), { method: 'POST', body: JSON.stringify(payload) }),
  listReplaySessions: (params?: { minecraft_uuid?: string, trigger?: string, limit?: number, offset?: number }) => {
    const query = new URLSearchParams()
    if (params?.minecraft_uuid) query.append('minecraft_uuid', params.minecraft_uuid)
    if (params?.trigger) query.append('trigger', params.trigger)
    if (params?.limit) query.append('limit', params.limit.toString())
    if (params?.offset) query.append('offset', params.offset.toString())
    return request<ReplaySession[]>(`/replay/sessions?${query.toString()}`, () => [])
  },
  getReplaySession: (replayId: string) => request<ReplaySession>(`/replay/sessions/${replayId}`, () => null),
  getReplayEvents: (replayId: string, params?: { event_type?: string, minecraft_uuid?: string, limit?: number, offset?: number }) => {
    const query = new URLSearchParams()
    if (params?.event_type) query.append('event_type', params.event_type)
    if (params?.minecraft_uuid) query.append('minecraft_uuid', params.minecraft_uuid)
    if (params?.limit) query.append('limit', params.limit.toString())
    if (params?.offset) query.append('offset', params.offset.toString())
    return request<ReplayEvent[]>(`/replay/sessions/${replayId}/events?${query.toString()}`, () => [])
  },
  finalizeReplaySession: (replayId: string) =>
    request<ReplaySession>(`/replay/sessions/${replayId}/finalize`, () => null, { method: 'POST' }),
  createSnapshot: (payload: { minecraft_uuid: string, trigger?: string, health?: number | null, food?: number | null, xp?: number | null, inventory?: Record<string, any> | null, armor?: Record<string, any> | null, offhand?: Record<string, any> | null, x?: number | null, y?: number | null, z?: number | null, yaw?: number | null, pitch?: number | null, world?: string | null, dimension?: string | null, replay_id?: string | null, timestamp?: string | null }) =>
    request<PlayerSnapshot>('/snapshots', () => ({ id: '', minecraft_uuid: '', timestamp: '', trigger: '', health: null, food: null, xp: null, inventory_json: null, armor_json: null, offhand_json: null, x: null, y: null, z: null, yaw: null, pitch: null, world: null, dimension: null, replay_id: null }), { method: 'POST', body: JSON.stringify(payload) }),
  listSnapshots: (uuid: string, params?: { limit?: number, offset?: number, trigger?: string, since?: string, until?: string }) => {
    const query = new URLSearchParams()
    if (params?.limit) query.append('limit', params.limit.toString())
    if (params?.offset) query.append('offset', params.offset.toString())
    if (params?.trigger) query.append('trigger', params.trigger)
    if (params?.since) query.append('since', params.since)
    if (params?.until) query.append('until', params.until)
    return request<PlayerSnapshot[]>(`/snapshots/players/${uuid}?${query.toString()}`, () => [])
  },
  getLatestSnapshot: (uuid: string) => request<PlayerSnapshot>(`/snapshots/players/${uuid}/latest`, () => null),
  getSnapshot: (snapshotId: string) => request<PlayerSnapshot>(`/snapshots/${snapshotId}`, () => null),
  getSnapshotsNearReplay: (replayId: string, params?: { window_minutes?: number }) => {
    const query = new URLSearchParams()
    if (params?.window_minutes) query.append('window_minutes', params.window_minutes.toString())
    return request<PlayerSnapshot[]>(`/snapshots/replay/${replayId}?${query.toString()}`, () => [])
  },
  getAITasks: (params?: { status?: string, task_type?: string, skip?: number, limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.status) query.append('status', params.status)
    if (params?.task_type) query.append('task_type', params.task_type)
    if (params?.skip) query.append('skip', params.skip.toString())
    if (params?.limit) query.append('limit', params.limit.toString())
    return request<AITask[]>(`/ai/tasks?${query.toString()}`, () => [])
  },
  getAITask: (taskId: number) => request<AITask>(`/ai/tasks/${taskId}`, () => null as AITask | null),
  approveAITask: (taskId: number, payload: { action_taken: string, reviewed_by: string }) =>
    request<AITask>(`/ai/tasks/${taskId}/approve`, () => null as AITask | null, { method: 'POST', body: JSON.stringify(payload) }),
  denyAITask: (taskId: number, payload: { reviewed_by: string, reason?: string }) =>
    request<AITask>(`/ai/tasks/${taskId}/deny`, () => null as AITask | null, { method: 'POST', body: JSON.stringify(payload) }),
  triggerPlayerReview: (uuid: string) =>
    request<AITask>(`/ai/review/player/${uuid}`, () => null as AITask | null, { method: 'POST' }),
  triggerAppealReview: (appealId: string) =>
    request<AITask>(`/ai/review/appeal/${appealId}`, () => null as AITask | null, { method: 'POST' }),
  getPlayerLanguages: () => request<any[]>('/translation/language/all', () => []),
  setPlayerLanguage: (player_uuid: string, language_code: string, language_name: string) =>
    request<any>('/translation/language', () => null, {
      method: 'POST',
      body: JSON.stringify({ player_uuid, language_code, language_name }),
    }),
  requestAIConfig: (action_type: string, natural_language: string) =>
    request<any>('/ai/config/request', () => null, {
      method: 'POST',
      body: JSON.stringify({ action_type, natural_language }),
    }),
  getPendingAIConfigs: () => request<any[]>('/ai/config/pending', () => []),
  approveAIConfig: (id: number) =>
    request<any>(`/ai/config/${id}/approve`, () => null, { method: 'POST' }),
  rejectAIConfig: (id: number) =>
    request<any>(`/ai/config/${id}/reject`, () => null, { method: 'POST' }),
}
