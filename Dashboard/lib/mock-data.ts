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

// Seeded pseudo-random for stable mock data between renders.
let seed = 1337
function rng() {
  seed = (seed * 9301 + 49297) % 233280
  return seed / 233280
}
function pick<T>(arr: T[]): T {
  return arr[Math.floor(rng() * arr.length)]
}
function int(min: number, max: number) {
  return Math.floor(rng() * (max - min + 1)) + min
}
function uuid() {
  const h = () => Math.floor(rng() * 0xffff).toString(16).padStart(4, '0')
  return `${h()}${h()}-${h()}-${h()}-${h()}-${h()}${h()}${h()}`
}
function daysAgo(d: number) {
  return new Date(Date.now() - d * 86400000).toISOString()
}
function hoursAgo(h: number) {
  return new Date(Date.now() - h * 3600000).toISOString()
}

const USERNAMES = [
  'CraftKing', 'EnderByte', 'PixelWarden', 'NovaMiner', 'ShadowReef', 'BlazeRunner',
  'FrostQuill', 'IronGale', 'VoidSeeker', 'LumenWisp', 'AshenFox', 'CobaltDrift',
  'QuartzVein', 'RuneSmith', 'TidalGlyph', 'EmberHollow', 'GildedMoth', 'StoneVane',
  'HazelCircuit', 'MossWatcher', 'ArcLamplight', 'DuskRavine', 'PaleLantern', 'OakenTally',
  'SableCrest', 'VerdantHex', 'CinderLark', 'GlassPrairie', 'NightFurrow', 'BronzeAtlas',
  'SilentCog', 'AmberToad', 'PineHerald', 'CrowMantle', 'FlintWidow', 'TealNomad',
]
const COUNTRIES = ['US', 'GB', 'DE', 'CA', 'AU', 'BR', 'FR', 'NL', 'SE', 'PL']
const SERVER_NAMES = ['lobby-01', 'survival-01', 'survival-02', 'skyblock-01', 'minigames-01', 'creative-01']
const STAFF_NAMES = ['Aurora', 'Helios', 'Vesper', 'Orion', 'Lyra', 'Atlas', 'Selene', 'Caelum']
const PUNISHMENT_REASONS = [
  'Hacked client (KillAura)', 'Chat spam', 'Toxic behavior', 'Advertising', 'X-Ray usage',
  'Fly hacks', 'Griefing', 'Inappropriate name', 'Bug abuse', 'Account sharing', 'Bypassing mute',
]

function makePlayer(i: number): Player {
  const username = USERNAMES[i % USERNAMES.length] + (i >= USERNAMES.length ? i : '')
  const status = rng() > 0.65 ? 'online' : 'offline'
  const ipCount = int(1, 5)
  const ips = Array.from({ length: ipCount }).map(() => ({
    address: `${int(11, 220)}.${int(0, 255)}.${int(0, 255)}.${int(1, 254)}`,
    firstSeen: daysAgo(int(30, 400)),
    lastSeen: daysAgo(int(0, 12)),
    usageCount: int(3, 900),
    flagged: rng() > 0.82,
    country: pick(COUNTRIES),
  }))
  const punishmentCount = int(0, 6)
  const risk = Math.min(
    100,
    punishmentCount * 9 + ips.filter((x) => x.flagged).length * 22 + int(0, 25),
  )
  return {
    uuid: uuid(),
    username,
    status,
    riskScore: risk,
    discordLinked: rng() > 0.4,
    discordTag: rng() > 0.4 ? `${username.toLowerCase()}#${int(1000, 9999)}` : undefined,
    firstSeen: daysAgo(int(40, 900)),
    lastSeen: status === 'online' ? new Date().toISOString() : hoursAgo(int(1, 600)),
    playtimeHours: int(2, 1800),
    joins: int(5, 4200),
    deaths: int(0, 950),
    punishmentCount,
    knownIpCount: ipCount,
    ips,
    currentServer: status === 'online' ? pick(SERVER_NAMES) : undefined,
  }
}

export const players: Player[] = Array.from({ length: 64 }).map((_, i) => makePlayer(i))

export const punishments: Punishment[] = Array.from({ length: 80 }).map((_, i) => {
  const p = players[i % players.length]
  const type = pick(['warn', 'mute', 'tempban', 'ban'] as const)
  const created = int(0, 90)
  const isPermanent = type === 'ban' && rng() > 0.5
  const statusRoll = rng()
  const status =
    statusRoll > 0.82 ? 'revoked' : statusRoll > 0.66 ? 'appealed' : statusRoll > 0.4 ? 'expired' : 'active'
  return {
    id: `PUN-${(1000 + i).toString()}`,
    playerUuid: p.uuid,
    playerName: p.username,
    type,
    reason: pick(PUNISHMENT_REASONS),
    staff: pick(STAFF_NAMES),
    createdAt: daysAgo(created),
    expiresAt: isPermanent ? null : daysAgo(created - int(1, 30)),
    status,
  }
})

export const appeals: Appeal[] = Array.from({ length: 28 }).map((_, i) => {
  const pun = punishments[i * 2]
  const status = pick(['open', 'open', 'accepted', 'denied', 'escalated'] as const)
  return {
    id: `APL-${(2000 + i).toString()}`,
    playerUuid: pun.playerUuid,
    playerName: pun.playerName,
    punishmentId: pun.id,
    punishmentType: pun.type,
    reason: pun.reason,
    message:
      'I believe this punishment was issued in error. I was not using any unfair advantage and would appreciate a review of the logs from that session.',
    status,
    createdAt: daysAgo(int(0, 20)),
    assignedTo: status === 'open' ? undefined : pick(STAFF_NAMES),
    staffNotes:
      status === 'denied'
        ? 'Logs confirm anomalous reach values. Appeal denied.'
        : status === 'accepted'
          ? 'False positive from anti-cheat. Punishment reversed.'
          : undefined,
    messages: [
      { author: pun.playerName, role: 'player', message: 'Please review my case, this was a mistake.', at: daysAgo(int(1, 19)) },
      ...(status !== 'open'
        ? [{ author: pick(STAFF_NAMES), role: 'staff' as const, message: 'Thanks, reviewing the session logs now.', at: daysAgo(int(0, 1)) }]
        : []),
    ],
  }
})

export const staff: StaffMember[] = STAFF_NAMES.map((name, i) => ({
  id: `STF-${i + 1}`,
  username: name,
  role: i === 0 ? 'Owner' : i < 3 ? 'Admin' : i < 6 ? 'Moderator' : 'Helper',
  joinedAt: daysAgo(int(120, 900)),
  lastActive: hoursAgo(int(0, 72)),
  actionsThisWeek: int(4, 180),
  status: rng() > 0.5 ? 'online' : 'offline',
}))

export const roles: RoleDefinition[] = [
  {
    role: 'Owner',
    description: 'Full unrestricted access to every subsystem and configuration.',
    memberCount: staff.filter((s) => s.role === 'Owner').length,
    permissions: ['*', 'settings.write', 'staff.manage', 'server.control', 'billing'],
  },
  {
    role: 'Admin',
    description: 'Manage staff, servers, plugins and network-wide settings.',
    memberCount: staff.filter((s) => s.role === 'Admin').length,
    permissions: ['staff.manage', 'punishments.*', 'server.control', 'plugins.manage', 'settings.read'],
  },
  {
    role: 'Moderator',
    description: 'Issue and revoke punishments, review and resolve appeals.',
    memberCount: staff.filter((s) => s.role === 'Moderator').length,
    permissions: ['punishments.create', 'punishments.revoke', 'appeals.resolve', 'players.view'],
  },
  {
    role: 'Helper',
    description: 'Front-line support with limited moderation capabilities.',
    memberCount: staff.filter((s) => s.role === 'Helper').length,
    permissions: ['punishments.warn', 'punishments.mute', 'players.view', 'appeals.view'],
  },
]

export const servers: MinecraftServer[] = SERVER_NAMES.map((name, i) => {
  const status = i === 4 ? 'maintenance' : rng() > 0.92 ? 'offline' : 'online'
  return {
    id: `SRV-${i + 1}`,
    name,
    status,
    tps: status === 'online' ? +(17 + rng() * 3).toFixed(1) : 0,
    players: status === 'online' ? int(8, 240) : 0,
    maxPlayers: 300,
    ramUsedMb: int(2400, 11800),
    ramTotalMb: 12288,
    cpu: status === 'online' ? int(18, 88) : 0,
    version: pick(['1.20.4', '1.20.6', '1.21.1']),
    pluginsConnected: int(6, 12),
    pluginsTotal: 12,
  }
})

const PLUGIN_NAMES = [
  'UmbrellaBridge', 'AntiCheatLink', 'ChatGuard', 'EconomyCore', 'PunishSync',
  'StaffTools', 'QueueManager', 'PlaytimeTracker', 'DiscordRelay', 'WorldGuardLink',
]
export const plugins: Plugin[] = PLUGIN_NAMES.map((name, i) => {
  const status = pick(['connected', 'connected', 'connected', 'degraded', 'disconnected'] as const)
  return {
    id: `PLG-${(100 + i).toString()}`,
    name,
    version: `${int(1, 4)}.${int(0, 9)}.${int(0, 9)}`,
    server: pick(SERVER_NAMES),
    status,
    heartbeatMs: status === 'connected' ? int(20, 400) : status === 'degraded' ? int(900, 2400) : 0,
    lastSeen: status === 'disconnected' ? hoursAgo(int(2, 40)) : new Date().toISOString(),
  }
})

const AUDIT_ACTIONS = [
  { action: 'Issued ban', category: 'moderation' as const },
  { action: 'Revoked mute', category: 'moderation' as const },
  { action: 'Accepted appeal', category: 'appeal' as const },
  { action: 'Updated setting', category: 'settings' as const },
  { action: 'Promoted staff', category: 'staff' as const },
  { action: 'Restarted server', category: 'server' as const },
  { action: 'Reloaded plugin', category: 'plugin' as const },
  { action: 'Signed in', category: 'auth' as const },
]
export const audit: AuditEntry[] = Array.from({ length: 120 }).map((_, i) => {
  const a = pick(AUDIT_ACTIONS)
  const actor = pick(STAFF_NAMES)
  return {
    id: `AUD-${(5000 + i).toString()}`,
    timestamp: hoursAgo(i * 0.7 + rng()),
    actor,
    actorRole: staff.find((s) => s.username === actor)?.role ?? 'Moderator',
    action: a.action,
    target: pick([...players.map((p) => p.username), ...SERVER_NAMES, ...PLUGIN_NAMES]),
    category: a.category,
    ip: `${int(11, 220)}.${int(0, 255)}.${int(0, 255)}.${int(1, 254)}`,
  }
})

function spark(n: number, base: number, variance: number) {
  return Array.from({ length: n }).map(() => Math.round(base + (rng() - 0.5) * variance))
}

export const dashboard: DashboardData = {
  cards: [
    { id: 'online', label: 'Online Players', value: '1,284', rawValue: 1284, changePct: 12.4, trend: 'up', spark: spark(16, 1200, 300) },
    { id: 'today', label: 'Players Today', value: '8,932', rawValue: 8932, changePct: 6.1, trend: 'up', spark: spark(16, 8500, 1200) },
    { id: 'joins', label: 'Joins Today', value: '14,205', rawValue: 14205, changePct: 3.4, trend: 'up', spark: spark(16, 14000, 2000) },
    { id: 'deaths', label: 'Deaths Today', value: '3,418', rawValue: 3418, changePct: -2.1, trend: 'down', spark: spark(16, 3400, 600) },
    { id: 'punishments', label: 'Punishments Today', value: '212', rawValue: 212, changePct: 18.9, trend: 'up', spark: spark(16, 190, 80), intent: 'danger' },
    { id: 'appeals', label: 'Open Appeals', value: '17', rawValue: 17, changePct: -8.0, trend: 'down', spark: spark(16, 20, 10), intent: 'warning' },
    { id: 'cpu', label: 'CPU Usage', value: '62%', rawValue: 62, changePct: 4.2, trend: 'up', spark: spark(16, 60, 20), intent: 'warning' },
    { id: 'ram', label: 'RAM Usage', value: '71%', rawValue: 71, changePct: 1.8, trend: 'up', spark: spark(16, 70, 14), intent: 'warning' },
    { id: 'disk', label: 'Disk Usage', value: '48%', rawValue: 48, changePct: 0.4, trend: 'flat', spark: spark(16, 48, 6) },
    { id: 'heartbeats', label: 'Plugin Heartbeats', value: '9 / 10', rawValue: 9, changePct: 0, trend: 'flat', spark: spark(16, 9, 2), intent: 'success' },
    { id: 'tps', label: 'Avg Server TPS', value: '19.6', rawValue: 19.6, changePct: 0.6, trend: 'up', spark: spark(16, 19, 2), intent: 'success' },
    { id: 'health', label: 'Network Health', value: '98.7%', rawValue: 98.7, changePct: 0.2, trend: 'up', spark: spark(16, 98, 3), intent: 'success' },
  ],
  activity: Array.from({ length: 24 }).map((_, h) => {
    const peak = 600 + Math.round(Math.sin((h / 24) * Math.PI * 2 - 1.5) * 500 + 700)
    return {
      hour: `${h.toString().padStart(2, '0')}:00`,
      joins: Math.max(40, peak / 6 + int(-40, 60)),
      leaves: Math.max(30, peak / 7 + int(-40, 50)),
      peak: Math.max(120, peak + int(-80, 80)),
    }
  }),
  punishments: Array.from({ length: 14 }).map((_, d) => ({
    day: daysAgo(13 - d).slice(5, 10),
    warns: int(20, 60),
    mutes: int(10, 40),
    tempbans: int(4, 22),
    bans: int(1, 12),
  })),
  appeals: Array.from({ length: 14 }).map((_, d) => ({
    day: daysAgo(13 - d).slice(5, 10),
    open: int(3, 16),
    accepted: int(1, 9),
    denied: int(1, 11),
  })),
}

export const analytics: AnalyticsData = {
  playerGrowth: Array.from({ length: 30 }).map((_, d) => ({
    label: daysAgo(29 - d).slice(5, 10),
    value: 6000 + d * 110 + int(-300, 400),
  })),
  retention: [
    { label: 'D1', value: 68 },
    { label: 'D3', value: 51 },
    { label: 'D7', value: 39 },
    { label: 'D14', value: 28 },
    { label: 'D30', value: 19 },
  ],
  punishmentFrequency: dashboard.punishments,
  appealSuccess: [
    { name: 'Accepted', value: 42 },
    { name: 'Denied', value: 51 },
    { name: 'Escalated', value: 7 },
  ],
  peakHours: Array.from({ length: 24 }).map((_, h) => ({
    label: `${h}:00`,
    value: 600 + Math.round(Math.sin((h / 24) * Math.PI * 2 - 1.5) * 500 + 700) + int(-60, 60),
  })),
  serverPerformance: servers.map((s) => ({ name: s.name, tps: s.tps, cpu: s.cpu })),
  riskDistribution: [
    { name: 'Low (0-25)', value: 38 },
    { name: 'Moderate (26-50)', value: 16 },
    { name: 'High (51-75)', value: 7 },
    { name: 'Critical (76-100)', value: 3 },
  ],
  topStaff: staff
    .map((s) => ({ name: s.username, actions: s.actionsThisWeek }))
    .sort((a, b) => b.actions - a.actions)
    .slice(0, 6),
}

export const settings: SettingsCategory[] = [
  {
    id: 'general',
    label: 'General',
    items: [
      { key: 'network.name', label: 'Network Name', description: 'Public display name of the network.', type: 'text', value: 'UmbrellaCraft Network' },
      { key: 'network.motd', label: 'MOTD', description: 'Message of the day shown in the server list.', type: 'text', value: 'Welcome to the grid.' },
      { key: 'network.maxPlayers', label: 'Max Players', description: 'Global concurrent player cap.', type: 'number', value: 3000, restartRequired: true },
      { key: 'network.maintenance', label: 'Maintenance Mode', description: 'Restrict the network to staff only.', type: 'boolean', value: false },
    ],
  },
  {
    id: 'discord',
    label: 'Discord',
    items: [
      { key: 'discord.token', label: 'Bot Token', description: 'Discord bot authentication token.', type: 'secret', value: 'MTEyMzQ1Njc4OTAxMjM0NTY3OA.GaBcDe.fGhIjKlMnOpQ' },
      { key: 'discord.guild', label: 'Guild ID', description: 'Primary Discord server ID.', type: 'text', value: '849201337420690000' },
      { key: 'discord.linkRequired', label: 'Require Link', description: 'Require Discord link to join.', type: 'boolean', value: false },
    ],
  },
  {
    id: 'ai',
    label: 'AI',
    items: [
      { key: 'ai.enabled', label: 'AI Moderation', description: 'Enable AI-assisted chat and behavior analysis.', type: 'boolean', value: true },
      { key: 'ai.sensitivity', label: 'Sensitivity', description: 'Detection sensitivity level.', type: 'select', value: 'balanced', options: ['lenient', 'balanced', 'strict'] },
      { key: 'ai.apiKey', label: 'Model API Key', description: 'Key for the inference provider.', type: 'secret', value: 'sk-umbr-9f8a7b6c5d4e3f2a1b0c' },
    ],
  },
  {
    id: 'moderation',
    label: 'Moderation',
    items: [
      { key: 'mod.autoBanThreshold', label: 'Auto-Ban Risk Threshold', description: 'Risk score that triggers auto-ban review.', type: 'number', value: 90 },
      { key: 'mod.muteDefault', label: 'Default Mute (min)', description: 'Default mute duration in minutes.', type: 'number', value: 60 },
      { key: 'mod.appealCooldown', label: 'Appeal Cooldown (h)', description: 'Hours before a player can re-appeal.', type: 'number', value: 24 },
    ],
  },
  {
    id: 'network',
    label: 'Network',
    items: [
      { key: 'net.proxy', label: 'Proxy Host', description: 'Velocity proxy bind address.', type: 'text', value: '0.0.0.0:25565', restartRequired: true },
      { key: 'net.compression', label: 'Compression Threshold', description: 'Packet compression threshold in bytes.', type: 'number', value: 256 },
    ],
  },
  {
    id: 'security',
    label: 'Security',
    items: [
      { key: 'sec.2fa', label: 'Require 2FA for Staff', description: 'Enforce two-factor for all staff accounts.', type: 'boolean', value: true },
      { key: 'sec.ipWhitelist', label: 'Panel IP Whitelist', description: 'Restrict panel access to listed CIDRs.', type: 'boolean', value: false },
      { key: 'sec.sessionTtl', label: 'Session TTL (min)', description: 'Idle session expiry in minutes.', type: 'number', value: 120 },
    ],
  },
  {
    id: 'database',
    label: 'Database',
    items: [
      { key: 'db.url', label: 'Connection String', description: 'Primary PostgreSQL connection URL.', type: 'secret', value: 'postgresql://umbrella:****@db.internal:5432/core' },
      { key: 'db.poolSize', label: 'Pool Size', description: 'Maximum DB connection pool size.', type: 'number', value: 40, restartRequired: true },
    ],
  },
  {
    id: 'api',
    label: 'API',
    items: [
      { key: 'api.baseUrl', label: 'Core Base URL', description: 'Base URL of the Umbrella Core service.', type: 'text', value: 'https://core.umbrella.internal/api' },
      { key: 'api.rateLimit', label: 'Rate Limit (req/min)', description: 'Per-key request rate limit.', type: 'number', value: 600 },
      { key: 'api.key', label: 'Service API Key', description: 'Key used by plugins to authenticate.', type: 'secret', value: 'umbr_live_3f9a2b7c1d8e4f5a6b9c0d1e' },
    ],
  },
]

export const systemMetrics: SystemMetrics = {
  apiLatencyMs: 42,
  memoryUsedPct: 71,
  cpuPct: 62,
  diskPct: 48,
  connections: 1284,
  components: [
    { id: 'core', label: 'Umbrella Core', status: 'healthy', detail: 'All endpoints responding', latencyMs: 42 },
    { id: 'db', label: 'PostgreSQL', status: 'healthy', detail: '40/40 pool, 2.1ms avg query', latencyMs: 2 },
    { id: 'redis', label: 'Redis Cache', status: 'healthy', detail: 'Hit rate 98.2%', latencyMs: 1 },
    { id: 'plugins', label: 'Plugin Mesh', status: 'degraded', detail: '9 of 10 plugins connected', latencyMs: 380 },
    { id: 'heartbeat', label: 'Heartbeat Monitor', status: 'healthy', detail: 'Last sweep 4s ago' },
    { id: 'gateway', label: 'API Gateway', status: 'healthy', detail: '600 req/min limit, 41% utilized', latencyMs: 12 },
  ],
  latencyHistory: Array.from({ length: 30 }).map((_, i) => ({
    label: `${i}`,
    value: 40 + Math.round((rng() - 0.5) * 30) + (i === 14 ? 60 : 0),
  })),
}
