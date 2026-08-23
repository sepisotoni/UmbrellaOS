export type ServerStatus = 'online' | 'warning' | 'offline' | 'starting' | 'restarting';
export type ServerType = 'velocity_proxy' | 'paper_lobby' | 'purpur_survival' | 'fabric_anarchy' | 'spigot_minigames';
export type DashboardTheme = 'cyber-ops' | 'solar-clean' | 'voxel-matrix' | 'obsidian-minimal';

export interface AuthUser {
  id: string;
  discordId?: string;
  username: string;
  discriminator?: string;
  avatarUrl?: string;
  role: 'superadmin' | 'admin' | 'moderator' | 'support' | 'developer' | 'viewer';
  permissions: string[];
  email?: string;
  linkedMinecraftUuid?: string;
  linkedMinecraftUsername?: string;
  sessionExpiry?: string;
}

export interface BackendPluginHeartbeat {
  id: string;
  name: string; // 'UmbrellaOS' | 'GrimAC'
  serverId: string;
  serverName?: string;
  version: string;
  status: 'healthy' | 'stale' | 'unreachable';
  lastSeen: string;
  heartbeatMs: number;
  activeFeatures?: string[];
}

export interface MinecraftServer {
  id: string;
  name: string;
  type: ServerType;
  version: string;
  status: ServerStatus;
  host: string;
  port: number;
  playersCount: number;
  maxPlayers: number;
  tps: number;
  cpuPercent: number;
  memoryMb: number;
  maxMemoryMb: number;
  uptimeSeconds: number;
  node: string;
  location: string;
  activePluginsCount: number;
  grimAcEnabled: boolean;
  // Backend real fields
  rawBackendData?: {
    ramUsedMb: number;
    ramTotalMb: number;
    cpu: number;
    pluginsConnected: number;
    pluginsTotal: number;
  };
}

export interface NodeInfrastructure {
  id: string;
  name: string;
  region: string;
  ip: string;
  status: 'healthy' | 'degraded' | 'unreachable';
  cpuCores: number;
  cpuUsage: number;
  ramGb: number;
  ramTotalGb: number;
  diskUsageGb: number;
  diskTotalGb: number;
  networkInMbps: number;
  networkOutMbps: number;
  pingMs: number;
  runningContainers: number;
  daemonVersion: string;
  assignedServers: string[];
}

export interface PlayerRecord {
  uuid: string;
  username: string;
  currentServer: string | null;
  online: boolean;
  ipAddress: string;
  firstJoined: string;
  lastSeen: string;
  playtimeHours: number;
  rank: 'Admin' | 'Moderator' | 'Helper' | 'MVP+' | 'VIP' | 'Player';
  suspicionScore: number; // 0 to 100
  pingMs: number;
  clientBrand: string;
  altAccountsCount: number;
  isVpn: boolean;
  warningCount: number;
  punishmentHistoryCount: number;
}

export interface PunishmentRecord {
  id: string;
  playerUuid: string;
  playerName: string;
  staffName: string;
  type: 'BAN' | 'TEMP_BAN' | 'MUTE' | 'TEMP_MUTE' | 'KICK' | 'WARN' | 'IP_BAN' | 'HWID_BAN';
  reason: string;
  status: 'ACTIVE' | 'EXPIRED' | 'PARDONED' | 'APPEALED';
  createdAt: string;
  expiresAt: string | null;
  serverScope: string; // 'GLOBAL' | serverId
  evidenceUrl?: string;
  appealId?: string;
}

export interface GrimACViolation {
  id: string;
  timestamp: string;
  playerUuid: string;
  playerName: string;
  server: string;
  checkName: 'Reach' | 'Velocity' | 'KillAura' | 'Speed' | 'Fly' | 'AutoClicker' | 'Timer' | 'BaritoneBot' | 'NoFall' | 'InventoryMove';
  violationLevel: number;
  confidencePercent: number;
  details: string;
  autoMitigationTaken: string | null; // e.g. 'Cancelled Packets', 'Flagged for Review', 'Auto-Ban'
  playerPing: number;
  tpsAtTime: number;
}

export interface AltAccountCluster {
  id: string;
  rootIdentifier: string; // e.g. "IP: 198.51.100.44" or "HWID: e3b0c44298fc"
  clusterType: 'IP_SHARED' | 'HWID_MATCH' | 'COOKIE_TOKEN' | 'SUBNET_BURST';
  confidence: number;
  primaryAccount: string;
  associatedAccounts: string[];
  bannedCount: number;
  status: 'INVESTIGATING' | 'CONFIRMED_ALT_RING' | 'WHITELISTED_HOUSEHOLD';
  notes: string;
}

export interface AppealTicket {
  id: string;
  punishmentId: string;
  playerUsername: string;
  playerUuid: string;
  type: 'BAN' | 'MUTE';
  originalReason: string;
  appealReason: string;
  createdAt: string;
  status: 'PENDING' | 'AI_REVIEWED' | 'ACCEPTED' | 'REJECTED';
  aiSentimentScore: number; // 0-100 (high = genuine remorse/likely innocent)
  aiRecommendedAction: 'ACCEPT' | 'REDUCE_DURATION' | 'DENY_HIGH_RISK';
  aiAnalysisSummary: string;
  assignedStaff: string | null;
}

export interface ConsoleLogMessage {
  id: string;
  timestamp: string;
  serverId: string;
  serverName: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'GRIM' | 'DEBUG' | 'CHAT' | 'COMMAND';
  thread?: string;
  message: string;
  rawAnsi?: string;
}

export interface AICopilotMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: string;
  content: string;
  codeSnippet?: string;
  actionPayload?: {
    type: 'EXECUTE_COMMAND' | 'AUTO_PATCH_CONFIG' | 'RESTART_SERVER' | 'TRIGGER_ROLLBACK' | 'GENERATE_POSTMORTEM';
    label: string;
    details: string;
  };
}

export interface CrashReport {
  id: string;
  serverId: string;
  serverName: string;
  timestamp: string;
  crashCause: string;
  exceptionType: string;
  stackTracePreview: string;
  affectedPluginOrCore: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  status: 'RESOLVED' | 'INVESTIGATING' | 'REPRODUCED';
  aiDiagnosis: string;
  aiSuggestedFix: string;
}

export interface PluginMeta {
  id: string;
  name: string;
  version: string;
  author: string;
  description: string;
  category: 'Security & Anticheat' | 'Performance' | 'Economy & Game' | 'Administration' | 'Chat & Social' | 'World Management';
  installed: boolean;
  enabled: boolean;
  downloads: number;
  rating: number;
  sizeKb: number;
  verified: boolean;
  resourceUsage: {
    avgCpuPercent: number;
    memoryMb: number;
    eventsPerSec: number;
  };
  sandboxRules: {
    allowNetworkSockets: boolean;
    allowFileSystemWrite: boolean;
    allowDirectMemoryAccess: boolean;
    maxThreadCount: number;
  };
  configEntries: Record<string, string | number | boolean>;
}

export interface SnapshotCheckpoint {
  id: string;
  serverId: string;
  serverName: string;
  timestamp: string;
  type: 'AUTO_HOURLY' | 'PRE_DEPLOY' | 'MANUAL' | 'INCIDENT_FREEZE';
  sizeMb: number;
  blockChangesCount: number;
  playerStatesCount: number;
  retentionDays: number;
  hash: string;
  tags: string[];
}

export interface AutomationCronTask {
  id: string;
  name: string;
  cronExpression: string; // e.g. "0 */6 * * *"
  description: string;
  actionType: 'RESTART_SERVER' | 'BACKUP_WORLDS' | 'PURGE_LOGS' | 'GRIM_SELF_TUNE' | 'DISCORD_SYNC' | 'GC_SWEEP';
  targetServerIds: string[];
  enabled: boolean;
  lastRunTime: string | null;
  nextRunTime: string;
  lastRunStatus: 'SUCCESS' | 'FAILED' | 'SKIPPED';
  durationMs: number;
}

export interface WebhookSubscription {
  id: string;
  name: string;
  url: string;
  secret: string;
  events: string[];
  enabled: boolean;
  deliveries24h: number;
  successRatePercent: number;
  lastStatusCode: number;
  lastDeliveredAt: string;
}

export interface ApiKeyRecord {
  id: string;
  name: string;
  prefix: string;
  createdAt: string;
  lastUsedAt: string | null;
  expiresAt: string | null;
  scopes: string[];
  status: 'ACTIVE' | 'REVOKED';
}

export interface FeatureFlagRecord {
  key: string;
  name: string;
  description: string;
  category: 'Core Runtime' | 'Anticheat & Moderation' | 'AI Intelligence' | 'Plugins & Hooks' | 'Experimental UI';
  enabled: boolean;
  rolloutPercentage: number;
  targetEnvironments: ('Production' | 'Staging' | 'Development')[];
  lastModifiedBy: string;
  updatedAt: string;
}

// ========================================================
// AI Providers, Task Routing & Automated Failover Types
// ========================================================

export type AIProviderId = 
  | 'google_gemini' 
  | 'anthropic_claude' 
  | 'openai' 
  | 'deepseek' 
  | 'groq' 
  | 'local_llm';

export interface AIProviderConfig {
  id: AIProviderId;
  name: string;
  badge: string;
  enabled: boolean;
  apiKey: string;
  baseUrl?: string;
  defaultModel: string;
  availableModels: string[];
  status: 'healthy' | 'rate_limited' | 'invalid_key' | 'disabled' | 'untested';
  rateLimitResetSeconds?: number;
  lastLatencyMs?: number;
  lastTestedAt?: string;
  quotaRemainingPercent?: number;
}

export type AITaskType = 
  | 'ai_triage' 
  | 'copilot' 
  | 'grim_combat' 
  | 'translation' 
  | 'appeals' 
  | 'tps_prediction';

export interface AITaskAssignment {
  taskType: AITaskType;
  title: string;
  description: string;
  primaryProvider: AIProviderId;
  primaryModel: string;
  fallbackProvider: AIProviderId;
  fallbackModel: string;
  autoFallbackOnRateLimit: boolean;
  timeoutMs: number;
}

export interface AIFailoverEvent {
  id: string;
  timestamp: string;
  taskType: AITaskType;
  primaryProvider: AIProviderId;
  primaryModel: string;
  fallbackProvider: AIProviderId;
  fallbackModel: string;
  triggerReason: string; // e.g. "HTTP 429 Too Many Requests (Rate Limit Exceeded)"
  latencyMs: number;
  status: 'SUCCESSFUL_FALLBACK' | 'FAILED_BOTH';
}

export interface AIEngineConfiguration {
  providers: Record<AIProviderId, AIProviderConfig>;
  taskAssignments: Record<AITaskType, AITaskAssignment>;
  simulateRateLimits: boolean;
  globalFallbackEnabled: boolean;
  strictSafetyGuard: boolean;
  maxTokensPerQuery: number;
}

// ========================================================
// Phase 15 — Player Profile, AI Review, Appeals Decision
// ========================================================

export interface PlayerDetail {
  uuid: string;
  username: string;
  first_seen: string;
  last_seen: string;
  playtime: number; // seconds
  current_server: string | null;
  risk_score: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  suspicion_score: number;
}

export interface VerificationLink {
  discord_id: string;
  discord_username: string;
  linked_at: string;
  status: string;
}

export interface Punishment {
  id: string;
  type: string;
  reason: string;
  staff_name: string;
  created_at: string;
  expires_at: string | null;
  status: string;
  appeal_id?: string;
}

export interface AnticheatFlag {
  check_name: string;
  vl: number;
  verbose: string;
  timestamp: string;
}

export interface AltAccount {
  uuid: string;
  username: string;
  confidence: number;
  cluster_type: string;
}

export interface Appeal {
  id: string;
  punishment_id: string;
  status: 'OPEN' | 'ACCEPTED' | 'REJECTED' | 'ESCALATED' | 'REVIEW_SCHEDULED' | 'PENDING' | 'AI_REVIEWED';
  created_at: string;
  action_taken: string | null;
  handled_by: string | null;
  ai_recommendation: string | null;
  ai_review_status: 'COMPLETED' | 'FAILED' | 'PENDING' | null;
  ai_result?: AIReviewResult | null;
  case_summary?: string | null;
  closed_at?: string | null;
  // Appeal details
  player_username?: string;
  player_uuid?: string;
  appeal_text?: string;
  punishment?: Punishment | null;
}

export interface PlayerFullProfile {
  player: PlayerDetail;
  verification: VerificationLink | null;
  punishment_history: Punishment[];
  anticheat_history: {
    total_flags: number;
    by_check: Record<string, { count: number; avg_vl: number; max_vl: number }>;
    timeline: AnticheatFlag[];
  };
  appeal_history: Appeal[];
  alt_accounts: AltAccount[];
}

export interface AIReviewResult {
  recommendation: 'ACCEPT' | 'REDUCE_SENTENCE' | 'REJECT' | 'ESCALATE' | 'SCHEDULE_REVIEW';
  confidence: number;
  reasoning: string;
  punishment_context: string;
  flag_summary: string | null;
  risk_factors: string[];
  mitigating_factors: string[];
}

export interface PlayerAIReview {
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  confidence: number;
  reasoning: string;
  recommendation: 'MONITOR' | 'WARN' | 'TEMP_BAN' | 'PERMANENT_BAN' | 'FALSE_POSITIVE';
  key_findings: string[];
  mitigating_factors: string[];
}
