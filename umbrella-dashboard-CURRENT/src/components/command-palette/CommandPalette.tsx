import React, { useState, useEffect } from 'react';
import { useDashboard, NavigationTab } from '../../context/DashboardContext';
import {
  Search,
  LayoutDashboard,
  Users,
  ShieldAlert,
  Scale,
  ShieldCheck,
  UserCheck,
  UserX,
  Server,
  Terminal,
  Cpu,
  Brain,
  ScrollText,
  Flag,
  Settings,
  Ban,
  X,
} from 'lucide-react';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenBanModal?: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onOpenBanModal,
}) => {
  const { setActiveTab } = useDashboard();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  interface PaletteItem {
    id: string;
    category: string;
    title: string;
    subtitle: string;
    icon: React.ComponentType<{ className?: string }>;
    action: () => void;
  }

  const items: PaletteItem[] = [
    {
      id: 'nav-overview',
      category: 'Navigation',
      title: 'Overview Dashboard',
      subtitle: 'Network status, players online, GrimAC flags, active appeals',
      icon: LayoutDashboard,
      action: () => {
        setActiveTab('overview');
        onClose();
      },
    },
    {
      id: 'nav-players',
      category: 'Navigation',
      title: 'Player Directory & Profiles',
      subtitle: 'Inspect playtime, joined history, punishments, and on-demand AI review',
      icon: Users,
      action: () => {
        setActiveTab('players');
        onClose();
      },
    },
    {
      id: 'nav-moderation',
      category: 'Navigation',
      title: 'Moderation & Anticheat Center',
      subtitle: 'Punishment management, GrimAC heuristics, issue new ban',
      icon: ShieldAlert,
      action: () => {
        setActiveTab('moderation');
        onClose();
      },
    },
    {
      id: 'nav-appeals',
      category: 'Navigation',
      title: 'Appeals Management',
      subtitle: 'Review player appeals with AI recommendation synthesis',
      icon: Scale,
      action: () => {
        setActiveTab('appeals');
        onClose();
      },
    },
    {
      id: 'nav-staff',
      category: 'Navigation',
      title: 'Staff Roster & Permissions',
      subtitle: 'Manage administrative staff appointments and Discord sync',
      icon: ShieldCheck,
      action: () => {
        setActiveTab('staff');
        onClose();
      },
    },
    {
      id: 'nav-verification',
      category: 'Navigation',
      title: 'Discord Verification',
      subtitle: 'Linked Minecraft & Discord player profiles and manual overrides',
      icon: UserCheck,
      action: () => {
        setActiveTab('verification');
        onClose();
      },
    },
    {
      id: 'nav-alts',
      category: 'Navigation',
      title: 'Alt Account Detection',
      subtitle: 'Ban evasion tracking, IP clusters, and false positive overrides',
      icon: UserX,
      action: () => {
        setActiveTab('alts');
        onClose();
      },
    },
    {
      id: 'nav-servers',
      category: 'Navigation',
      title: 'Minecraft Fleet & Servers',
      subtitle: 'Live TPS, online players, version telemetry, and health',
      icon: Server,
      action: () => {
        setActiveTab('servers');
        onClose();
      },
    },
    {
      id: 'nav-console',
      category: 'Navigation',
      title: 'Live Server Console',
      subtitle: 'Streaming terminal logs and interactive command execution',
      icon: Terminal,
      action: () => {
        setActiveTab('console');
        onClose();
      },
    },
    {
      id: 'nav-plugins',
      category: 'Navigation',
      title: 'Plugin Ecosystem & Heartbeats',
      subtitle: 'Status of UmbrellaOS bridge and GrimAC anticheat hooks',
      icon: Cpu,
      action: () => {
        setActiveTab('plugins');
        onClose();
      },
    },
    {
      id: 'nav-ai-tasks',
      category: 'Navigation',
      title: 'AI Operations & Tasks',
      subtitle: 'Task approvals, AI Copilot chat, and crash risk scoring',
      icon: Brain,
      action: () => {
        setActiveTab('ai-tasks');
        onClose();
      },
    },
    {
      id: 'nav-audit',
      category: 'Navigation',
      title: 'Security Audit Log',
      subtitle: 'Immutable log of staff actions and administrative events',
      icon: ScrollText,
      action: () => {
        setActiveTab('audit');
        onClose();
      },
    },
    {
      id: 'nav-feature-flags',
      category: 'Navigation',
      title: 'Feature Flags',
      subtitle: 'Toggle network features and manage staged rollouts',
      icon: Flag,
      action: () => {
        setActiveTab('feature-flags');
        onClose();
      },
    },
    {
      id: 'nav-settings',
      category: 'Navigation',
      title: 'System Settings',
      subtitle: 'Core connection, Discord bot, templates, and Gemini AI config',
      icon: Settings,
      action: () => {
        setActiveTab('settings');
        onClose();
      },
    },
    {
      id: 'act-issue-punishment',
      category: 'Quick Actions',
      title: 'Issue Network Punishment',
      subtitle: 'Open the punishment modal to ban, kick, or mute a player',
      icon: Ban,
      action: () => {
        onClose();
        if (onOpenBanModal) onOpenBanModal();
      },
    },
  ];

  const filteredItems = items.filter(
    (item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      item.subtitle.toLowerCase().includes(query.toLowerCase()) ||
      item.category.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-2xl border border-[#1e1b4b] bg-[#0d1127] shadow-2xl overflow-hidden font-mono text-xs">
        {/* Search Header */}
        <div className="flex items-center gap-3 border-b border-[#1e1b4b] px-4 py-3.5 bg-[#070914]">
          <Search className="h-4 w-4 text-purple-400 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="Type a command or jump to page..."
            autoFocus
            className="w-full bg-transparent text-white placeholder-slate-500 focus:outline-none text-xs"
          />
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-[380px] overflow-y-auto p-2 space-y-1">
          {filteredItems.length === 0 ? (
            <div className="py-8 text-center text-slate-500">No matching commands or pages.</div>
          ) : (
            filteredItems.map((item, index) => {
              const Icon = item.icon;
              const isSelected = index === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={item.action}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`flex items-center justify-between rounded-xl px-3.5 py-2.5 cursor-pointer transition ${
                    isSelected
                      ? 'bg-purple-950/80 border border-purple-500/40 text-white'
                      : 'text-slate-300 hover:bg-[#121638]'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Icon className="h-4 w-4 text-purple-400 shrink-0" />
                    <div className="min-w-0">
                      <div className="font-semibold text-white truncate">{item.title}</div>
                      <div className="text-[11px] text-slate-400 font-sans truncate">
                        {item.subtitle}
                      </div>
                    </div>
                  </div>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#070914] text-purple-300 border border-[#1e1b4b]">
                    {item.category}
                  </span>
                </div>
              );
            })
          )}
        </div>

        <div className="border-t border-[#1e1b4b] px-4 py-2 bg-[#070914] text-[10px] text-slate-500 flex justify-between">
          <span>Navigate with mouse or arrow keys</span>
          <span>Press ESC to close</span>
        </div>
      </div>
    </div>
  );
};
