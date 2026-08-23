import React, { useState, useEffect } from 'react';
import { api, PluginHeartbeatStatus } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  Cpu,
  Shield,
  Activity,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  Zap,
} from 'lucide-react';

export const PluginsView: React.FC = () => {
  const [plugins, setPlugins] = useState<PluginHeartbeatStatus[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPlugins = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getPluginsHeartbeat();
      setPlugins(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load plugin status');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPlugins();
  }, []);

  return (
    <div id="umbrella-plugins-view" className="space-y-6">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Plugin Ecosystem & Heartbeats</span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-purple-950/80 border border-purple-800/40 text-purple-300">
              {plugins.length} Server Hooks
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Status of UmbrellaOS Bridge and GrimAC anticheat hooks across your fleet.
          </p>
        </div>

        <button
          id="plugins-refresh-btn"
          onClick={fetchPlugins}
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
            <span className="font-bold">Error loading plugin heartbeats:</span>
            <p className="mt-0.5 text-rose-200/80">{error}</p>
          </div>
        </div>
      )}

      {/* Plugins Table */}
      <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
        {isLoading ? (
          <div className="py-12 text-center text-xs text-slate-500 font-mono">
            Checking plugin heartbeat signals from core...
          </div>
        ) : plugins.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500 font-mono">
            No plugin heartbeats detected. Ensure `UmbrellaPlugin` is active in `plugins/`.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-[#1e1b4b] text-slate-400">
                  <th className="pb-3 font-semibold">Server</th>
                  <th className="pb-3 font-semibold">UmbrellaOS Bridge</th>
                  <th className="pb-3 font-semibold">Bridge Version</th>
                  <th className="pb-3 font-semibold">GrimAC Hook</th>
                  <th className="pb-3 font-semibold">Last Heartbeat</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e1b4b]/60">
                {plugins.map((p) => (
                  <tr key={p.server_id} className="hover:bg-[#121638]/50 transition">
                    <td className="py-3 font-bold text-white flex items-center gap-2">
                      <Cpu className="h-4 w-4 text-purple-400" />
                      <span>{p.server_name || p.server_id}</span>
                    </td>

                    <td className="py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                          p.umbrella_status === 'ACTIVE'
                            ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/40'
                            : 'bg-rose-950/80 text-rose-300 border border-rose-800/40'
                        }`}
                      >
                        <CheckCircle2 className="h-3 w-3" />
                        {p.umbrella_status}
                      </span>
                    </td>

                    <td className="py-3 text-purple-300">
                      v{p.umbrella_version || '1.0.0'}
                    </td>

                    <td className="py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                          p.grimac_status === 'ACTIVE'
                            ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/40'
                            : 'bg-amber-950/80 text-amber-300 border border-amber-800/40'
                        }`}
                      >
                        <Shield className="h-3 w-3" />
                        {p.grimac_status || 'STANDALONE'}
                      </span>
                    </td>

                    <td className="py-3 text-slate-400 text-[11px]">
                      {p.last_heartbeat
                        ? new Date(p.last_heartbeat).toLocaleTimeString()
                        : 'Active (<30s)'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
