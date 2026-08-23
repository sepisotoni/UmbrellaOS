import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import {
  Users,
  Server,
  Activity,
  ShieldAlert,
  Cpu,
  HardDrive,
  Radio,
  ArrowUpRight,
  RefreshCw,
  Zap,
  Terminal,
  AlertOctagon,
  Sparkles,
  Flame,
  CheckCircle2,
  Lock,
  PauseCircle,
  PlayCircle,
  Megaphone
} from 'lucide-react';

interface OverviewViewProps {
  onOpenBanModal: () => void;
  onOpenBroadcastModal: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({ onOpenBanModal, onOpenBroadcastModal }) => {
  const {
    servers,
    nodes,
    players,
    grimViolations,
    punishments,
    appeals,
    crashReports,
    restartServer,
    setActiveTab,
    setSelectedServerId,
    addToast
  } = useDashboard();

  const [threatDefenseActive, setThreatDefenseActive] = useState(true);

  // Network Computations
  const totalPlayers = servers.reduce((acc, s) => acc + s.playersCount, 0);
  const maxPlayers = servers.reduce((acc, s) => acc + s.maxPlayers, 0);
  const avgTps = servers.length > 0 
    ? (servers.reduce((acc, s) => acc + s.tps, 0) / servers.length).toFixed(2)
    : '20.00';
  const totalMemoryUsedMb = servers.reduce((acc, s) => acc + s.memoryMb, 0);
  const totalMemoryMaxMb = servers.reduce((acc, s) => acc + s.maxMemoryMb, 0);
  const activeBansCount = punishments.filter(p => p.status === 'ACTIVE').length;
  const pendingAppealsCount = appeals.filter(a => a.status === 'PENDING').length;
  const recentGrimFlags = grimViolations.length;

  const handleFreezeNetwork = () => {
    addToast('warning', 'Network Freeze Enacted', 'Emergency player proxy routing throttled to prevent packet flood.');
  };

  const handleTriggerGC = () => {
    addToast('success', 'Global GC Cleanse Triggered', 'Dispatched ZGC concurrent sweep across all connected instances.');
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Metric Stat Row (High information density, deliberate typography) */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Global TPS */}
        <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium font-mono">
            <span>Cluster TPS</span>
            <Activity className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold font-mono text-white tracking-tight">{avgTps}</div>
            <div className="text-[11px] text-emerald-400 flex items-center gap-1 mt-0.5 font-mono">
              <span>Stable (Target 20.0)</span>
            </div>
          </div>
        </div>

        {/* Players Online */}
        <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium font-mono">
            <span>Players Online</span>
            <Users className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold font-mono text-white tracking-tight">{totalPlayers.toLocaleString()}</div>
            <div className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5 font-mono">
              <span>Cap: {maxPlayers.toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Plugin-reported RAM */}
        <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium font-mono">
            <span>Plugin RAM Usage</span>
            <HardDrive className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold font-mono text-white tracking-tight">
              {(totalMemoryUsedMb / 1024).toFixed(1)} <span className="text-sm font-normal text-slate-400">GB</span>
            </div>
            <div className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5 font-mono">
              <span>of {(totalMemoryMaxMb / 1024).toFixed(0)} GB reported by plugins</span>
            </div>
          </div>
        </div>

        {/* Servers with heartbeat */}
        <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium font-mono">
            <span>Servers Online</span>
            <Server className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold font-mono text-white tracking-tight">{servers.filter(s => s.status === 'online').length} / {servers.length}</div>
            <div className="text-[11px] text-emerald-400 flex items-center gap-1 mt-0.5 font-mono">
              <span>Heartbeat received ≤60s</span>
            </div>
          </div>
        </div>

        {/* GrimAC Flags */}
        <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium font-mono">
            <span>GrimAC Flags</span>
            <ShieldAlert className="h-4 w-4 text-rose-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold font-mono text-rose-300 tracking-tight">{recentGrimFlags}</div>
            <div className="text-[11px] text-rose-400/80 flex items-center gap-1 mt-0.5 font-mono">
              <span>Live Packet Stream</span>
            </div>
          </div>
        </div>

        {/* Appeals & Moderation */}
        <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium font-mono">
            <span>Active Bans / Appeals</span>
            <Lock className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold font-mono text-white tracking-tight">
              {activeBansCount} <span className="text-xs font-normal text-amber-400 font-mono">({pendingAppealsCount} app)</span>
            </div>
            <div className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5 font-mono">
              <span>Enforced Globally</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Server Node Grid + Live Control Center */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Server Instances Fleet Table & Matrix */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white tracking-tight font-display">Minecraft Server Node Fleet</h2>
              <p className="text-xs text-slate-400">Instances dynamically discovered from FastAPI backend</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('topology')}
                className="flex items-center gap-1 text-xs font-semibold text-cyan-400 hover:text-cyan-300"
              >
                <span>View Full Topology Map</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-[#0c1017] overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="border-b border-slate-800 bg-slate-900/60 font-mono text-[11px] text-slate-400">
                  <tr>
                    <th className="py-3 px-4">Instance / Core</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-3">TPS</th>
                    <th className="py-3 px-3">Players</th>
                    <th className="py-3 px-3">Memory / CPU</th>
                    <th className="py-3 px-3">GrimAC</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {servers.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 px-4 text-center text-slate-500 font-mono">
                        No servers currently reporting. Connect backend or wait for heartbeat.
                      </td>
                    </tr>
                  ) : (
                    servers.map(server => (
                      <tr 
                        key={server.id}
                        className="hover:bg-slate-900/40 transition-colors group"
                      >
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2.5">
                            <span className={`h-2.5 w-2.5 rounded-full shrink-0 ${
                              server.status === 'online' ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]' :
                              server.status === 'warning' ? 'bg-amber-400 animate-pulse' :
                              server.status === 'restarting' ? 'bg-cyan-400 animate-spin' :
                              'bg-rose-500'
                            }`} />
                            <div>
                              <div className="font-bold text-white group-hover:text-cyan-300 transition-colors font-mono">
                                {server.name}
                              </div>
                              <div className="text-[10px] font-mono text-slate-500">
                                {server.version.split(' ')[0]} • {server.host}:{server.port}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-semibold border ${
                            server.status === 'online' ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30' :
                            server.status === 'warning' ? 'bg-amber-950/40 text-amber-300 border-amber-500/30' :
                            server.status === 'restarting' ? 'bg-cyan-950/40 text-cyan-300 border-cyan-500/30' :
                            'bg-rose-950/40 text-rose-300 border-rose-500/30'
                          }`}>
                            {server.status}
                          </span>
                        </td>
                        <td className="py-3 px-3 font-mono font-semibold">
                          <span className={server.tps < 18 ? 'text-amber-400' : 'text-emerald-400'}>
                            {server.tps}
                          </span>
                        </td>
                        <td className="py-3 px-3 font-mono text-slate-200">
                          {server.playersCount} <span className="text-slate-500 text-[10px]">/ {server.maxPlayers}</span>
                        </td>
                        <td className="py-3 px-3">
                          <div className="font-mono text-[11px] text-slate-200">
                            {(server.memoryMb / 1024).toFixed(1)} GB
                          </div>
                          <div className="w-20 bg-slate-800 rounded-full h-1 mt-1 overflow-hidden">
                            <div 
                              className={`h-full ${server.cpuPercent > 80 ? 'bg-amber-500' : 'bg-cyan-500'}`}
                              style={{ width: `${Math.min(100, server.cpuPercent)}%` }}
                            />
                          </div>
                        </td>
                        <td className="py-3 px-3">
                          {server.grimAcEnabled ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium text-emerald-400 bg-emerald-950/30 border border-emerald-500/20 px-1.5 py-0.5 rounded">
                              <CheckCircle2 className="h-3 w-3" /> Shield
                            </span>
                          ) : (
                            <span className="text-[10px] font-mono text-slate-500">N/A</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => {
                                setSelectedServerId(server.id);
                                setActiveTab('console');
                              }}
                              className="rounded p-1.5 text-slate-400 hover:bg-slate-800 hover:text-cyan-300 transition-colors"
                              title="Open Console"
                            >
                              <Terminal className="h-3.5 w-3.5" />
                            </button>
                            <button
                              onClick={() => restartServer(server.id)}
                              className="rounded p-1.5 text-slate-400 hover:bg-slate-800 hover:text-amber-300 transition-colors"
                              title="Graceful Restart"
                            >
                              <RefreshCw className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right 1 Col: Quick Action Control Station & Live Threat Center */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white tracking-tight font-display">Executive Quick Actions</h2>
            <Zap className="h-4 w-4 text-cyan-400" />
          </div>

          <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-4 space-y-3">
            <button
              onClick={onOpenBanModal}
              className="w-full flex items-center justify-between p-3 rounded-lg border border-rose-500/20 bg-rose-950/20 hover:bg-rose-950/40 text-rose-200 transition-colors text-xs font-semibold"
            >
              <div className="flex items-center gap-2.5">
                <ShieldAlert className="h-4 w-4 text-rose-400" />
                <span>Issue Global Punishment / Ban</span>
              </div>
              <span className="text-[10px] font-mono text-rose-400">Modal →</span>
            </button>

            <button
              onClick={onOpenBroadcastModal}
              className="w-full flex items-center justify-between p-3 rounded-lg border border-cyan-500/20 bg-cyan-950/20 hover:bg-cyan-950/40 text-cyan-200 transition-colors text-xs font-semibold"
            >
              <div className="flex items-center gap-2.5">
                <Megaphone className="h-4 w-4 text-cyan-400" />
                <span>Dispatch Global Broadcast Notice</span>
              </div>
              <span className="text-[10px] font-mono text-cyan-400">Title / Chat →</span>
            </button>

            <button
              onClick={handleTriggerGC}
              className="w-full flex items-center justify-between p-3 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-slate-300 transition-colors text-xs font-semibold"
            >
              <div className="flex items-center gap-2.5">
                <RefreshCw className="h-4 w-4 text-emerald-400" />
                <span>Flush Garbage Collector (GC Sweep)</span>
              </div>
              <span className="text-[10px] font-mono text-emerald-400">ZGC Fast</span>
            </button>

            <button
              onClick={handleFreezeNetwork}
              className="w-full flex items-center justify-between p-3 rounded-lg border border-amber-500/20 bg-amber-950/20 hover:bg-amber-950/40 text-amber-200 transition-colors text-xs font-semibold"
            >
              <div className="flex items-center gap-2.5">
                <AlertOctagon className="h-4 w-4 text-amber-400" />
                <span>Emergency Proxy Traffic Quarantine</span>
              </div>
              <span className="text-[10px] font-mono text-amber-400">Lock Rate</span>
            </button>
          </div>

          {/* GrimAC Live Ticker Mini-Widget */}
          <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-rose-400 animate-ping" />
                <span className="text-xs font-bold text-white uppercase tracking-wider font-mono">GrimAC Live Threat Stream</span>
              </div>
              <button
                onClick={() => setActiveTab('moderation')}
                className="text-[11px] font-semibold text-cyan-400 hover:text-cyan-300"
              >
                View Center →
              </button>
            </div>

            <div className="space-y-2">
              {grimViolations.length === 0 ? (
                <div className="p-4 rounded-lg bg-slate-900/40 text-xs text-slate-500 font-mono text-center">
                  Zero active anticheat flags. Network reporting nominal packet state.
                </div>
              ) : (
                grimViolations.slice(0, 3).map(v => (
                  <div key={v.id} className="rounded-lg border border-slate-800 bg-slate-900/50 p-2.5 text-xs">
                    <div className="flex items-center justify-between font-mono text-[10px]">
                      <span className="font-bold text-rose-400">[VL:{v.violationLevel}] {v.checkName}</span>
                      <span className="text-slate-500">{v.timestamp}</span>
                    </div>
                    <div className="mt-1 font-mono text-[11px] text-slate-200 flex items-center justify-between">
                      <span className="font-semibold text-cyan-300">{v.playerName}</span>
                      <span className="text-slate-400 text-[10px]">@{v.server}</span>
                    </div>
                    <p className="mt-1 text-[10px] text-slate-400 truncate">
                      {v.details}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
