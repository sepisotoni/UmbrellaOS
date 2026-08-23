import React, { useState, useEffect } from 'react';
import { api, ServerRecord } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  Server,
  Activity,
  Users,
  Shield,
  Terminal,
  RefreshCw,
  AlertCircle,
  Radio,
  Clock,
  ExternalLink,
} from 'lucide-react';

export const ServersView: React.FC = () => {
  const { navigateToServerConsole } = useDashboard();
  const [servers, setServers] = useState<ServerRecord[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchServers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getServers();
      setServers(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve Minecraft fleet status');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
  }, []);

  const totalPlayers = servers.reduce((acc, s) => acc + (s.players || 0), 0);
  const onlineCount = servers.filter((s) => s.status === 'online').length;

  return (
    <div id="umbrella-fleet-view" className="space-y-6">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Minecraft Fleet Instances</span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-purple-950/80 border border-purple-800/40 text-purple-300">
              {onlineCount}/{servers.length} Online
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time TPS, player counts, GrimAC anticheat hooks, and heartbeat telemetry.
          </p>
        </div>

        <button
          id="servers-refresh-btn"
          onClick={fetchServers}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-purple-500/40 hover:text-white transition cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
          <div>
            <span className="font-bold">Error loading server fleet:</span>
            <p className="mt-0.5 text-rose-200/80">{error}</p>
          </div>
        </div>
      )}

      {/* Server Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {isLoading ? (
          <div className="col-span-full py-16 text-center text-xs text-slate-500 font-mono">
            Fetching live Minecraft telemetry...
          </div>
        ) : servers.length === 0 ? (
          <div className="col-span-full py-16 text-center text-xs text-slate-500 font-mono">
            No servers reported. Verify the UmbrellaOS Minecraft plugin heartbeat.
          </div>
        ) : (
          servers.map((srv) => (
            <div
              key={srv.id}
              id={`server-card-${srv.id}`}
              className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl hover:border-purple-500/40 transition flex flex-col justify-between"
            >
              <div>
                {/* Header */}
                <div className="flex items-center justify-between pb-3 border-b border-[#1e1b4b]">
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`h-3 w-3 rounded-full ${
                        srv.status === 'online'
                          ? 'bg-emerald-400 animate-pulse'
                          : srv.status === 'warning'
                          ? 'bg-amber-400'
                          : 'bg-rose-500'
                      }`}
                    />
                    <h3 className="font-bold text-white font-mono text-sm">{srv.name}</h3>
                  </div>

                  <span className="text-[10px] px-2 py-0.5 rounded font-mono font-bold bg-[#070914] text-purple-300 border border-[#1e1b4b]">
                    {srv.version || 'Paper 1.20.4'}
                  </span>
                </div>

                {/* Server Telemetry Metrics */}
                <div className="mt-4 grid grid-cols-2 gap-3 font-mono text-xs">
                  <div className="rounded-lg border border-[#1a1f42] bg-[#070914] p-3">
                    <div className="text-[10px] text-slate-400 uppercase">TPS Rating</div>
                    <div
                      className={`text-lg font-bold mt-1 ${
                        srv.tps >= 19.5
                          ? 'text-emerald-400'
                          : srv.tps >= 17
                          ? 'text-amber-400'
                          : 'text-rose-400'
                      }`}
                    >
                      {srv.tps.toFixed(2)}
                    </div>
                  </div>

                  <div className="rounded-lg border border-[#1a1f42] bg-[#070914] p-3">
                    <div className="text-[10px] text-slate-400 uppercase">Online Players</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {srv.players}{' '}
                      <span className="text-xs text-slate-500 font-normal">/ {srv.maxPlayers}</span>
                    </div>
                  </div>
                </div>

                {/* Plugin & GrimAC Status */}
                <div className="mt-4 space-y-2 text-xs font-mono">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <Shield className="h-3.5 w-3.5 text-purple-400" />
                      <span>GrimAC Anticheat:</span>
                    </span>
                    <span className="text-emerald-400 font-bold">
                      {srv.grim_status || 'Hooked & Active'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5 text-slate-500" />
                      <span>Last Heartbeat:</span>
                    </span>
                    <span className="text-slate-300">
                      {srv.last_heartbeat
                        ? new Date(srv.last_heartbeat).toLocaleTimeString()
                        : 'Live (<10s)'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Console Action */}
              <div className="mt-5 pt-3 border-t border-[#1e1b4b]">
                <button
                  id={`open-console-${srv.id}`}
                  onClick={() => navigateToServerConsole(srv.id)}
                  className="w-full flex items-center justify-center gap-2 rounded-lg border border-purple-500/40 bg-purple-950/40 hover:bg-purple-900/60 p-2 text-xs font-bold text-purple-200 transition cursor-pointer"
                >
                  <Terminal className="h-3.5 w-3.5 text-purple-400" />
                  <span>Open Live Console</span>
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
