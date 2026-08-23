import React from 'react';
import { useDashboard, NavigationTab } from '../../context/DashboardContext';
import {
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
  LogOut,
  ChevronLeft,
  ChevronRight,
  Bot,
} from 'lucide-react';
import { UmbrellaLogo } from '../common/UmbrellaLogo';

interface SidebarProps {
  onOpenBanModal?: () => void;
}

interface NavItem {
  id: NavigationTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeColor?: string;
}

export const Sidebar: React.FC<SidebarProps> = () => {
  const {
    activeTab,
    setActiveTab,
    sidebarCollapsed,
    toggleSidebar,
    logout,
    currentUser,
  } = useDashboard();

  const navigationItems: NavItem[] = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'discord', label: 'Discord Server', icon: Bot, badge: 'Hub', badgeColor: 'bg-[#5865F2]/20 text-[#818cf8] border-[#5865F2]/40' },
    { id: 'players', label: 'Players', icon: Users },
    { id: 'moderation', label: 'Moderation', icon: ShieldAlert },
    { id: 'appeals', label: 'Appeals', icon: Scale },
    { id: 'staff', label: 'Staff', icon: ShieldCheck },
    { id: 'verification', label: 'Verification', icon: UserCheck },
    { id: 'alts', label: 'Alt Detection', icon: UserX },
    { id: 'servers', label: 'Fleet / Servers', icon: Server },
    { id: 'console', label: 'Console', icon: Terminal },
    { id: 'plugins', label: 'Plugins', icon: Cpu },
    { id: 'ai-tasks', label: 'AI Tasks', icon: Brain },
    { id: 'audit', label: 'Audit Log', icon: ScrollText },
    { id: 'feature-flags', label: 'Feature Flags', icon: Flag },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside
      id="umbrella-sidebar"
      className={`shrink-0 h-full flex flex-col border-r select-none transition-all duration-200 bg-[#02040a]/65 backdrop-blur-2xl border-[#141d3d]/80 shadow-[4px_0_24px_rgba(0,0,0,0.45)] text-slate-300 relative z-20 ${
        sidebarCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Navigation Section */}
      <div className={`flex-1 overflow-y-auto min-h-0 ${sidebarCollapsed ? 'px-2 py-3' : 'p-3'}`}>
        {!sidebarCollapsed && (
          <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-indigo-400/90 font-mono">
            Navigation
          </div>
        )}
        <nav className="mt-1 space-y-0.5">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                id={`sidebar-nav-${item.id}`}
                onClick={() => setActiveTab(item.id)}
                title={sidebarCollapsed ? item.label : undefined}
                className={`w-full flex items-center ${
                  sidebarCollapsed ? 'justify-center px-0 py-2.5' : 'justify-between px-3 py-2'
                } text-xs font-medium rounded-lg transition-all cursor-pointer relative group ${
                  isActive
                    ? 'bg-[#13173d]/90 text-indigo-200 border border-indigo-500/50 shadow-[0_0_12px_rgba(99,102,241,0.25)] font-semibold'
                    : 'text-slate-400 hover:bg-[#080f26]/80 hover:text-slate-100 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Icon
                    className={`h-4 w-4 shrink-0 ${
                      isActive ? 'text-[#818cf8]' : 'text-slate-400 group-hover:text-indigo-300'
                    }`}
                  />
                  {!sidebarCollapsed && (
                    <span className="truncate">{item.label}</span>
                  )}
                </div>

                {!sidebarCollapsed && item.badge && (
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-mono border ${
                      item.badgeColor || 'bg-indigo-950/60 text-indigo-300 border-indigo-700/40'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* User Info & Toggle Section */}
      <div className="shrink-0 border-t border-[#141d3d]/80 bg-[#05091a]/70 p-3">
        {!sidebarCollapsed && currentUser && (
          <div className="mb-2.5 flex items-center justify-between px-1">
            <div className="flex items-center gap-2 min-w-0">
              <div className="h-7 w-7 rounded-full bg-indigo-950/90 border border-indigo-500/40 flex items-center justify-center font-bold text-indigo-300 text-xs shrink-0">
                {currentUser.username ? currentUser.username.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="min-w-0">
                <div className="text-xs font-semibold text-slate-100 truncate">
                  {currentUser.username}
                </div>
                <div className="text-[10px] text-indigo-400/90 uppercase font-mono truncate">
                  {currentUser.role || 'Staff'}
                </div>
              </div>
            </div>

            <button
              id="sidebar-logout-button"
              onClick={logout}
              title="Sign Out"
              className="h-7 w-7 rounded-md hover:bg-rose-950/40 hover:text-rose-300 text-slate-400 border border-transparent hover:border-rose-800/40 flex items-center justify-center transition cursor-pointer"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        <button
          id="sidebar-toggle-button"
          onClick={toggleSidebar}
          className="w-full flex items-center justify-center gap-2 py-1.5 rounded-md hover:bg-[#0a122e] text-slate-400 hover:text-indigo-300 text-xs transition border border-[#141d3d] cursor-pointer"
          title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" />
              <span className="text-[11px] font-mono">Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
};
