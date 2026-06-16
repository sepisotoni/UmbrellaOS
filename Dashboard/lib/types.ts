// UmbrellaOS domain types — mirror the Umbrella Core REST API contracts.

export type PlayerStatus = 'online' | 'offline'

export interface PlayerIP {
  address: string
  firstSeen: string
  lastSeen: string
  usageCount: number
  flagged: boolean
  country: string
}

export interface Player {
  uuid: string
  username: string
  status: PlayerStatus
  riskScore: number
  discordLinked: boolean
  discordTag?: string
  firstSeen: string
  lastSeen: string
  playtimeHours: number
  joins: number
  deaths: number
  punishmentCount: number
  knownIpCount: number
  ips?: PlayerIP[]
  currentServer?: string
}

export type PunishmentType = 'warn' | 'mute' | 'tempban' | 'ban'
export type PunishmentStatus = 'active' | 'expired' | 'revoked' | 'appealed'

export interface Punishment {
  id: string
  playerUuid: string
  playerName: string
  type: PunishmentType
  reason: string
  staff: string
  createdAt: string
  expiresAt: string | null
  status: PunishmentStatus
}

export type AppealStatus = 'open' | 'accepted' | 'denied' | 'escalated'

export interface AppealMessage {
  author: string
  role: 'player' | 'staff'
  message: string
  at: string
}

export interface Appeal {
  id: string
  playerUuid: string
  playerName: string
  punishmentId: string
  punishmentType: PunishmentType
  reason: string
  message: string
  status: AppealStatus
  createdAt: string
  assignedTo?: string
  staffNotes?: string
  messages: AppealMessage[]
}

export type StaffRole = 'Owner' | 'Admin' | 'Moderator' | 'Helper'

export interface StaffMember {
  id: string
  username: string
  role: StaffRole
  joinedAt: string
  lastActive: string
  actionsThisWeek: number
  status: PlayerStatus
}

export interface RoleDefinition {
  role: StaffRole
  description: string
  memberCount: number
  permissions: string[]
}

export type PluginStatus = 'connected' | 'degraded' | 'disconnected'

export interface Plugin {
  id: string
  name: string
  version: string
  server: string
  status: PluginStatus
  heartbeatMs: number
  lastSeen: string
}

export type ServerStatus = 'online' | 'maintenance' | 'offline'

export interface MinecraftServer {
  id: string
  name: string
  status: ServerStatus
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

export type AuditCategory =
  | 'moderation'
  | 'staff'
  | 'settings'
  | 'plugin'
  | 'server'
  | 'auth'
  | 'appeal'

export interface AuditEntry {
  id: string
  timestamp: string
  actor: string
  actorRole: StaffRole
  action: string
  target: string
  category: AuditCategory
  ip: string
}

export interface TrendPoint {
  label: string
  value: number
}

export interface StatCard {
  id: string
  label: string
  value: string
  rawValue: number
  changePct: number
  trend: 'up' | 'down' | 'flat'
  spark: number[]
  intent?: 'default' | 'success' | 'warning' | 'danger'
}

export interface ActivityPoint {
  hour: string
  joins: number
  leaves: number
  peak: number
}

export interface PunishmentPoint {
  day: string
  warns: number
  mutes: number
  tempbans: number
  bans: number
}

export interface AppealPoint {
  day: string
  open: number
  accepted: number
  denied: number
}

export type SettingType = 'text' | 'number' | 'boolean' | 'secret' | 'select'

export interface SettingItem {
  key: string
  label: string
  description: string
  type: SettingType
  value: string | number | boolean
  options?: string[]
  restartRequired?: boolean
}

export interface SettingsCategory {
  id: string
  label: string
  items: SettingItem[]
}

export type HealthStatus = 'healthy' | 'degraded' | 'down'

export interface HealthComponent {
  id: string
  label: string
  status: HealthStatus
  detail: string
  latencyMs?: number
}

export interface SystemMetrics {
  apiLatencyMs: number
  memoryUsedPct: number
  cpuPct: number
  diskPct: number
  connections: number
  components: HealthComponent[]
  latencyHistory: TrendPoint[]
}

export interface DashboardData {
  cards: StatCard[]
  activity: ActivityPoint[]
  punishments: PunishmentPoint[]
  appeals: AppealPoint[]
}

export interface AnalyticsData {
  playerGrowth: TrendPoint[]
  retention: TrendPoint[]
  punishmentFrequency: PunishmentPoint[]
  appealSuccess: { name: string; value: number }[]
  peakHours: TrendPoint[]
  serverPerformance: { name: string; tps: number; cpu: number }[]
  riskDistribution: { name: string; value: number }[]
  topStaff: { name: string; actions: number }[]
}
