import React, { useState, useEffect } from 'react';
import { useDashboard, NavigationTab } from '../../context/DashboardContext';
import {
  Search,
  Server,
  User,
  ShieldAlert,
  Terminal,
  Package,
  History,
  Sliders,
  Sparkles,
  Radio,
  Clock,
  ExternalLink,
  RefreshCw,
  X
} from 'lucide-react';

export const CommandPalette: React.FC = () => {
  const {
    commandPaletteOpen,
    setCommandPaletteOpen,
    setActiveTab,
    servers,
    players,
    plugins,
    setSelectedServerId,
    restartServer,
    executeConsoleCommand
  } = useDashboard();

  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    if (commandPaletteOpen) {
      setQuery('');
      setSelectedIndex(0);
    }
  }, [commandPaletteOpen]);

  if (!commandPaletteOpen) return null;

  // Build searchable items
  interface PaletteItem {
    id: string;
    category: string;
    title: string;
    subtitle: string;
    icon: React.ComponentType<{ className?: string }>;
    action: () => void;
  }

  const items: PaletteItem[] = [
    // Navigation items
    { id: 'nav-overview', category: 'Navigation', title: 'Network Pulse & Executive Overview', subtitle: 'View real-time cluster health and live radar', icon: Radio, action: () => { setActiveTab('overview'); setCommandPaletteOpen(false); } },
    { id: 'nav-players', category: 'Navigation', title: 'Player Analytics & Sessions', subtitle: 'Inspect active player sessions, playtime and alt accounts', icon: User, action: () => { setActiveTab('players'); setCommandPaletteOpen(false); } },
    { id: 'nav-topology', category: 'Navigation', title: 'Network Topology & Infrastructure Matrix', subtitle: 'Inspect server nodes, latency ping map, and plugin heartbeat status', icon: Radio, action: () => { setActiveTab('topology'); setCommandPaletteOpen(false); } },
    { id: 'nav-console', category: 'Navigation', title: 'Live Server Terminals', subtitle: 'Multi-node ANSI log streamer and command prompt', icon: Terminal, action: () => { setActiveTab('console'); setCommandPaletteOpen(false); } },
    { id: 'nav-moderation', category: 'Navigation', title: 'Security, Bans & GrimAC Threat Center', subtitle: 'Active bans, GrimAC predictive flags, alt detection graph', icon: ShieldAlert, action: () => { setActiveTab('moderation'); setCommandPaletteOpen(false); } },
    { id: 'nav-ai', category: 'Navigation', title: 'AI Operational Intelligence & Copilot', subtitle: 'Automated crash diagnostics, post-mortems and NL query', icon: Sparkles, action: () => { setActiveTab('ai-intelligence'); setCommandPaletteOpen(false); } },
    { id: 'nav-plugins', category: 'Navigation', title: 'Plugin Marketplace & Sandboxes', subtitle: 'Connected plugin heartbeats and telemetry', icon: Package, action: () => { setActiveTab('plugins'); setCommandPaletteOpen(false); } },
    { id: 'nav-discord', category: 'Navigation', title: 'Discord Integration & Cloud SRV Hub', subtitle: 'Live in-game chat bridge, embed builder, slash commands, webhook router', icon: Radio, action: () => { setActiveTab('discord'); setCommandPaletteOpen(false); } },
    { id: 'nav-snapshots', category: 'Navigation', title: 'Time-Travel Snapshots & World Rollbacks', subtitle: 'Delta snapshot checkpoints and item history scrubber', icon: History, action: () => { setActiveTab('snapshots'); setCommandPaletteOpen(false); } },
    { id: 'nav-staff', category: 'Navigation', title: 'Staff Directory & Roles (RBAC)', subtitle: 'Manage staff Discord identities and permissions', icon: Sliders, action: () => { setActiveTab('staff'); setCommandPaletteOpen(false); } },
    { id: 'nav-audit', category: 'Navigation', title: 'Audit & Centralized Logs', subtitle: 'Real-time trace logs and operational audit events', icon: Terminal, action: () => { setActiveTab('audit'); setCommandPaletteOpen(false); } },
    { id: 'nav-verification', category: 'Navigation', title: 'Account Verification Pairs', subtitle: 'Discord <-> Minecraft account linkages', icon: User, action: () => { setActiveTab('verification'); setCommandPaletteOpen(false); } },
    { id: 'nav-translation', category: 'Navigation', title: 'Translation & Localization', subtitle: 'Multi-lingual MiniMessage chat and broadcast mapping', icon: Sparkles, action: () => { setActiveTab('translation'); setCommandPaletteOpen(false); } },
    { id: 'nav-automation', category: 'Navigation', title: 'Automations & Cron Task Schedules', subtitle: 'Auto-backups, GC sweeps, and self-healing watchdog', icon: Clock, action: () => { setActiveTab('automation'); setCommandPaletteOpen(false); } },
    { id: 'nav-api', category: 'Navigation', title: 'API Hub & Webhooks', subtitle: 'OpenAPI tester, scoped keys and webhook subscriptions', icon: Sliders, action: () => { setActiveTab('api-hub'); setCommandPaletteOpen(false); } },
    { id: 'nav-settings', category: 'Navigation', title: 'Feature Flags & System Settings', subtitle: 'Real-time toggles, rollout percentages, Discord bots', icon: Sliders, action: () => { setActiveTab('settings'); setCommandPaletteOpen(false); } },

    // Servers
    ...servers.map(s => ({
      id: `server-${s.id}`,
      category: 'Server Instances',
      title: s.name,
      subtitle: `${s.type} • ${s.playersCount} players • ${s.tps} TPS • ${s.host}:${s.port}`,
      icon: Server,
      action: () => {
        setSelectedServerId(s.id);
        setActiveTab('console');
        setCommandPaletteOpen(false);
      }
    })),

    // Players
    ...players.map(p => ({
      id: `player-${p.username}`,
      category: 'Players Online',
      title: `${p.username} (${p.rank})`,
      subtitle: `${p.currentServer || 'Offline'} • Ping: ${p.pingMs}ms • Suspicion: ${p.suspicionScore}% • Client: ${p.clientBrand}`,
      icon: User,
      action: () => {
        setActiveTab('players');
        setCommandPaletteOpen(false);
      }
    })),

    // Quick Command Actions
    {
      id: 'act-restart-anarchy',
      category: 'Quick Commands',
      title: 'Graceful Reboot: Selected Instance',
      subtitle: 'Triggers chunk save, unregisters proxy route, and restarts process',
      icon: RefreshCw,
      action: () => {
        if (servers[0]) restartServer(servers[0].id);
        setCommandPaletteOpen(false);
      }
    },
    {
      id: 'act-tps-all',
      category: 'Quick Commands',
      title: 'Run /tps on Active Console',
      subtitle: 'Query tick timings across Paper Watchdog threads',
      icon: Terminal,
      action: () => {
        if (servers[0]) executeConsoleCommand(servers[0].id, '/tps');
        setActiveTab('console');
        setCommandPaletteOpen(false);
      }
    }
  ];

  const filteredItems = items.filter(item => {
    const term = query.toLowerCase();
    return (
      item.title.toLowerCase().includes(term) ||
      item.subtitle.toLowerCase().includes(term) ||
      item.category.toLowerCase().includes(term)
    );
  });

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev + 1) % (filteredItems.length || 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev - 1 + filteredItems.length) % (filteredItems.length || 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        filteredItems[selectedIndex].action();
      }
    } else if (e.key === 'Escape') {
      setCommandPaletteOpen(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/75 backdrop-blur-sm pt-[12vh] p-4">
      <div className="w-full max-w-2xl rounded-xl border border-slate-700 bg-[#0f131a] shadow-2xl overflow-hidden flex flex-col max-h-[70vh]">
        {/* Search Input Box */}
        <div className="flex items-center border-b border-slate-800 px-4 py-3 bg-slate-900/90">
          <Search className="h-4 w-4 text-cyan-400 shrink-0 mr-3" />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search nodes, servers, players, GrimAC flags, plugins, commands (e.g. /ban, survival)..."
            autoFocus
            className="w-full bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none"
          />
          <button
            onClick={() => setCommandPaletteOpen(false)}
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filteredItems.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500 font-mono">
              No results found for "<span className="text-slate-300">{query}</span>".
            </div>
          ) : (
            filteredItems.map((item, idx) => {
              const Icon = item.icon;
              const isSelected = idx === selectedIndex;
              return (
                <button
                  key={item.id}
                  onClick={item.action}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`w-full flex items-center justify-between p-2.5 rounded-lg text-left transition-colors ${
                    isSelected ? 'bg-cyan-950/50 border border-cyan-500/40 text-white' : 'text-slate-300 hover:bg-slate-900/50 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`p-1.5 rounded-md ${isSelected ? 'bg-cyan-900/60 text-cyan-300' : 'bg-slate-800 text-slate-400'}`}>
                      <Icon className="h-4 w-4 shrink-0" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-semibold truncate flex items-center gap-2">
                        <span>{item.title}</span>
                      </div>
                      <div className="text-[11px] text-slate-400 truncate mt-0.5 font-mono">
                        {item.subtitle}
                      </div>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 bg-slate-800/80 px-2 py-0.5 rounded ml-2 shrink-0">
                    {item.category}
                  </span>
                </button>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="flex items-center justify-between border-t border-slate-800 bg-slate-950/80 px-4 py-2 text-[10px] text-slate-500 font-mono">
          <div className="flex items-center gap-3">
            <span><kbd className="text-slate-400">↑↓</kbd> Navigate</span>
            <span><kbd className="text-slate-400">Enter</kbd> Select</span>
            <span><kbd className="text-slate-400">Esc</kbd> Close</span>
          </div>
          <span>UmbrellaOS Omni-Search</span>
        </div>
      </div>
    </div>
  );
};
