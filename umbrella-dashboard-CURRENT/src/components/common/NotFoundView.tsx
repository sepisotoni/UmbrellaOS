import React from 'react';
import { useDashboard, NavigationTab } from '../../context/DashboardContext';
import {
  Compass,
  ArrowLeft,
  LayoutDashboard,
  Server,
  Users,
  ShieldAlert,
  Bot,
  Settings,
  HelpCircle,
  Radio,
} from 'lucide-react';
import { BrandLogo } from './BrandLogos';

interface NotFoundViewProps {
  attemptedTab?: string;
}

export const NotFoundView: React.FC<NotFoundViewProps> = ({ attemptedTab }) => {
  const { setActiveTab } = useDashboard();

  const quickLinks: Array<{
    tab: NavigationTab;
    label: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
  }> = [
    {
      tab: 'overview',
      label: 'Network Overview',
      description: 'Fleet metrics, player spikes, and node status',
      icon: LayoutDashboard,
    },
    {
      tab: 'discord',
      label: 'Discord Server Hub',
      description: 'Bot telemetry, webhook relays, and role sync',
      icon: Bot,
    },
    {
      tab: 'servers',
      label: 'Minecraft Servers',
      description: 'Velocity proxy, paper nodes, and live TPS',
      icon: Server,
    },
    {
      tab: 'players',
      label: 'Player Directory',
      description: 'UUID lookups, playtime records, and risk triage',
      icon: Users,
    },
    {
      tab: 'moderation',
      label: 'Moderation Center',
      description: 'Active bans, mutes, and GrimAC detections',
      icon: ShieldAlert,
    },
    {
      tab: 'settings',
      label: 'System Settings',
      description: 'Core gateway, AI model, and brand wallpaper',
      icon: Settings,
    },
  ];

  return (
    <div
      id="umbrella-404-page"
      className="min-h-[80vh] flex flex-col items-center justify-center p-6 text-center select-none"
    >
      <div className="w-full max-w-2xl space-y-6">
        {/* Animated Radar / Signal Lost Icon */}
        <div className="flex justify-center items-center">
          <div className="relative">
            <div className="absolute -inset-4 rounded-full bg-indigo-500/20 blur-xl animate-pulse" />
            <div className="relative h-24 w-24 rounded-3xl border border-indigo-500/40 bg-[#060b1c]/90 backdrop-blur-xl flex items-center justify-center shadow-[0_0_30px_rgba(99,102,241,0.25)]">
              <Compass className="h-12 w-12 text-indigo-400 animate-spin [animation-duration:12s]" />
              <div className="absolute top-2 right-2 h-3 w-3 rounded-full bg-rose-500 animate-ping" />
              <div className="absolute top-2 right-2 h-3 w-3 rounded-full bg-rose-500" />
            </div>
          </div>
        </div>

        {/* 404 Headline */}
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-950/40 text-[11px] font-mono text-indigo-300">
            <Radio className="h-3 w-3 animate-pulse text-rose-400" />
            <span>HTTP 404 • SIGNAL LOST IN NETWORK MESH</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight font-sans">
            Coordinate Not Found
          </h1>

          <p className="text-sm text-slate-400 max-w-md mx-auto leading-relaxed font-sans">
            The target module coordinate{' '}
            {attemptedTab && (
              <span className="font-mono text-rose-300 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800/40">
                "{attemptedTab}"
              </span>
            )}{' '}
            does not exist in the UmbrellaOS hypervisor routing table.
          </p>
        </div>

        {/* Primary Action Button */}
        <div className="flex justify-center gap-3 pt-2">
          <button
            onClick={() => setActiveTab('overview')}
            className="inline-flex items-center gap-2 rounded-xl border border-indigo-500/50 bg-indigo-600 hover:bg-indigo-500 px-6 py-2.5 text-xs font-bold text-white transition shadow-[0_0_20px_rgba(99,102,241,0.35)] cursor-pointer"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Return to Network Overview</span>
          </button>
        </div>

        {/* Suggested Quick Jump Modules */}
        <div className="pt-6 border-t border-[#141d3d]/70 text-left">
          <div className="text-xs font-mono text-slate-400 uppercase tracking-wider mb-3 flex items-center justify-between">
            <span>AVAILABLE ACTIVE SYSTEM MODULES:</span>
            <span className="text-[10px] text-indigo-400 font-normal">Select a route below</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {quickLinks.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.tab}
                  onClick={() => setActiveTab(item.tab)}
                  className="flex items-start gap-3 p-3 rounded-xl border border-[#141d3d] bg-[#060b1c]/80 hover:bg-[#0c1433] hover:border-indigo-500/50 text-left transition group cursor-pointer"
                >
                  <div className="p-2 rounded-lg bg-[#02040a] border border-[#141d3d] group-hover:border-indigo-500/40 shrink-0 text-slate-400 group-hover:text-indigo-300 transition">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="font-bold text-xs text-white group-hover:text-indigo-200 truncate">
                      {item.label}
                    </div>
                    <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                      {item.description}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
