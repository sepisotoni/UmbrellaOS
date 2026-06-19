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
  roleId?: string
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

export type BridgeMode = 'off' | 'partial' | 'full'

export interface BridgeSettings {
  mode: BridgeMode
  mc_to_discord: boolean
  discord_to_mc: boolean
  show_avatars: boolean
  discord_channel_id: string
}

export interface VerificationCode {
  id: number
  player_uuid: string
  player_username: string
  code: string
  created_at: string
  expires_at: string
  used: boolean
  ip_address: string | null
}

export interface VerificationStatus {
  verified: boolean
  discord_id?: string
  discord_username?: string
}

export interface SuspicionEvent {
  id: number
  player_uuid: string
  trigger: string
  points: number
  metadata_json: string | null
  created_at: string
  reviewed: boolean
  reviewed_by: string | null
  false_positive: boolean
}

export interface AltGroup {
  id: number
  created_at: string
  notes: string | null
  confirmed: boolean
}

export interface AltGroupMember {
  id: number
  group_id: number
  player_uuid: string
  added_at: string
  added_by: string | null
}

export interface FlaggedPlayer {
  uuid: string
  username: string
  suspicion_score: number
  created_at: string
}

export interface AnalyticsEvent {
  id: string
  event_type: string
  minecraft_uuid: string | null
  data_json: string | null
  created_at: string
}

export interface PlayerStat {
  metric: string
  value: number
  period: string
  period_start: string
  updated_at: string
}

export interface ServerSummary {
  joins: number
  leaves: number
  deaths: number
  kills: number
  chat_volume: number
  playtime_seconds: number
}

export interface AnalyticsEventsResponse {
  events: AnalyticsEvent[]
}

export interface ReplaySession {
  id: string
  trigger: string
  triggered_by: string
  minecraft_uuid: string
  started_at: string
  incident_at: string
  ended_at: string | null
  event_count: number
  created_at: string
  notes: string | null
}

export interface ReplayEvent {
  id: string
  replay_id: string
  minecraft_uuid: string
  event_type: string
  event_data_json: string
  timestamp: string
  world: string | null
}

export interface PlayerSnapshot {
  id: string
  minecraft_uuid: string
  timestamp: string
  trigger: string
  health: number | null
  food: number | null
  xp: number | null
  inventory_json: string | null
  armor_json: string | null
  offhand_json: string | null
  x: number | null
  y: number | null
  z: number | null
  yaw: number | null
  pitch: number | null
  world: string | null
  dimension: string | null
  replay_id: string | null
}

export type AITaskStatus = "pending" | "approved" | "denied" | "expired"

export interface AITask {
  id: number
  task_type: string
  status: AITaskStatus
  player_uuid: string | null
  created_at: string
  expires_at: string
  ai_summary: string
  ai_recommendation: string
  ai_confidence: number
  evidence: string | null
  reviewed_by: string | null
  reviewed_at: string | null
  action_taken: string | null
}
