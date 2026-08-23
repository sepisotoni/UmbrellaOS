import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { UmbrellaLogo } from '../common/UmbrellaLogo';
import { 
  Search, 
  Bell, 
  Megaphone,
  Server,
  Zap,
  Globe,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';

interface HeaderProps {
  onOpenBroadcastModal?: () => void;
  onOpenCommandPalette?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenBroadcastModal, onOpenCommandPalette }) => {
  const { 
    setCommandPaletteOpen, 
    setAccountModalOpen,
    setActiveTab,
    sidebarCollapsed,
    toggleSidebar,
    currentUser,
    backendStatus,
    backendLatencyMs,
    servers, 
    players,
    grimViolations,
    dashboardTheme
  } = useDashboard();

  const [notificationOpen, setNotificationOpen] = useState(false);

  const onlinePlayersCount = players.filter(p => p.online).length;
  const avgTps = (servers.reduce((acc, s) => acc + s.tps, 0) / (servers.length || 1)).toFixed(2);
  const onlineServersCount = servers.filter(s => s.status === 'online').length;
  const warningNodes = servers.filter(s => s.status === 'warning' || s.status === 'offline').length;

  const isLight = dashboardTheme === 'solar-clean';
  const isMatrix = dashboardTheme === 'voxel-matrix';
  const isObsidian = dashboardTheme === 'obsidian-minimal';

  const headerBg = isLight
    ? 'border-slate-200 bg-white/95 text-slate-800'
    : isMatrix
    ? 'border-emerald-950/80 bg-black/95 text-emerald-300 font-mono'
    : isObsidian
    ? 'border-zinc-800 bg-[#121214]/95 text-zinc-100'
    : 'border-slate-800 bg-[#090b10]/95 text-slate-100';

  const buttonBase = isLight
    ? 'border-slate-200 bg-slate-100 text-slate-600 hover:border-slate-300 hover:text-slate-900'
    : isMatrix
    ? 'border-emerald-900 bg-emerald-950/50 text-emerald-300 hover:border-emerald-700 hover:text-emerald-100 font-mono'
    : isObsidian
    ? 'border-zinc-800 bg-zinc-900 text-zinc-300 hover:border-zinc-700 hover:text-white'
    : 'border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700 hover:text-white';

  return (
    <header className={`shrink-0 z-30 flex h-14 w-full items-center justify-between border-b px-4 backdrop-blur-md transition-colors ${headerBg}`}>
      {/* Zone 1: Sidebar Toggle, Brand Wordmark & Fast Status Pill */}
      <div className="flex items-center gap-3">
        <button
          onClick={toggleSidebar}
          className={`flex h-8 w-8 items-center justify-center rounded-lg border transition-colors cursor-pointer ${buttonBase}`}
          title={sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {sidebarCollapsed ? (
            <PanelLeftOpen className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </button>

        <UmbrellaLogo size="sm" />

        <div className={`hidden sm:flex items-center gap-2 rounded-full border px-2.5 py-0.5 text-xs ${
          isLight
            ? 'border-emerald-300 bg-emerald-50 text-emerald-700 font-medium'
            : isMatrix
            ? 'border-emerald-500/30 bg-emerald-950/50 text-emerald-300'
            : isObsidian
            ? 'border-purple-500/30 bg-purple-950/30 text-purple-300'
            : 'border-emerald-500/20 bg-emerald-950/30 text-emerald-300'
        }`}>
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-mono font-medium">{avgTps} TPS</span>
          <span className="opacity-50">•</span>
          <span className="font-mono">{onlinePlayersCount || servers.reduce((a, b) => a + b.playersCount, 0)} Online</span>
        </div>
      </div>

      {/* Zone 2: Cluster Operational Status Bar */}
      <div className="hidden xl:flex items-center gap-4 text-xs font-mono text-slate-400">
        <div className={`flex items-center gap-2 px-3 py-1 rounded-lg border ${
          isLight ? 'bg-slate-50 border-slate-200 text-slate-600' : 'bg-slate-900/60 border-slate-800'
        }`}>
          <Server className={`h-3.5 w-3.5 ${isLight ? 'text-blue-600' : 'text-cyan-400'}`} />
          <span>Nodes:</span>
          <span className={`font-bold ${isLight ? 'text-slate-900' : 'text-white'}`}>{onlineServersCount}/{servers.length} Online</span>
        </div>

        <div className={`flex items-center gap-2 px-3 py-1 rounded-lg border ${
          isLight ? 'bg-slate-50 border-slate-200 text-slate-600' : 'bg-slate-900/60 border-slate-800'
        }`}>
          <Globe className="h-3.5 w-3.5 text-emerald-500" />
          <span>Proxy:</span>
          <span className={`font-bold ${isLight ? 'text-emerald-700' : 'text-emerald-300'}`}>Velocity (Edge)</span>
        </div>

        <div className={`flex items-center gap-2 px-3 py-1 rounded-lg border ${
          isLight ? 'bg-slate-50 border-slate-200 text-slate-600' : 'bg-slate-900/60 border-slate-800'
        }`}>
          <Zap className={`h-3.5 w-3.5 ${isLight ? 'text-purple-600' : 'text-purple-400'}`} />
          <span>Backend:</span>
          <span className={isLight ? 'text-slate-700' : 'text-slate-300'}>FastAPI</span>
          {backendLatencyMs !== null && (
            <span className="text-emerald-500 font-bold">({backendLatencyMs}ms)</span>
          )}
        </div>
      </div>

      {/* Zone 3: Primary Actions (Search, Broadcast, Profile, Notifications) */}
      <div className="flex items-center gap-2">
        {/* Quick Command Palette Button */}
        <button
          onClick={() => (onOpenCommandPalette ? onOpenCommandPalette() : setCommandPaletteOpen(true))}
          className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs transition-colors ${buttonBase}`}
          title="Global Command Palette (Cmd + K)"
        >
          <Search className="h-3.5 w-3.5" />
          <span className="hidden sm:inline font-medium">Quick Find</span>
          <kbd className="hidden sm:inline-flex items-center rounded border px-1.5 py-0.2 text-[10px] font-mono opacity-70">
            ⌘K
          </kbd>
        </button>

        {/* Broadcast Action Button */}
        <button
          onClick={onOpenBroadcastModal}
          className={`flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
            isLight
              ? 'bg-blue-600 hover:bg-blue-700'
              : isMatrix
              ? 'bg-emerald-600 hover:bg-emerald-500'
              : isObsidian
              ? 'bg-purple-600 hover:bg-purple-500'
              : 'bg-cyan-600 hover:bg-cyan-500'
          }`}
        >
          <Megaphone className="h-3.5 w-3.5" />
          <span>Broadcast</span>
        </button>

        {/* Connected Account & Backend Status Badge */}
        <button
          onClick={() => setAccountModalOpen(true)}
          className={`flex items-center gap-2 rounded-lg border px-2.5 py-1 text-xs transition-all text-left group cursor-pointer ${buttonBase}`}
          title="View Connected Account & Backend Status"
        >
          <div className="relative shrink-0">
            {currentUser?.avatarUrl ? (
              <img
                src={currentUser.avatarUrl}
                alt={currentUser.username}
                className="h-6 w-6 rounded-md object-cover border border-cyan-500/40"
              />
            ) : (
              <div className={`h-6 w-6 rounded-md border flex items-center justify-center font-mono font-bold text-[11px] ${
                isLight 
                  ? 'bg-blue-50 border-blue-200 text-blue-700' 
                  : isMatrix 
                  ? 'bg-emerald-950 border-emerald-500 text-emerald-400' 
                  : 'bg-cyan-950/80 border-cyan-500/40 text-cyan-400'
              }`}>
                {currentUser?.username ? currentUser.username.charAt(0).toUpperCase() : 'U'}
              </div>
            )}
            <span
              className={`absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full border border-black ${
                backendStatus === 'connected' ? 'bg-emerald-400 animate-pulse' :
                backendStatus === 'connecting' ? 'bg-cyan-400' :
                backendStatus === 'unauthorized' ? 'bg-amber-400' :
                'bg-rose-400'
              }`}
            />
          </div>

          <div className="hidden sm:flex flex-col min-w-0 pr-1">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-[11px] truncate max-w-[110px]">
                {currentUser?.username || 'Guest Staff'}
              </span>
              <span className={`px-1.5 py-0.2 rounded text-[9px] font-mono uppercase font-bold border ${
                isLight
                  ? 'bg-blue-100 text-blue-700 border-blue-200'
                  : 'bg-cyan-950/80 text-cyan-300 border-cyan-500/30'
              }`}>
                {currentUser?.role || 'Staff'}
              </span>
            </div>
          </div>
        </button>

        {/* Notifications bell */}
        <div className="relative">
          <button
            onClick={() => setNotificationOpen(!notificationOpen)}
            className={`relative flex h-8 w-8 items-center justify-center rounded-lg border transition-colors cursor-pointer ${buttonBase}`}
          >
            <Bell className="h-4 w-4" />
            {warningNodes > 0 && (
              <span className="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-amber-500" />
              </span>
            )}
          </button>

          {notificationOpen && (
            <div className={`absolute right-0 mt-2 w-80 rounded-xl border p-3 shadow-2xl z-50 ${
              isLight ? 'border-slate-200 bg-white text-slate-800' : 'border-slate-800 bg-[#0f131a] text-slate-100'
            }`}>
              <div className="flex items-center justify-between border-b border-slate-700/40 pb-2 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider">Live Activity Feed</span>
                <span className="text-[10px] font-mono text-cyan-400">{grimViolations.length} Events</span>
              </div>
              <div className="max-h-64 space-y-2 overflow-y-auto pr-1 text-xs">
                {grimViolations.slice(0, 4).map(v => (
                  <div key={v.id} className={`rounded-md border p-2 ${
                    isLight ? 'border-slate-200 bg-slate-50 text-slate-700' : 'border-slate-800 bg-slate-900/60 text-slate-300'
                  }`}>
                    <div className="flex items-center justify-between font-mono text-[10px]">
                      <span className="text-rose-500 font-semibold">[GrimAC] {v.checkName}</span>
                      <span className="text-slate-500">{v.timestamp}</span>
                    </div>
                    <p className="mt-1 font-mono text-[11px] truncate">
                      <strong className="text-cyan-400">{v.playerName}</strong> @ {v.server}: {v.details}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
