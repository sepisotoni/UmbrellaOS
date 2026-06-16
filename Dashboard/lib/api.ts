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
  DashboardData,
  MinecraftServer,
  Player,
  Plugin,
  Punishment,
  RoleDefinition,
  SettingsCategory,
  StaffMember,
  SystemMetrics,
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
  
  if (ADMIN_KEY) {
    headers['X-Admin-Key'] = ADMIN_KEY
  }
  
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  })
  if (!res.ok) {
    throw new Error(`Umbrella Core request failed: ${res.status} ${path}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  getDashboard: () => request<DashboardData>('/stats', () => dashboard),
  getPlayers: () => request<Player[]>('/players', () => players),
  getPlayer: (uuid: string) =>
    request<Player | undefined>(`/players/${uuid}`, () =>
      players.find((p) => p.uuid === uuid),
    ),
  getPunishments: () => request<Punishment[]>('/punishments', () => punishments),
  getPlayerPunishments: (uuid: string) =>
    request<Punishment[]>('/punishments?player_uuid=' + uuid, () =>
      punishments.filter((p) => p.playerUuid === uuid),
    ),
  getAppeals: () => request<Appeal[]>('/appeals', () => appeals),
  getPlayerAppeals: (uuid: string) =>
    request<Appeal[]>('/appeals?player_uuid=' + uuid, () =>
      appeals.filter((a) => a.playerUuid === uuid),
    ),
  getStaff: () => request<StaffMember[]>('/staff', () => staff),
  getRoles: () => request<RoleDefinition[]>('/roles', () => roles),
  getPlugins: () => request<Plugin[]>('/plugins', () => plugins),
  getServers: () => request<MinecraftServer[]>('/servers', () => servers),
  getAnalytics: () => request<AnalyticsData>('/analytics', () => analytics),
  getSettings: () => request<SettingsCategory[]>('/settings', () => settings),
  getAudit: () => request<AuditEntry[]>('/audit', () => audit),
  getSystemHealth: () =>
    request<SystemMetrics>('/system/health', () => systemMetrics),
}
