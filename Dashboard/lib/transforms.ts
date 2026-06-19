import type {
  Appeal, AuditEntry, BridgeSettings, DashboardData, Player, Punishment,
  RoleDefinition, SettingsCategory, SettingItem, StaffMember, ServerSummary,
  SystemMetrics, MinecraftServer, Plugin,
} from './types'

const CATEGORY_LABELS: Record<string, string> = {
  server: 'General', discord: 'Discord', ai: 'AI', moderation: 'Moderation',
  anticheat: 'Anti-Cheat', bridge: 'Bridge', rcon: 'Network', sync: 'Network', security: 'Security',
}

const BOOL_KEYS = new Set([
  'anticheat.enabled', 'anticheat.auto_tempban', 'moderation.require_discord_link',
  'bridge.mc_to_discord', 'bridge.discord_to_mc', 'bridge.show_avatars',
])

const SELECT_KEYS: Record<string, string[]> = {
  'bridge.mode': ['off', 'partial', 'full'],
}

export function mapPunishment(p: Record<string, unknown>): Punishment {
  return {
    id: String(p.id),
    playerUuid: String(p.player_uuid),
    playerName: String(p.player_name || ''),
    type: p.type as Punishment['type'],
    reason: String(p.reason),
    staff: String(p.staff_id || 'system'),
    createdAt: String(p.created_at),
    expiresAt: p.expires_at ? String(p.expires_at) : null,
    status: p.active ? 'active' : 'revoked',
  }
}

export function mapAppeal(a: Record<string, unknown>): Appeal {
  const raw = String(a.status)
  const status = raw === 'pending' ? 'open' : raw === 'approved' ? 'accepted' : raw as Appeal['status']
  return {
    id: String(a.id), playerUuid: String(a.player_uuid), playerName: '',
    punishmentId: String(a.punishment_id), punishmentType: 'warn', reason: '',
    message: String(a.message), status, createdAt: String(a.created_at), messages: [],
  }
}

export function mapPlayer(p: Record<string, unknown>): Player {
  return {
    uuid: String(p.uuid), username: String(p.username), status: 'offline',
    riskScore: Number(p.risk_score || 0), discordLinked: !!p.discord_id,
    firstSeen: String(p.first_seen), lastSeen: String(p.last_seen),
    playtimeHours: Math.round(Number(p.playtime || 0) / 3600),
    joins: Number(p.joins || 0), deaths: Number(p.deaths || 0),
    punishmentCount: 0, knownIpCount: 0,
  }
}

export function mapStaff(users: Record<string, unknown>[], roles: Record<string, unknown>[]): StaffMember[] {
  const roleMap = new Map(roles.map((r) => [String(r.id), String(r.name)]))
  return users.map((u) => ({
    id: String(u.id), username: String(u.username),
    role: (roleMap.get(String(u.role_id)) || 'Helper') as StaffMember['role'],
    roleId: u.role_id ? String(u.role_id) : undefined,
    joinedAt: String(u.created_at), lastActive: String(u.updated_at || u.created_at),
    actionsThisWeek: 0, status: u.is_active ? 'online' : 'offline',
  }))
}

export function mapRoles(roles: Record<string, unknown>[]): RoleDefinition[] {
  const title = (n: string) => n.charAt(0).toUpperCase() + n.slice(1) as RoleDefinition['role']
  return roles.map((r) => ({
    role: title(String(r.name)),
    description: String(r.description || ''),
    memberCount: Number(r.member_count || 0),
    permissions: (r.permissions as string[]) || [],
  }))
}

export function mapAudit(data: { entries?: Record<string, unknown>[] }): AuditEntry[] {
  return (data.entries || []).map((e) => ({
    id: String(e.id), timestamp: String(e.created_at),
    actor: String(e.actor), actorRole: String(e.actor_type),
    action: String(e.action), target: String(e.target || ''),
    category: 'moderation' as AuditEntry['category'],
    details: String(e.details || e.details_json || ''),
    ip: '',
  }))
}

export function mapSettings(flat: Record<string, unknown>[]): SettingsCategory[] {
  const groups = new Map<string, SettingItem[]>()
  for (const s of flat) {
    const key = String(s.key)
    const cat = String(s.category || 'server')
    const val = String(s.value ?? '')
    let type: SettingItem['type'] = 'text'
    if (s.sensitive) type = 'secret'
    else if (BOOL_KEYS.has(key) || val === 'true' || val === 'false') type = 'boolean'
    else if (SELECT_KEYS[key]) type = 'select'
    else if (/^\d+$/.test(val) && !key.includes('channel')) type = 'number'
    const item: SettingItem = {
      key, label: key.split('.').pop()?.replace(/_/g, ' ') || key,
      description: String(s.description || ''), type, value: val,
      options: SELECT_KEYS[key], restartRequired: Boolean(s.requires_restart),
    }
    if (!groups.has(cat)) groups.set(cat, [])
    groups.get(cat)!.push(item)
  }
  return Array.from(groups.entries()).map(([id, items]) => ({
    id, label: CATEGORY_LABELS[id] || id.charAt(0).toUpperCase() + id.slice(1), items,
  }))
}

export function mapServer(h: Record<string, unknown>): MinecraftServer {
  return {
    id: String(h.id), name: String(h.name), status: h.status as MinecraftServer['status'],
    tps: Number(h.tps || 0), players: Number(h.players || 0), maxPlayers: Number(h.maxPlayers || 100),
    ramUsedMb: 0, ramTotalMb: 0, cpu: 0, version: String(h.version || ''),
    pluginsConnected: Number(h.pluginsConnected || 0), pluginsTotal: Number(h.pluginsTotal || 0),
  }
}

export function mapPlugin(p: Record<string, unknown>): Plugin {
  return {
    id: String(p.id), name: String(p.name), version: String(p.version),
    server: String(p.server), status: p.status as Plugin['status'],
    heartbeatMs: Number(p.heartbeatMs || 0), lastSeen: String(p.lastSeen || ''),
  }
}

export function buildDashboard(
  punishments: Punishment[], appeals: Appeal[], summary: ServerSummary,
): DashboardData {
  const activePunishments = punishments.filter((p) => p.status === 'active').length
  const openAppeals = appeals.filter((a) => a.status === 'open').length
  const cards = [
    { id: 'punishments', label: 'Active Punishments', value: String(activePunishments), rawValue: activePunishments, changePct: 0, trend: 'flat' as const, spark: Array(16).fill(activePunishments), intent: activePunishments > 50 ? 'danger' as const : 'success' as const },
    { id: 'appeals', label: 'Open Appeals', value: String(openAppeals), rawValue: openAppeals, changePct: 0, trend: 'flat' as const, spark: Array(16).fill(openAppeals), intent: openAppeals > 10 ? 'warning' as const : 'success' as const },
    { id: 'joins', label: 'Total Joins', value: String(summary.joins), rawValue: summary.joins, changePct: 0, trend: 'flat' as const, spark: Array(16).fill(summary.joins) },
    { id: 'deaths', label: 'Total Deaths', value: String(summary.deaths), rawValue: summary.deaths, changePct: 0, trend: 'flat' as const, spark: Array(16).fill(summary.deaths) },
  ]
  const activity = Array.from({ length: 24 }).map((_, h) => ({
    hour: `${h.toString().padStart(2, '0')}:00`,
    joins: Math.round(summary.joins / 24), leaves: Math.round(summary.leaves / 24),
    peak: Math.round(summary.joins / 10),
  }))
  const punishmentCounts: Record<string, { day: string; warns: number; mutes: number; tempbans: number; bans: number }> = {}
  punishments.forEach((p) => {
    const day = p.createdAt.slice(5, 10)
    if (!punishmentCounts[day]) punishmentCounts[day] = { day, warns: 0, mutes: 0, tempbans: 0, bans: 0 }
    if (p.type === 'warn') punishmentCounts[day].warns++
    else if (p.type === 'mute') punishmentCounts[day].mutes++
    else if (p.type === 'tempban') punishmentCounts[day].tempbans++
    else if (p.type === 'ban') punishmentCounts[day].bans++
  })
  const appealCounts: Record<string, { day: string; open: number; accepted: number; denied: number }> = {}
  appeals.forEach((a) => {
    const day = a.createdAt.slice(5, 10)
    if (!appealCounts[day]) appealCounts[day] = { day, open: 0, accepted: 0, denied: 0 }
    if (a.status === 'open') appealCounts[day].open++
    else if (a.status === 'accepted') appealCounts[day].accepted++
    else if (a.status === 'denied') appealCounts[day].denied++
  })
  return {
    cards, activity,
    punishments: Object.values(punishmentCounts).sort((a, b) => a.day.localeCompare(b.day)),
    appeals: Object.values(appealCounts).sort((a, b) => a.day.localeCompare(b.day)),
  }
}

export function mapHealth(h: Record<string, unknown>): SystemMetrics {
  const ok = h.status === 'ok'
  return {
    coreStatus: ok ? 'online' : 'degraded',
    database: h.database === 'connected' ? 'connected' : 'disconnected',
    apiLatencyMs: 0, activeConnections: 0, requestsPerMinute: 0,
    errorRate: ok ? 0 : 5, uptime: '—', version: String(h.version || '1.0.0'),
    components: [
      { name: 'API', status: ok ? 'healthy' : 'degraded', latencyMs: 0 },
      { name: 'Database', status: h.database === 'connected' ? 'healthy' : 'down', latencyMs: 0 },
    ],
    latencyHistory: Array(20).fill(0),
    cpuPercent: 0, memoryPercent: 0, diskPercent: 0,
  }
}

export function appealStatusToApi(status: string): string {
  if (status === 'open') return 'pending'
  if (status === 'accepted') return 'approved'
  return status
}
