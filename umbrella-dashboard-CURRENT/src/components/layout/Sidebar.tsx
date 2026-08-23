import React from 'react';
import { useDashboard, NavigationTab } from '../../context/DashboardContext';
import {
  LayoutDashboard,
  Users,
  Network,
  Terminal,
  ShieldAlert,
  BrainCircuit,
  History,
  ShieldCheck,
  FileText,
  UserCheck,
  Clock,
  Key,
  Sliders,
  Languages,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { UmbrellaCoreIcon, UmbrellaBotIcon, UmbrellaPluginIcon } from '../common/UmbrellaIcons';

interface SidebarProps {
  onOpenBanModal?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = () => {
  const { 
    activeTab, 
    setActiveTab, 
    players,
    grimViolations, 
    appeals, 
    crashReports,
    featureFlags,
    sidebarCollapsed,
    toggleSidebar,
    dashboardTheme
  } = useDashboard();

  const onlinePlayersCount = players.filter(p => p.online).length;
  const activeAppealsCount = appeals.filter(a => a.status === 'PENDING').length;
  const recentGrimFlags = grimViolations.length;
  const activeCrashCount = crashReports.filter(c => c.status === 'INVESTIGATING').length;

  // Real backend-aligned navigation categories
  const mainNavigation: { id: NavigationTab; label: string; icon: React.ComponentType<{ className?: string }>; badge?: string | number; badgeColor?: string }[] = [
    { id: 'overview', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'players', label: 'Players', icon: Users, badge: onlinePlayersCount > 0 ? `${onlinePlayersCount} on` : undefined, badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
    { id: 'topology', label: 'Servers', icon: Network },
    { id: 'console', label: 'Console', icon: Terminal },
    { 
      id: 'moderation', 
      label: 'Moderation', 
      icon: ShieldAlert,
      badge: activeAppealsCount > 0 ? activeAppealsCount : recentGrimFlags,
      badgeColor: activeAppealsCount > 0 ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' : 'bg-rose-500/20 text-rose-300 border-rose-500/30'
    },
    { 
      id: 'ai-intelligence', 
      label: 'AI Ops', 
      icon: BrainCircuit,
      badge: activeCrashCount > 0 ? `${activeCrashCount} triage` : undefined,
      badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30'
    },
    { id: 'plugins', label: 'Plugins', icon: UmbrellaPluginIcon },
    { id: 'discord', label: 'Discord Hub', icon: UmbrellaBotIcon, badge: 'Live', badgeColor: 'bg-[#5865F2]/20 text-[#5865F2] border-[#5865F2]/40' },
    { id: 'snapshots', label: 'Snapshots', icon: History },
    { id: 'staff', label: 'Staff & Roles', icon: ShieldCheck },
    { id: 'audit', label: 'Audit Logs', icon: FileText },
    { id: 'verification', label: 'Verification', icon: UserCheck },
    { id: 'translation', label: 'Translation', icon: Languages },
    { id: 'automation', label: 'Automation', icon: Clock },
    { id: 'api-hub', label: 'API Hub', icon: Key },
    { id: 'settings', label: 'Settings', icon: Sliders, badge: featureFlags.length, badgeColor: 'bg-slate-800 text-slate-400' },
  ];

  // Theme styling variants
  const isLight = dashboardTheme === 'solar-clean';
  const isMatrix = dashboardTheme === 'voxel-matrix';
  const isObsidian = dashboardTheme === 'obsidian-minimal';

  const sidebarBg = isLight 
    ? 'bg-slate-50 border-slate-200 text-slate-700' 
    : isMatrix 
    ? 'bg-black border-emerald-950/80 text-emerald-400 font-mono' 
    : isObsidian 
    ? 'bg-[#121214] border-zinc-800/80 text-zinc-300' 
    : 'bg-[#090b10] border-slate-800/80 text-slate-300';

  const activeItemStyle = isLight
    ? 'bg-blue-50 text-blue-700 border border-blue-200 shadow-xs'
    : isMatrix
    ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/50 shadow-[0_0_10px_rgba(16,185,129,0.2)]'
    : isObsidian
    ? 'bg-zinc-800 text-purple-300 border border-purple-500/40 shadow-xs'
    : 'bg-slate-800/90 text-cyan-300 border border-slate-700 shadow-xs';

  const inactiveItemStyle = isLight
    ? 'text-slate-600 hover:bg-slate-200/60 hover:text-slate-900'
    : isMatrix
    ? 'text-emerald-600 hover:bg-emerald-950/30 hover:text-emerald-300'
    : isObsidian
    ? 'text-zinc-400 hover:bg-zinc-850 hover:text-zinc-100'
    : 'text-slate-400 hover:bg-slate-900/60 hover:text-slate-100';

  const footerBg = isLight
    ? 'border-slate-200 bg-slate-100/80'
    : isMatrix
    ? 'border-emerald-950/80 bg-black'
    : isObsidian
    ? 'border-zinc-800/80 bg-[#16161a]'
    : 'border-slate-800/80 bg-slate-900/40';

  return (
    <aside
      className={`shrink-0 h-full flex flex-col border-r select-none transition-all duration-200 ${sidebarBg} ${
        sidebarCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Navigation Section with Independent Scrollbar */}
      <div className={`flex-1 overflow-y-auto min-h-0 ${sidebarCollapsed ? 'px-1.5 py-2.5' : 'p-3'}`}>
        {!sidebarCollapsed && (
          <div className={`px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest ${
            isLight ? 'text-slate-400' : isMatrix ? 'text-emerald-700' : isObsidian ? 'text-zinc-500' : 'text-slate-500'
          }`}>
            Navigation
          </div>
        )}
        <div className="mt-1 space-y-0.5">
          {mainNavigation.map(item => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                title={sidebarCollapsed ? `${item.label}${item.badge ? ` (${item.badge})` : ''}` : undefined}
                className={`w-full flex items-center ${
                  sidebarCollapsed ? 'justify-center px-0 py-2' : 'justify-between px-3 py-1.5'
                } text-xs font-semibold rounded-lg transition-all cursor-pointer relative group ${
                  isActive ? activeItemStyle : inactiveItemStyle
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <Icon className={`h-4 w-4 shrink-0 ${
                    isActive 
                      ? (isLight ? 'text-blue-600' : isMatrix ? 'text-emerald-400' : isObsidian ? 'text-purple-400' : 'text-cyan-400')
                      : (isLight ? 'text-slate-400' : isMatrix ? 'text-emerald-700' : isObsidian ? 'text-zinc-500' : 'text-slate-400')
                  }`} />
                  {!sidebarCollapsed && (
                    <span className="truncate whitespace-nowrap">{item.label}</span>
                  )}
                </div>

                {!sidebarCollapsed && item.badge !== undefined && (
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-mono border font-medium whitespace-nowrap shrink-0 ${item.badgeColor}`}>
                    {item.badge}
                  </span>
                )}

                {/* Collapsed Badge Dot Indicator */}
                {sidebarCollapsed && item.badge !== undefined && (
                  <span className={`absolute top-1 right-1 h-2 w-2 rounded-full ring-2 ${
                    isLight ? 'bg-blue-500 ring-white' : isMatrix ? 'bg-emerald-400 ring-black' : isObsidian ? 'bg-purple-400 ring-[#121214]' : 'bg-cyan-400 ring-[#090b10]'
                  }`} />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Cluster Pinned Footer: Always Locked at the Bottom */}
      <div className={`shrink-0 mt-auto border-t ${footerBg} ${sidebarCollapsed ? 'p-2' : 'px-3 py-2.5'}`}>
        {!sidebarCollapsed ? (
          <div className="flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-2">
              <UmbrellaCoreIcon className={`h-3.5 w-3.5 ${isLight ? 'text-blue-600' : isMatrix ? 'text-emerald-400' : isObsidian ? 'text-purple-400' : 'text-cyan-400'}`} />
              <div className="flex flex-col">
                <span className={`font-semibold leading-tight ${isLight ? 'text-slate-800' : isMatrix ? 'text-emerald-300' : isObsidian ? 'text-zinc-200' : 'text-slate-200'}`}>Umbrella Core</span>
                <span className="text-[9px] font-mono text-slate-500">v2.5.0 • Bridge Active</span>
              </div>
            </div>
            <button
              onClick={toggleSidebar}
              className={`p-1 rounded transition-colors cursor-pointer ${
                isLight ? 'text-slate-400 hover:text-slate-700 hover:bg-slate-200' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'
              }`}
              title="Collapse Sidebar"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <div className="flex justify-center">
            <button
              onClick={toggleSidebar}
              className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                isLight ? 'text-slate-500 hover:text-blue-600 hover:bg-slate-200' : isMatrix ? 'text-emerald-500 hover:text-emerald-300 hover:bg-emerald-950/60' : 'text-slate-500 hover:text-cyan-400 hover:bg-slate-800'
              }`}
              title="Expand Sidebar"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </aside>
  );
};
