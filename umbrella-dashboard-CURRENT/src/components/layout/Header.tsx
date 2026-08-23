import React from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { UmbrellaLogo } from '../common/UmbrellaLogo';
import {
  Megaphone,
  Radio,
  Search,
  Zap,
  Activity,
} from 'lucide-react';

interface HeaderProps {
  onOpenBroadcastModal?: () => void;
  onOpenCommandPalette?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenBroadcastModal, onOpenCommandPalette }) => {
  const {
    isDisconnected,
    healthInfo,
    currentUser,
    setActiveTab,
  } = useDashboard();

  return (
    <header
      id="umbrella-header"
      className="shrink-0 z-30 flex h-14 w-full items-center justify-between border-b px-4 backdrop-blur-md bg-[#070914]/95 border-[#1e1b4b] text-slate-100 transition-colors"
    >
      {/* Brand Wordmark & Health Indicator */}
      <div className="flex items-center gap-4">
        <UmbrellaLogo size="sm" />

        <div
          className={`flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs ${
            isDisconnected
              ? 'border-rose-500/40 bg-rose-950/40 text-rose-300 font-mono'
              : 'border-emerald-500/30 bg-emerald-950/30 text-emerald-300 font-mono'
          }`}
        >
          <span
            className={`h-2 w-2 rounded-full ${
              isDisconnected ? 'bg-rose-500 animate-ping' : 'bg-emerald-400 animate-pulse'
            }`}
          />
          <span className="font-semibold">{isDisconnected ? 'CORE DISCONNECTED' : 'CORE CONNECTED'}</span>
          {healthInfo?.version && (
            <>
              <span className="opacity-40">•</span>
              <span className="opacity-80">v{healthInfo.version}</span>
            </>
          )}
        </div>
      </div>

      {/* Center / Fast Actions */}
      <div className="flex items-center gap-3">
        {onOpenBroadcastModal && (
          <button
            id="header-broadcast-button"
            onClick={onOpenBroadcastModal}
            className="hidden sm:inline-flex items-center gap-1.5 rounded-lg border border-purple-500/30 bg-purple-950/40 px-3 py-1.5 text-xs font-semibold text-purple-200 hover:bg-purple-900/50 transition cursor-pointer"
          >
            <Megaphone className="h-3.5 w-3.5 text-purple-400" />
            <span>Broadcast</span>
          </button>
        )}

        {onOpenCommandPalette && (
          <button
            id="header-search-button"
            onClick={onOpenCommandPalette}
            className="flex items-center gap-2 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs text-slate-400 hover:border-purple-500/40 hover:text-slate-200 transition cursor-pointer"
          >
            <Search className="h-3.5 w-3.5 text-slate-400" />
            <span className="hidden md:inline">Quick Jump...</span>
            <kbd className="hidden md:inline-block font-mono text-[10px] bg-[#1a1f42] text-purple-300 px-1.5 py-0.5 rounded border border-[#2e356b]">
              ⌘K
            </kbd>
          </button>
        )}

        {/* User Pill / Status */}
        {currentUser ? (
          <div
            id="header-user-badge"
            className="flex items-center gap-2 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs cursor-pointer hover:border-purple-500/40"
            onClick={() => setActiveTab('settings')}
          >
            <div className="h-5 w-5 rounded-full bg-purple-900/80 border border-purple-400/50 flex items-center justify-center font-bold text-purple-200 text-[10px]">
              {currentUser.username ? currentUser.username.charAt(0).toUpperCase() : 'U'}
            </div>
            <span className="font-medium text-slate-200">{currentUser.username}</span>
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-purple-950/80 text-purple-300 border border-purple-800/40">
              {currentUser.role || 'Staff'}
            </span>
          </div>
        ) : (
          <button
            id="header-login-button"
            onClick={() => setActiveTab('login')}
            className="inline-flex items-center gap-1.5 rounded-lg border border-purple-500/40 bg-purple-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-purple-500 transition cursor-pointer shadow-[0_0_10px_rgba(168,85,247,0.3)]"
          >
            <Zap className="h-3.5 w-3.5" />
            <span>Staff Sign In</span>
          </button>
        )}
      </div>
    </header>
  );
};
