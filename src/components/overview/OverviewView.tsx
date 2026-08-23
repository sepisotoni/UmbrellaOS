import React, { useState, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { api, ServerRecord, AnticheatViolationRecord, PunishmentSchema, AppealSchema } from '../../lib/api';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  Server,
  Users,
  ShieldAlert,
  Scale,
  Activity,
  RefreshCw,
  Megaphone,
  AlertCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';

interface OverviewViewProps {
  onOpenBanModal?: () => void;
  onOpenBroadcastModal?: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  onOpenBanModal,
  onOpenBroadcastModal,
}) => {
  const {
    setActiveTab,
    navigateToPlayer,
    navigateToServerConsole,
    navigateToAppeal,
    isDisconnected,
  } = useDashboard();

  const [servers, setServers] = useState<ServerRecord[]>([]);
  const [recentFlags, setRecentFlags] = useState<AnticheatViolationRecord[]>([]);
  const [activeBansCount, setActiveBansCount] = useState<number>(0);
  const [activeAppealsCount, setActiveAppealsCount] = useState<number>(0);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverviewData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [serversRes, flagsRes, bansRes, appealsRes] = await Promise.allSettled([
        api.getServers(),
        api.getAnticheatViolations({ limit: 15 }),
        api.getPunishments({ active_only: true, limit: 100 }),
        api.getAppeals({ status: 'pending', limit: 100 }),
      ]);

      if (serversRes.status === 'fulfilled') {
        setServers(serversRes.value || []);
      }
      if (flagsRes.status === 'fulfilled') {
        setRecentFlags(flagsRes.value || []);
      }
      if (bansRes.status === 'fulfilled') {
        setActiveBansCount((bansRes.value || []).length);
      }
      if (appealsRes.status === 'fulfilled') {
        setActiveAppealsCount((appealsRes.value || []).length);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch network overview metrics');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOverviewData();
  }, []);

  const totalPlayersOnline = servers.reduce((acc, s) => acc + (s.players || 0), 0);
  const onlineServersCount = servers.filter((s) => s.status === 'online').length;
  const avgTps = servers.length > 0
    ? (servers.reduce((acc, s) => acc + (s.tps || 0), 0) / servers.length).toFixed(1)
    : '20.0';

  return (
    <div id="umbrella-overview-view" className="space-y-6">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Network Overview</span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-indigo-950/80 border border-indigo-800/40 text-indigo-300">
              Live Fleet
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time status across Minecraft instances, anticheat triggers, and moderation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {onOpenBroadcastModal && (
            <button
              id="overview-broadcast-btn"
              onClick={onOpenBroadcastModal}
              className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/40 bg-indigo-950/50 px-3 py-1.5 text-xs font-semibold text-indigo-200 hover:bg-indigo-900/60 transition cursor-pointer"
            >
              <Megaphone className="h-3.5 w-3.5 text-indigo-400" />
              <span>Broadcast</span>
            </button>
          )}

          {onOpenBanModal && (
            <button
              id="overview-punish-btn"
              onClick={onOpenBanModal}
              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/40 bg-rose-950/40 px-3 py-1.5 text-xs font-semibold text-rose-200 hover:bg-rose-900/50 transition cursor-pointer"
            >
              <ShieldAlert className="h-3.5 w-3.5 text-rose-400" />
              <span>Issue Punishment</span>
            </button>
          )}

          <button
            id="overview-refresh-btn"
            onClick={fetchOverviewData}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#141d3d] bg-[#060b1c] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-indigo-500/40 hover:text-white transition cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
          <div>
            <div className="font-bold">Error loading live telemetry:</div>
            <p className="mt-0.5 text-rose-200/80">{error}</p>
          </div>
        </div>
      )}

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Servers Online */}
        <div
          id="stat-servers-online"
          onClick={() => setActiveTab('servers')}
          className="rounded-xl border border-[#141d3d] bg-[#060b1c] p-5 shadow-lg hover:border-indigo-500/40 transition cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider font-mono">
              Servers Online
            </span>
            <div className="h-8 w-8 rounded-lg bg-indigo-950/70 border border-indigo-800/40 flex items-center justify-center text-indigo-400 group-hover:scale-105 transition">
              <Server className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">
              {isLoading ? '...' : onlineServersCount}
            </span>
            <span className="text-xs text-slate-500 font-mono">/ {servers.length} configured</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5 text-[11px] text-indigo-300">
            <span>Avg TPS: <strong className="font-mono text-white">{avgTps}</strong></span>
          </div>
        </div>

        {/* Card 2: Players Online */}
        <div
          id="stat-players-online"
          onClick={() => setActiveTab('players')}
          className="rounded-xl border border-[#141d3d] bg-[#060b1c] p-5 shadow-lg hover:border-emerald-500/40 transition cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider font-mono">
              Players Online
            </span>
            <div className="h-8 w-8 rounded-lg bg-emerald-950/60 border border-emerald-800/40 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition">
              <Users className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">
              {isLoading ? '...' : totalPlayersOnline}
            </span>
            <span className="text-xs text-emerald-400 font-mono flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live
            </span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400">
            Across active Minecraft instances
          </div>
        </div>

        {/* Card 3: GrimAC Violations */}
        <div
          id="stat-grim-violations"
          onClick={() => setActiveTab('moderation')}
          className="rounded-xl border border-[#141d3d] bg-[#060b1c] p-5 shadow-lg hover:border-rose-500/40 transition cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider font-mono">
              GrimAC Flags
            </span>
            <div className="h-8 w-8 rounded-lg bg-rose-950/60 border border-rose-800/40 flex items-center justify-center text-rose-400 group-hover:scale-105 transition">
              <ShieldAlert className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">
              {isLoading ? '...' : recentFlags.length}
            </span>
            <span className="text-xs text-slate-400">recent alerts</span>
          </div>
          <div className="mt-2 text-[11px] text-rose-300/80">
            Active cheat heuristics detection
          </div>
        </div>

        {/* Card 4: Active Appeals */}
        <div
          id="stat-active-appeals"
          onClick={() => setActiveTab('appeals')}
          className="rounded-xl border border-[#141d3d] bg-[#060b1c] p-5 shadow-lg hover:border-amber-500/40 transition cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider font-mono">
              Pending Appeals
            </span>
            <div className="h-8 w-8 rounded-lg bg-amber-950/60 border border-amber-800/40 flex items-center justify-center text-amber-400 group-hover:scale-105 transition">
              <Scale className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">
              {isLoading ? '...' : activeAppealsCount}
            </span>
            <span className="text-xs text-amber-400">awaiting review</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400">
            Active bans: <strong className="font-mono text-white">{activeBansCount}</strong>
          </div>
        </div>
      </div>

      {/* Main Grid: Fleet Status & Recent GrimAC Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Servers / Fleet Panel */}
        <div className="lg:col-span-2 rounded-xl border border-[#141d3d] bg-[#060b1c] p-5 shadow-xl">
          <div className="flex items-center justify-between pb-4 border-b border-[#141d3d]">
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-indigo-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                Fleet Instances
              </h2>
            </div>
            <button
              onClick={() => setActiveTab('servers')}
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium cursor-pointer"
            >
              <span>Manage Fleet</span>
              <ArrowRight className="h-3 w-3" />
            </button>
          </div>

          <div className="mt-4 space-y-3">
            {isLoading ? (
              <div className="py-8 text-center text-xs text-slate-500 font-mono">
                Loading server telemetry...
              </div>
            ) : servers.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500 font-mono">
                No active servers reported. Check Minecraft plugin connection.
              </div>
            ) : (
              servers.map((srv) => (
                <div
                  key={srv.id}
                  id={`overview-server-${srv.id}`}
                  onClick={() => navigateToServerConsole(srv.id)}
                  className="flex items-center justify-between rounded-lg border border-[#141d3d] bg-[#02040a] p-3 hover:border-indigo-500/40 transition cursor-pointer group"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-2.5 w-2.5 rounded-full ${
                        srv.status === 'online'
                          ? 'bg-emerald-400 animate-pulse'
                          : srv.status === 'warning'
                          ? 'bg-amber-400'
                          : 'bg-rose-500'
                      }`}
                    />
                    <div>
                      <div className="text-xs font-bold text-white group-hover:text-indigo-300 transition">
                        {srv.name}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {srv.version || 'Paper 1.20.4'}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-xs font-mono">
                    <div className="text-right">
                      <div className="text-slate-200">
                        {srv.players} <span className="text-slate-500">/ {srv.maxPlayers}</span>
                      </div>
                      <div className="text-[10px] text-slate-500">Players</div>
                    </div>

                    <div className="text-right min-w-[50px]">
                      <div
                        className={`font-bold ${
                          srv.tps >= 19.5
                            ? 'text-emerald-400'
                            : srv.tps >= 17
                            ? 'text-amber-400'
                            : 'text-rose-400'
                        }`}
                      >
                        {srv.tps.toFixed(1)}
                      </div>
                      <div className="text-[10px] text-slate-500">TPS</div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* GrimAC Alerts Feed */}
        <div className="rounded-xl border border-[#141d3d] bg-[#060b1c] p-5 shadow-xl flex flex-col">
          <div className="flex items-center justify-between pb-4 border-b border-[#141d3d]">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-rose-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                GrimAC Activity
              </h2>
            </div>
            <button
              onClick={() => setActiveTab('moderation')}
              className="text-xs text-rose-400 hover:text-rose-300 flex items-center gap-1 font-medium cursor-pointer"
            >
              <span>All Flags</span>
              <ArrowRight className="h-3 w-3" />
            </button>
          </div>

          <div className="mt-4 space-y-2.5 flex-1 overflow-y-auto max-h-[360px]">
            {isLoading ? (
              <div className="py-8 text-center text-xs text-slate-500 font-mono">
                Loading violation records...
              </div>
            ) : recentFlags.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500 font-mono">
                No recent anticheat violations recorded.
              </div>
            ) : (
              recentFlags.map((flag) => (
                <div
                  key={flag.id}
                  onClick={() => navigateToPlayer(flag.player_uuid)}
                  className="rounded-lg border border-[#141d3d] bg-[#02040a] p-2.5 hover:border-rose-500/40 transition cursor-pointer"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-200">
                      {flag.player_name || flag.player_uuid.slice(0, 8)}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold bg-rose-950/80 text-rose-300 border border-rose-800/40">
                      VL {flag.vl}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="text-rose-400 font-mono">{flag.check_name}</span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {flag.created_at ? new Date(flag.created_at).toLocaleTimeString() : ''}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
