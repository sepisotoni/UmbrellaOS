/**
 * UmbrellaOS Core API Client
 * FastAPI + Postgres Backend Integration
 * All API calls route through this single client.
 */

export interface ApiConfig {
  baseUrl: string;
  sessionToken: string | null;
  adminKey: string | null;
}

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// User & Auth Types
export interface UserSchema {
  id: string;
  discord_id: string;
  username: string;
  email: string | null;
  role_id: string | null;
  role: string | null;
  permissions: string[];
  avatar_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DiscordOAuthStartResponse {
  authorize_url: string;
  state: string;
}

export interface DiscordOAuthCallbackResponse {
  token: string;
  user: UserSchema;
  expires_in: number;
}

export interface MFAVerifyResponse {
  token: string;
  user: UserSchema;
  expires_in: number;
}

/** Shape of the 403 detail body when MFA is required after Discord OAuth */
export interface MFAChallengeDetail {
  mfa_required: true;
  mfa_token: string;
  message: string;
}

// Bot Guild Types
export interface GuildChannel {
  id: string;
  name: string;
  category: string | null;
}

export interface GuildRole {
  id: string;
  name: string;
  color: number;
}

// Knowledge Base Types
export interface KnowledgeEntry {
  id: string;
  channel_name: string;
  author_name: string;
  content: string;
  confidence_score: number;
  review_status: 'approved' | 'pending' | 'rejected';
  created_at: string;
  updated_at: string | null;
  corrects_entry_id: string | null;
  superseded_by_id: string | null;
}

export interface KnowledgeVersion {
  version_number: number;
  content: string;
  edited_by: string | null;
  created_at: string;
}

// Server & Mesh Types
export interface ServerRecord {
  id: string;
  name: string;
  status: 'online' | 'warning' | 'offline' | 'maintenance';
  tps: number;
  players: number;
  maxPlayers: number;
  ramUsedMb?: number;
  ramTotalMb?: number;
  cpu?: number;
  version: string;
  pluginsConnected: number;
  pluginsTotal: number;
  grim_status?: string;
  last_heartbeat?: string;
}

export interface PluginHeartbeatRecord {
  id: string;
  name: string;
  version: string;
  server: string;
  status: 'connected' | 'stale' | 'unreachable';
  heartbeatMs: number;
  lastSeen: string;
}

export interface PluginHeartbeatStatus {
  server_id: string;
  server_name?: string;
  umbrella_status: string;
  umbrella_version?: string;
  grimac_status?: string;
  last_heartbeat?: string;
}

export interface NetworkSettings {
  discord_guild_id?: string;
  verification_channel_id?: string;
  ai_model?: string;
  discord_invite?: string;
}

export interface FlaggedAltAccount {
  id: string;
  primary_uuid: string;
  primary_username?: string;
  alt_uuid: string;
  alt_username?: string;
  method: string;
  confidence: number;
  created_at: string;
}

export interface AltClusterGroup {
  group_id: string;
  reason: string;
  members: Array<{
    uuid: string;
    username: string;
    is_banned: boolean;
  }>;
}

// Player Types
export interface PlayerSummary {
  uuid: string;
  username: string;
  first_seen: string;
  last_seen: string;
  playtime: number;
  joins: number;
  deaths: number;
  risk_score: number;
  suspicion_score: number;
  discord_id: string | null;
}

export interface FullProfileResponse {
  player: {
    uuid: string;
    username: string;
    first_seen: string;
    last_seen: string;
    playtime: number;
    joins?: number;
    deaths?: number;
    current_server?: string | null;
    risk_score: number;
    suspicion_score?: number;
    discord_id?: string | null;
    discord_username?: string | null;
    ip_address?: string | null;
  };
  metrics: {
    total_playtime_hours: number;
    session_count: number;
    average_session_mins: number;
    total_punishments: number;
    active_punishments: number;
    anticheat_flags: number;
  };
  anticheat_history: {
    total_flags: number;
    flags_last_24h: number;
    by_check: Record<string, { count: number; max_vl: number }>;
    recent_violations: Array<{
      id: string;
      check_name: string;
      verbose: string;
      vl: number;
      created_at: string;
      server_id?: string | null;
    }>;
  };
  punishment_history: Array<{
    id: string;
    type: string;
    reason: string;
    created_at: string;
    expires_at?: string | null;
    active: boolean;
    staff_name?: string | null;
  }>;
  appeal_history: Array<{
    id: string;
    punishment_id: string;
    status: string;
    created_at: string;
    action_taken?: string | null;
    handled_by?: string | null;
    ai_recommendation?: string | null;
    case_summary?: string | null;
  }>;
  alt_accounts: Array<{
    uuid: string;
    username: string | null;
    confidence: string | null;
    cluster_type: string | null;
  }>;
}

// Punishments
export interface PunishmentSchema {
  id: string;
  player_uuid: string | null;  // null for IP-level bans (type='ipban')
  player_name?: string | null;
  staff_id: string | null;
  type: string;
  reason: string;
  created_at: string;
  expires_at: string | null;
  active: boolean;
  status?: string | null;
  ban_ip_address?: string | null;  // set for type='ipban'
}

export interface CreatePunishmentPayload {
  player_uuid: string;
  player_username?: string;
  type: string; // 'ban' | 'mute' | 'warn' | 'kick' | 'ipban'
  reason: string;
  expires_at?: string | null;
  staff_id?: string | null;
  server_scope?: string;
  evidence_url?: string;
}

// Anticheat
export interface AnticheatViolationRecord {
  id: string;
  player_uuid: string;
  player_name: string;
  server_id: string | null;
  check_name: string;
  verbose: string;
  vl: number;
  created_at: string;
}

// Appeals
export interface AppealSchema {
  id: string;
  punishment_id: string;
  player_uuid: string;
  status: string;
  message: string;
  created_at: string;
  action_taken?: string | null;
  handled_by?: string | null;
  case_summary?: string | null;
  closed_at?: string | null;
  ai_review_status?: string | null;
}

export interface AppealClosePayload {
  action: 'ACCEPT' | 'REDUCE_SENTENCE' | 'REJECT' | 'ESCALATE' | 'SCHEDULE_REVIEW';
  staff_note?: string;
  new_expiry?: string;
}

export interface AIReviewAppealResponse {
  recommendation: 'ACCEPT' | 'REDUCE_SENTENCE' | 'REJECT' | 'ESCALATE' | 'SCHEDULE_REVIEW';
  confidence: number;
  reasoning: string;
  flag_summary?: string;
  punishment_context?: string;
  risk_factors?: string[];
  mitigating_factors?: string[];
}

// Staff
export interface StaffMemberSchema {
  id: string;
  discord_id: string;
  username: string;
  discriminator?: string;
  avatar_url: string | null;
  role: string | null;
  permissions: string[];
  email: string | null;
  linked_minecraft_uuid?: string | null;
  linked_minecraft_username?: string | null;
  is_active?: boolean;
}

export type StaffRecord = StaffMemberSchema;
export type StaffMember = StaffMemberSchema;

export interface DiscordMemberSchema {
  discord_id: string;
  username: string;
  is_staff: boolean;
}

export type DiscordGuildMember = DiscordMemberSchema;

export interface RoleSchema {
  id: string;
  name: string;
  description: string;
  permissions: string[];
}

// Verification
export interface VerificationLinkSchema {
  id: number;
  discord_id: string;
  discord_username: string | null;
  minecraft_uuid: string | null;
  minecraft_username: string | null;
  linked_at: string | null;
  verified_by: string;
  status: string;
}

export type VerificationLink = VerificationLinkSchema;

export interface PendingVerification {
  code: string;
  player_uuid: string;
  username?: string;
  created_at: string;
  expires_at?: string;
}

// Alts
export interface SuspicionEventSchema {
  id: number;
  player_uuid: string;
  trigger: string;
  points: number;
  metadata_json: string | null;
  created_at: string;
  reviewed: boolean;
  reviewed_by: string | null;
  false_positive: boolean;
}

export interface AltGroupSchema {
  id: number;
  created_at: string;
  notes: string | null;
  confirmed: boolean;
  members?: Array<{ id: number; group_id: number; player_uuid: string; added_at: string }>;
}

// AI Tasks & Intelligence
export interface AITaskSchema {
  id: number;  // backend AITask.id is Integer autoincrement, not a UUID string
  task_type: string;
  status: string;
  player_uuid: string | null;
  created_at: string;
  expires_at: string;
  ai_summary: string | null;
  ai_recommendation: string | null;
  ai_confidence: number | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  action_taken: string | null;
  evidence?: any;
  ai_result?: any;
}

export type AITask = AITaskSchema;

export interface CopilotResponse {
  response: string;
  model_used: string;
  latency_ms: number;
}

export interface CrashRiskResponse {
  server_id: string;
  risk_level: string;
  tps_trend: number | null;
  mspt_avg: number | null;
  recommendation: string;
  assessed_at: string;
}

// Audit Log
export interface AuditLogItem {
  id: number;
  actor: string;
  actor_type: string;
  action: string;
  target: string | null;
  details_json: string | null;
  created_at: string;
}

export type AuditLogEntry = AuditLogItem;

export interface AuditLogResponse {
  items?: AuditLogItem[];
  logs?: AuditLogItem[];
  total: number;
  limit: number;
  offset: number;
}

// Feature Flags
export interface FeatureFlagResponse {
  id: string;
  name: string;
  enabled: boolean;
  description: string;
  percentage?: number;
}

export type FeatureFlag = FeatureFlagResponse;

// Settings
export interface SettingRecord {
  key: string;
  value: string;
  category?: string;
  description?: string;
  sensitive?: boolean;
}

// Default Base URL
const DEFAULT_CORE_URL = (import.meta as any).env?.VITE_UMBRELLA_CORE_URL || 'https://umbrellaos-core.onrender.com';

export class UmbrellaApiClient {
  private baseUrl: string = DEFAULT_CORE_URL;
  private sessionToken: string | null = null;
  private adminKey: string | null = null;

  constructor() {
    if (typeof window !== 'undefined' && window.localStorage) {
      const storedUrl = localStorage.getItem('umbrella_core_url_override');
      if (storedUrl) {
        this.baseUrl = storedUrl.replace(/\/+$/, '');
      }
      const storedKey = localStorage.getItem('umbrella_admin_key_override') || localStorage.getItem('umbrella_admin_key');
      if (storedKey) {
        this.adminKey = storedKey;
      }
    }
  }

  public setBaseUrl(url: string) {
    this.baseUrl = url.replace(/\/+$/, '');
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.setItem('umbrella_core_url_override', this.baseUrl);
    }
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  public setSessionToken(token: string | null) {
    this.sessionToken = token;
  }

  public getSessionToken(): string | null {
    return this.sessionToken;
  }

  public setAdminKey(key: string | null) {
    this.adminKey = key;
  }

  public getAdminKey(): string | null {
    return this.adminKey;
  }

  public getServerConsoleWebSocketUrl(serverId: string): string {
    const wsProtocol = this.baseUrl.startsWith('https') ? 'wss:' : 'ws:';
    const host = this.baseUrl.replace(/^https?:\/\//, '');
    const tokenParam = this.sessionToken ? `&token=${encodeURIComponent(this.sessionToken)}` : '';
    const adminParam = this.adminKey ? `&admin_key=${encodeURIComponent(this.adminKey)}` : '';
    return `${wsProtocol}//${host}/ws/console/${encodeURIComponent(serverId)}?source=dashboard${tokenParam}${adminParam}`;
  }

  public async sendServerCommand(serverId: string, command: string): Promise<any> {
    // Core queues commands via POST /api/v1/mc/command — plugin polls and executes
    return this.request<any>('/api/v1/mc/command', {
      method: 'POST',
      body: JSON.stringify({
        command,
        requested_by_discord_id: 'dashboard',
        requested_by_username: 'Dashboard',
      }),
    });
  }

  public async getPluginConsoleLogs(
    serverId: string,
    n = 100,
  ): Promise<{ server_id: string; lines: { ts: string; line: string }[] }> {
    return this.request(
      `/api/v1/plugin/servers/${encodeURIComponent(serverId)}/console/recent?n=${n}`,
    );
  }

  // Knowledge Base
  public async getKnowledgeEntries(params?: {
    query?: string;
    limit?: number;
    status?: string;
  }): Promise<{ entries: KnowledgeEntry[]; total: number }> {
    const qs = new URLSearchParams();
    if (params?.query) qs.set('query', params.query);
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.status) qs.set('status', params.status);
    const q = qs.toString();
    return this.request(`/api/v1/knowledge${q ? `?${q}` : ''}`);
  }

  public async createKnowledgeEntry(data: {
    title: string;
    content: string;
    category?: string;
  }): Promise<KnowledgeEntry> {
    return this.request('/api/v1/knowledge', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  public async updateKnowledgeEntry(id: string, content: string): Promise<KnowledgeEntry> {
    return this.request(`/api/v1/knowledge/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify({ content }),
    });
  }

  public async deleteKnowledgeEntry(id: string): Promise<void> {
    return this.request(`/api/v1/knowledge/${encodeURIComponent(id)}`, { method: 'DELETE' });
  }

  public async getKnowledgeEntryDetail(
    id: string,
  ): Promise<{ entry: KnowledgeEntry; versions: KnowledgeVersion[] }> {
    return this.request(`/api/v1/knowledge/${encodeURIComponent(id)}`);
  }

  public async getPendingKnowledge(): Promise<{ entries: KnowledgeEntry[] }> {
    return this.request('/api/v1/knowledge/pending');
  }

  public async approveKnowledge(id: string): Promise<KnowledgeEntry> {
    return this.request(`/api/v1/knowledge/${encodeURIComponent(id)}/approve`, { method: 'POST' });
  }

  public async rejectKnowledge(id: string): Promise<KnowledgeEntry> {
    return this.request(`/api/v1/knowledge/${encodeURIComponent(id)}/reject`, { method: 'POST' });
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});

    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }

    if (this.sessionToken) {
      headers.set('Authorization', `Bearer ${this.sessionToken}`);
    }

    if (this.adminKey) {
      headers.set('X-Admin-Key', this.adminKey);
    }

    const url = `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'omit',
      });

      if (!response.ok) {
        let errData: any;
        try {
          errData = await response.json();
        } catch {
          errData = { detail: response.statusText };
        }
        throw new ApiError(
          errData?.detail || errData?.message || `Request failed with status ${response.status}`,
          response.status,
          errData
        );
      }

      if (response.status === 204) {
        return {} as T;
      }

      return (await response.json()) as T;
    } catch (err: any) {
      if (err instanceof ApiError) throw err;
      // TypeError = browser blocked the request (CORS / server offline)
      const isNetworkErr = err instanceof TypeError;
      throw new ApiError(
        isNetworkErr
          ? `Cannot reach Core at ${this.baseUrl} — server may be offline or CORS is blocking this origin`
          : (err?.message || 'Network connection failed'),
        0,
        err
      );
    }
  }

  // --------------------------------------------------------------------------
  // Health & System
  // --------------------------------------------------------------------------
  public async getHealth(): Promise<{ status: string; uptime?: number; version?: string; database?: string }> {
    return this.request<{ status: string; uptime?: number; version?: string; database?: string }>('/health');
  }

  // --------------------------------------------------------------------------
  // Auth
  // --------------------------------------------------------------------------
  public async getDiscordAuthUrl(redirectUri?: string): Promise<DiscordOAuthStartResponse> {
    return this.request<DiscordOAuthStartResponse>('/api/v1/auth/discord/authorize', {
      method: 'POST',
      body: JSON.stringify({ redirect_uri: redirectUri ?? `${window.location.origin}/` }),
    });
  }

  public async discordAuthorize(redirectUri?: string): Promise<DiscordOAuthStartResponse> {
    return this.getDiscordAuthUrl(redirectUri);
  }

  public async exchangeDiscordCode(code: string, state: string, redirectUri?: string): Promise<DiscordOAuthCallbackResponse> {
    return this.request<DiscordOAuthCallbackResponse>('/api/v1/auth/discord/callback', {
      method: 'POST',
      body: JSON.stringify({ code, state, redirect_uri: redirectUri }),
    });
  }

  public async discordCallback(code: string, state: string, redirectUri?: string): Promise<DiscordOAuthCallbackResponse> {
    return this.exchangeDiscordCode(code, state, redirectUri);
  }

  /** Exchange a short-lived MFA pre-session token + TOTP code for a full session. */
  public async mfaVerify(mfaToken: string, code: string): Promise<MFAVerifyResponse> {
    return this.request<MFAVerifyResponse>('/api/v1/auth/mfa/verify', {
      method: 'POST',
      body: JSON.stringify({ mfa_token: mfaToken, code }),
    });
  }

  public async logout(): Promise<void> {
    // Hit core to revoke the session server-side before clearing local state
    if (this.sessionToken) {
      try {
        await this.request<unknown>('/api/v1/auth/logout', {
          method: 'POST',
          // Session token is sent as Authorization: Bearer <token> by request()
        });
      } catch {
        // Best-effort — clear local state regardless
      }
    }
    this.sessionToken = null;
    this.adminKey = null;
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.removeItem('umbrella_session_token');
      localStorage.removeItem('umbrella_admin_key');
      localStorage.removeItem('umbrella_admin_user');
      localStorage.removeItem('umb_auth_user');
    }
  }

  public async getMe(): Promise<UserSchema> {
    return this.request<UserSchema>('/api/v1/auth/me');
  }

  public async getRoles(): Promise<RoleSchema[]> {
    return this.request<RoleSchema[]>('/api/v1/roles');
  }

  // --------------------------------------------------------------------------
  // Servers & Fleet
  // --------------------------------------------------------------------------
  public async getServers(): Promise<ServerRecord[]> {
    return this.request<ServerRecord[]>('/api/v1/dashboard/servers');
  }

  public async getServer(id: string): Promise<ServerRecord> {
    return this.request<ServerRecord>(`/api/v1/dashboard/servers/${encodeURIComponent(id)}`);
  }

  public async restartServer(id: string): Promise<{ success: boolean; message: string }> {
    // Core endpoint is POST /api/v1/server/control with body {server_id, action}
    return this.request<{ success: boolean; message: string }>('/api/v1/server/control', {
      method: 'POST',
      body: JSON.stringify({ server_id: id, action: 'restart' }),
    });
  }

  public async getPlugins(serverId?: string): Promise<PluginHeartbeatRecord[]> {
    // Core prefix is /api/v1/plugin (not /api/v1/plugins); use dashboard endpoint
    const query = serverId ? `?server=${encodeURIComponent(serverId)}` : '';
    return this.request<PluginHeartbeatRecord[]>(`/api/v1/plugin/health${query}`);
  }

  public async getPluginsHeartbeat(): Promise<PluginHeartbeatStatus[]> {
    try {
      const data = await this.request<any[]>('/api/v1/dashboard/plugins');
      return (data || []).map((p: any) => ({
        server_id: p.server_id || p.server || 'unknown',
        server_name: p.server_name || p.server || 'Unknown Node',
        umbrella_status: p.umbrella_status || p.status || 'ACTIVE',
        umbrella_version: p.umbrella_version || p.version || '1.0.0',
        grimac_status: p.grimac_status || 'ACTIVE',
        last_heartbeat: p.last_heartbeat || p.lastSeen,
      }));
    } catch {
      return [];
    }
  }

  // --------------------------------------------------------------------------
  // Players & Profiles
  // --------------------------------------------------------------------------
  public async getPlayers(params?: { search?: string; username?: string; limit?: number; offset?: number }): Promise<PlayerSummary[]> {
    const q = new URLSearchParams();
    const searchTerm = params?.search || params?.username;
    if (searchTerm) q.set('username', searchTerm);
    if (params?.limit) q.set('limit', params.limit.toString());
    if (params?.offset) q.set('offset', params.offset.toString());
    const queryStr = q.toString() ? `?${q.toString()}` : '';
    return this.request<PlayerSummary[]>(`/api/v1/players${queryStr}`);
  }

  public async getPlayerFullProfile(uuid: string): Promise<FullProfileResponse> {
    return this.request<FullProfileResponse>(`/api/v1/players/${encodeURIComponent(uuid)}/full-profile`);
  }

  // --------------------------------------------------------------------------
  // Moderation & Punishments
  // --------------------------------------------------------------------------
  public async getPunishments(params?: { player_uuid?: string; active_only?: boolean; skip?: number; limit?: number }): Promise<PunishmentSchema[]> {
    const q = new URLSearchParams();
    if (params?.player_uuid) q.set('player_uuid', params.player_uuid);
    if (params?.active_only !== undefined) q.set('active_only', params.active_only.toString());
    if (params?.skip !== undefined) q.set('skip', params.skip.toString());
    if (params?.limit !== undefined) q.set('limit', params.limit.toString());
    const queryStr = q.toString() ? `?${q.toString()}` : '';
    return this.request<PunishmentSchema[]>(`/api/v1/punishments${queryStr}`);
  }

  public async createPunishment(payload: CreatePunishmentPayload): Promise<PunishmentSchema> {
    return this.request<PunishmentSchema>('/api/v1/punishments', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async revokePunishment(punishmentId: string): Promise<PunishmentSchema> {
    return this.request<PunishmentSchema>(`/api/v1/punishments/${encodeURIComponent(punishmentId)}/revoke`, {
      method: 'POST',
    });
  }

  public async kickPlayer(playerUuid: string, reason: string = 'Kicked by staff', staffId?: string): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>('/api/v1/moderation/kick', {
      method: 'POST',
      body: JSON.stringify({ player_uuid: playerUuid, reason, staff_id: staffId }),
    });
  }

  public async warnPlayer(playerUuid: string, reason: string, staffId?: string): Promise<any> {
    return this.request<any>('/api/v1/moderation/warn', {
      method: 'POST',
      body: JSON.stringify({ player_uuid: playerUuid, reason, staff_id: staffId }),
    });
  }

  // --------------------------------------------------------------------------
  // Anticheat & GrimAC Violations
  // --------------------------------------------------------------------------
  public async getAnticheatViolations(params?: {
    player_uuid?: string;
    server_id?: string;
    check_name?: string;
    limit?: number;
  }): Promise<AnticheatViolationRecord[]> {
    const q = new URLSearchParams();
    if (params?.player_uuid) q.set('player_uuid', params.player_uuid);
    if (params?.server_id) q.set('server_id', params.server_id);
    if (params?.check_name) q.set('check_name', params.check_name);
    if (params?.limit) q.set('limit', params.limit.toString());
    const queryStr = q.toString() ? `?${q.toString()}` : '';
    return this.request<AnticheatViolationRecord[]>(`/api/v1/anticheat/violations${queryStr}`);
  }

  // --------------------------------------------------------------------------
  // Appeals & Appeals Decision Flow
  // --------------------------------------------------------------------------
  public async getAppeals(params?: { status?: string; player_uuid?: string; skip?: number; limit?: number }): Promise<AppealSchema[]> {
    const q = new URLSearchParams();
    if (params?.status) q.set('status', params.status);
    if (params?.player_uuid) q.set('player_uuid', params.player_uuid);
    if (params?.skip !== undefined) q.set('skip', params.skip.toString());
    if (params?.limit !== undefined) q.set('limit', params.limit.toString());
    const queryStr = q.toString() ? `?${q.toString()}` : '';
    return this.request<AppealSchema[]>(`/api/v1/appeals${queryStr}`);
  }

  public async closeAppeal(appealId: string, payload: AppealClosePayload): Promise<AppealSchema> {
    return this.request<AppealSchema>(`/api/v1/appeals/${encodeURIComponent(appealId)}/close`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async triggerAppealAIReview(appealId: string): Promise<any> {
    return this.request<any>(`/api/v1/ai/review/appeal/${encodeURIComponent(appealId)}`, {
      method: 'POST',
    });
  }

  public async triggerPlayerAIReview(playerUuid: string): Promise<any> {
    return this.request<any>(`/api/v1/ai/review/player/${encodeURIComponent(playerUuid)}`, {
      method: 'POST',
    });
  }

  public async reviewAppealAI(appealId: string): Promise<any> {
    return this.triggerAppealAIReview(appealId);
  }

  public async reviewPlayerFullAI(uuid: string): Promise<any> {
    return this.triggerPlayerAIReview(uuid);
  }

  // --------------------------------------------------------------------------
  // Staff Directory & Management
  // --------------------------------------------------------------------------
  public async getStaff(): Promise<StaffMemberSchema[]> {
    return this.request<StaffMemberSchema[]>('/api/v1/staff');
  }

  public async getStaffMembers(): Promise<StaffMemberSchema[]> {
    return this.getStaff();
  }

  public async manageStaff(param1: any, param2?: any): Promise<any> {
    if (typeof param1 === 'object') {
      return this.request<any>('/api/v1/staff/manage', {
        method: 'POST',
        body: JSON.stringify(param1),
      });
    }
    return this.request<any>('/api/v1/staff/manage', {
      method: 'POST',
      body: JSON.stringify({ user_id: param1, action: param2 || 'update' }),
    });
  }

  public async addStaff(discordId: string, role: string, username?: string): Promise<any> {
    return this.request<any>('/api/v1/staff/add', {
      method: 'POST',
      body: JSON.stringify({ discord_id: discordId, role, username }),
    });
  }

  public async addStaffMember(payloadOrDiscordId: any, role?: string, username?: string): Promise<any> {
    if (typeof payloadOrDiscordId === 'object') {
      return this.addStaff(payloadOrDiscordId.discord_id, payloadOrDiscordId.role, payloadOrDiscordId.username);
    }
    return this.addStaff(payloadOrDiscordId, role || 'helper', username);
  }

  public async updateStaff(discordId: string, role: string): Promise<any> {
    return this.manageStaff({ discord_id: discordId, role });
  }

  public async updateStaffRole(discordId: string, role: string): Promise<any> {
    return this.updateStaff(discordId, role);
  }

  public async removeStaff(discordId: string): Promise<any> {
    return this.manageStaff({ discord_id: discordId, is_active: false });
  }

  public async removeStaffMember(discordId: string): Promise<any> {
    return this.removeStaff(discordId);
  }

  public async getDiscordMembers(): Promise<DiscordMemberSchema[]> {
    return this.request<DiscordMemberSchema[]>('/api/v1/staff/discord-members');
  }

  public async getDiscordGuildMembers(): Promise<DiscordMemberSchema[]> {
    return this.getDiscordMembers();
  }

  // --------------------------------------------------------------------------
  // Verification
  // --------------------------------------------------------------------------
  public async getVerificationLinks(limit: number = 50, offset: number = 0): Promise<VerificationLinkSchema[]> {
    return this.request<VerificationLinkSchema[]>(`/api/v1/verification/links?limit=${limit}&offset=${offset}`);
  }

  public async unlinkAccount(discordId: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/api/v1/verification/unlink/${encodeURIComponent(discordId)}`, {
      method: 'DELETE',
    });
  }

  public async unlinkVerification(discordId: string): Promise<{ success: boolean }> {
    return this.unlinkAccount(discordId);
  }

  public async getVerificationCount(): Promise<{ count: number }> {
    return this.request<{ count: number }>('/api/v1/verification/count');
  }

  public async getPendingVerifications(): Promise<PendingVerification[]> {
    // Core returns player_username; normalize to username for dashboard consistency
    const raw = await this.request<any[]>('/api/v1/verification/pending');
    return (raw || []).map((v: any) => ({
      code: v.code,
      player_uuid: v.player_uuid,
      username: v.player_username || v.username,
      created_at: v.created_at,
      expires_at: v.expires_at,
    }));
  }

  public async manualLinkAccount(discordId: string, mcUsername: string): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>('/api/v1/verification/manual-link', {
      method: 'POST',
      body: JSON.stringify({ discord_id: discordId, mc_username: mcUsername }),
    });
  }

  public async manualLinkVerification(payloadOrDiscordId: any, maybeMcUsername?: string): Promise<{ success: boolean; message: string }> {
    if (typeof payloadOrDiscordId === 'object') {
      return this.request<{ success: boolean; message: string }>('/api/v1/verification/manual-link', {
        method: 'POST',
        body: JSON.stringify(payloadOrDiscordId),
      });
    }
    return this.manualLinkAccount(payloadOrDiscordId, maybeMcUsername || '');
  }

  // --------------------------------------------------------------------------
  // Alt Detection
  // --------------------------------------------------------------------------
  public async getFlaggedAlts(limit: number = 50, offset: number = 0): Promise<SuspicionEventSchema[]> {
    return this.request<SuspicionEventSchema[]>(`/api/v1/alts/flagged?limit=${limit}&offset=${offset}`);
  }

  public async getAltGroups(limit: number = 50, offset: number = 0): Promise<AltGroupSchema[]> {
    return this.request<AltGroupSchema[]>(`/api/v1/alts/groups?limit=${limit}&offset=${offset}`);
  }

  public async markAltFalsePositive(
    primaryUuidOrEventId?: string | number,
    altUuid?: string,
    reviewedBy: string = 'staff'
  ): Promise<{ success: boolean }> {
    const eventId = typeof primaryUuidOrEventId === 'number' ? primaryUuidOrEventId : undefined;
    const playerUuid = typeof primaryUuidOrEventId === 'string' ? primaryUuidOrEventId : undefined;
    return this.request<{ success: boolean }>('/api/v1/alts/false-positive', {
      method: 'POST',
      body: JSON.stringify({ event_id: eventId, player_uuid: playerUuid, alt_uuid: altUuid, reviewed_by: reviewedBy }),
    });
  }

  // --------------------------------------------------------------------------
  // AI Tasks & Intelligence
  // --------------------------------------------------------------------------
  public async getAITasks(limit: number = 50, offset: number = 0): Promise<AITaskSchema[]> {
    return this.request<AITaskSchema[]>(`/api/v1/ai/tasks?limit=${limit}&offset=${offset}`);
  }

  public async approveAITask(taskId: number, actionTaken: string = 'approve', reviewedBy: string = 'staff'): Promise<any> {
    return this.request<any>(`/api/v1/ai/tasks/${taskId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ action_taken: actionTaken, reviewed_by: reviewedBy }),
    });
  }

  public async denyAITask(taskId: number, reviewedBy: string = 'staff', reason: string = 'denied'): Promise<any> {
    return this.request<any>(`/api/v1/ai/tasks/${taskId}/deny`, {
      method: 'POST',
      body: JSON.stringify({ reviewed_by: reviewedBy, reason }),
    });
  }

  public async sendCopilotPrompt(message: string, context?: string): Promise<CopilotResponse> {
    return this.request<CopilotResponse>('/api/v1/ai/copilot', {
      method: 'POST',
      body: JSON.stringify({ message, context }),
    });
  }

  public async askCopilot(prompt: string, context?: any): Promise<any> {
    return this.sendCopilotPrompt(prompt, typeof context === 'string' ? context : JSON.stringify(context || {}));
  }

  public async getCrashRisk(serverId: string): Promise<CrashRiskResponse> {
    return this.request<CrashRiskResponse>(`/api/v1/ai/crash-risk/${encodeURIComponent(serverId)}`);
  }

  public async testAIProvider(provider: string, apiKey?: string): Promise<{ success: boolean; latency_ms: number; message: string; model?: string }> {
    return this.request<any>('/api/v1/ai/providers/test', {
      method: 'POST',
      body: JSON.stringify({ provider, api_key: apiKey }),
    });
  }

  // --------------------------------------------------------------------------
  // Audit Log
  // --------------------------------------------------------------------------
  public async getAuditLogs(params?: { limit?: number; offset?: number; actor_type?: string; action?: string }): Promise<AuditLogEntry[]> {
    const q = new URLSearchParams();
    if (params?.limit !== undefined) q.set('limit', params.limit.toString());
    if (params?.offset !== undefined) q.set('offset', params.offset.toString());
    if (params?.actor_type) q.set('actor_type', params.actor_type);
    if (params?.action) q.set('action', params.action);
    const queryStr = q.toString() ? `?${q.toString()}` : '';
    const res = await this.request<any>(`/api/v1/audit${queryStr}`);
    if (Array.isArray(res)) return res;
    if (res && Array.isArray(res.items)) return res.items;
    if (res && Array.isArray(res.logs)) return res.logs;
    return [];
  }

  // --------------------------------------------------------------------------
  // Feature Flags
  // --------------------------------------------------------------------------
  public async getFeatureFlags(): Promise<FeatureFlagResponse[]> {
    return this.request<FeatureFlagResponse[]>('/api/v1/feature-flags');
  }

  public async upsertFeatureFlag(name: string, enabled: boolean, description: string = ''): Promise<FeatureFlagResponse> {
    return this.request<FeatureFlagResponse>('/api/v1/feature-flags', {
      method: 'POST',
      body: JSON.stringify({ name, enabled, description }),
    });
  }

  public async setFeatureFlag(flag: { name: string; enabled: boolean; description?: string; percentage?: number }): Promise<any> {
    return this.upsertFeatureFlag(flag.name, flag.enabled, flag.description || '');
  }

  public async deleteFeatureFlag(name: string): Promise<{ deleted: boolean }> {
    return this.request<{ deleted: boolean }>(`/api/v1/feature-flags/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    });
  }

  // --------------------------------------------------------------------------
  // Settings (Only Real Backend Keys)
  // --------------------------------------------------------------------------
  public async getSettings(): Promise<SettingRecord[]> {
    return this.request<SettingRecord[]>('/api/v1/settings');
  }

  public async getSetting(key: string): Promise<SettingRecord> {
    return this.request<SettingRecord>(`/api/v1/settings/${encodeURIComponent(key)}`);
  }

  public async updateSetting(key: string, value: string): Promise<SettingRecord> {
    return this.request<SettingRecord>(`/api/v1/settings/${encodeURIComponent(key)}`, {
      method: 'PATCH',
      body: JSON.stringify({ value }),
    });
  }

  public async updateSettings(settings: Partial<NetworkSettings>): Promise<any> {
    const promises: Promise<any>[] = [];
    if (settings.discord_guild_id !== undefined) {
      promises.push(this.updateSetting('discord_guild_id', settings.discord_guild_id));
    }
    if (settings.verification_channel_id !== undefined) {
      promises.push(this.updateSetting('verification_channel_id', settings.verification_channel_id));
    }
    if (settings.ai_model !== undefined) {
      promises.push(this.updateSetting('ai_model', settings.ai_model));
    }
    return Promise.all(promises);
  }

  // --------------------------------------------------------------------------
  // Bot Registration & Command Manifest
  // --------------------------------------------------------------------------
  public async getBotRegistration(): Promise<{ registered: boolean; callback_url: string | null; registered_at: string | null }> {
    return this.request('/api/v1/bot/register');
  }

  public async getBotCommands(): Promise<{ commands: { name: string; description: string; args: string; owner_only: boolean }[]; pushed_at: string | null }> {
    return this.request('/api/v1/bot/commands');
  }

  public async getGuildChannels(): Promise<{ channels: GuildChannel[]; pushed_at: string | null }> {
    return this.request('/api/v1/bot/channels');
  }

  public async getGuildRoles(): Promise<{ roles: GuildRole[]; pushed_at: string | null }> {
    return this.request('/api/v1/bot/roles');
  }

  // --------------------------------------------------------------------------
  // Global Broadcast & Shortcuts
  // --------------------------------------------------------------------------
  public async broadcast(message: string, serverId?: string): Promise<any> {
    return this.broadcastMessage(message, 'Admin');
  }

  public async broadcastMessage(message: string, playerName: string = 'Staff', channelId?: string): Promise<any> {
    return this.request<any>('/api/v1/bridge/message', {
      method: 'POST',
      body: JSON.stringify({
        source: 'DASHBOARD',
        player_name: playerName,
        message,
        ...(channelId ? { channel_id: channelId } : {}),
      }),
    });
  }
}

export const api = new UmbrellaApiClient();
export default api;

// Bot-related interfaces (exported for DiscordView)
export interface BotRegistrationStatus {
  registered: boolean;
  callback_url: string | null;
  registered_at: string | null;
}

export interface BotCommand {
  name: string;
  description: string;
  args: string;
  owner_only: boolean;
}
