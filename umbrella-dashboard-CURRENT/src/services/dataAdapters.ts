/**
 * Data Adapters & Transformer Layer
 * Normalizes raw FastAPI backend responses into strongly typed dashboard models.
 */

import {
  MinecraftServer,
  PlayerRecord,
  PunishmentRecord,
  AppealTicket,
  GrimACViolation,
  AltAccountCluster,
  CrashReport,
  PluginMeta,
  SnapshotCheckpoint,
  AutomationCronTask,
  ApiKeyRecord,
  WebhookSubscription,
  FeatureFlagRecord,
  NodeInfrastructure
} from '../types/dashboard';

import {
  BackendServer,
  BackendPunishment,
  BackendAppeal,
  BackendAltFlag,
  BackendLogEntry,
  BackendPluginHeartbeat
} from '../lib/api';

export const adaptBackendServer = (bs: BackendServer): MinecraftServer => {
  let sType: MinecraftServer['type'] = 'purpur_survival';
  const nameLower = (bs.name || '').toLowerCase();
  const idLower = (bs.id || '').toLowerCase();

  if (idLower.includes('proxy') || nameLower.includes('velocity')) {
    sType = 'velocity_proxy';
  } else if (idLower.includes('lobby') || nameLower.includes('hub') || nameLower.includes('lobby')) {
    sType = 'paper_lobby';
  } else if (idLower.includes('anarchy') || nameLower.includes('anarchy')) {
    sType = 'fabric_anarchy';
  }

  return {
    id: bs.id,
    name: bs.name || bs.id,
    type: sType,
    version: bs.version || 'Paper 1.20.4',
    status: bs.status || 'online',
    host: bs.id.includes('proxy') ? 'play.umbrella-mc.net' : '10.0.0.1',
    port: 25565,
    playersCount: bs.players || 0,
    maxPlayers: bs.maxPlayers || 100,
    tps: bs.tps !== undefined ? bs.tps : 20.0,
    cpuPercent: bs.cpu || 0,
    memoryMb: bs.ramUsedMb || 0,
    maxMemoryMb: bs.ramTotalMb || 8192,
    uptimeSeconds: 0,
    node: bs.node || 'node-01',
    location: bs.location || 'Frankfurt, DE',
    activePluginsCount: bs.pluginsConnected || 0,
    grimAcEnabled: true,
    rawBackendData: {
      ramUsedMb: bs.ramUsedMb || 0,
      ramTotalMb: bs.ramTotalMb || 8192,
      cpu: bs.cpu || 0,
      pluginsConnected: bs.pluginsConnected || 0,
      pluginsTotal: bs.pluginsTotal || 0
    }
  };
};

export const adaptBackendPunishment = (bp: BackendPunishment): PunishmentRecord => {
  return {
    id: bp.id,
    playerUuid: bp.playerUuid,
    playerName: bp.playerName || 'Unknown Player',
    staffName: bp.staffName || 'Automated / Console',
    type: bp.type as any,
    reason: bp.reason,
    status: bp.status,
    createdAt: bp.createdAt,
    expiresAt: bp.expiresAt,
    serverScope: bp.serverScope || 'GLOBAL',
    evidenceUrl: bp.evidenceUrl,
    appealId: bp.appealId
  };
};

export const adaptBackendAppeal = (ba: BackendAppeal): AppealTicket => {
  return {
    id: ba.id,
    punishmentId: ba.punishmentId,
    playerUsername: ba.playerUsername,
    playerUuid: ba.playerUuid,
    type: ba.type,
    originalReason: ba.originalReason,
    appealReason: ba.appealReason,
    createdAt: ba.createdAt,
    status: ba.status,
    aiSentimentScore: ba.aiSentimentScore ?? 80,
    aiRecommendedAction: ba.aiRecommendedAction ?? 'ACCEPT',
    aiAnalysisSummary: ba.aiAnalysisSummary ?? 'Awaiting staff evaluation.',
    assignedStaff: ba.assignedStaff
  };
};

export const adaptBackendAltCluster = (ba: BackendAltFlag): AltAccountCluster => {
  return {
    id: ba.id,
    rootIdentifier: ba.rootIdentifier || 'IP: 192.168.1.1',
    clusterType: ba.clusterType || 'IP_SHARED',
    confidence: ba.confidence || 90,
    primaryAccount: (ba.associatedAccounts && ba.associatedAccounts.length > 0) ? ba.associatedAccounts[0] : 'Unknown',
    associatedAccounts: ba.associatedAccounts || [],
    bannedCount: ba.bannedCount || 0,
    status: ba.status || 'INVESTIGATING',
    notes: ba.notes || 'Alt cluster detected'
  };
};

export const adaptBackendPlayer = (raw: any): PlayerRecord => {
  return {
    uuid: raw.uuid || raw.player_uuid || `uuid-${Math.random().toString(36).substring(2, 9)}`,
    username: raw.username || raw.player_name || 'Player',
    currentServer: raw.currentServer || raw.current_server || null,
    online: Boolean(raw.online),
    ipAddress: raw.ipAddress || raw.ip || '127.0.0.1',
    firstJoined: raw.firstJoined || raw.first_joined || new Date().toISOString(),
    lastSeen: raw.lastSeen || raw.last_seen || new Date().toISOString(),
    playtimeHours: raw.playtimeHours || raw.playtime_hours || 0,
    rank: raw.rank || 'Player',
    suspicionScore: raw.suspicionScore || raw.suspicion_score || 0,
    pingMs: raw.pingMs || raw.ping || 20,
    clientBrand: raw.clientBrand || raw.client_brand || 'Vanilla',
    altAccountsCount: raw.altAccountsCount || raw.alt_accounts_count || 0,
    isVpn: Boolean(raw.isVpn || raw.is_vpn),
    warningCount: raw.warningCount || raw.warning_count || 0,
    punishmentHistoryCount: raw.punishmentHistoryCount || raw.punishment_history_count || 0
  };
};
