import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { UmbrellaLogo } from '../common/UmbrellaLogo';
import { ProfileModal } from '../auth/ProfileModal';
import {
  Megaphone,
  Radio,
  Search,
  Zap,
  Activity,
  Sparkles,
} from 'lucide-react';

interface HeaderProps {
  onOpenBroadcastModal?: () => void;
  onOpenCommandPalette?: () => void;
  onOpenBrandModal?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenBroadcastModal,
  onOpenCommandPalette,
  onOpenBrandModal,
}) => {
  const {
    isDisconnected,
    healthInfo,
    currentUser,
    setActiveTab,
  } = useDashboard();

  const [isProfileOpen, setIsProfileOpen] = useState(false);

  return (
    <header
      id="umbrella-header"
      className="shrink-0 z-30 flex h-14 w-full items-center justify-between border-b px-4 backdrop-blur-md bg-[#02040a]/95 border-[#141d3d] text-slate-100 transition-colors"
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
        {onOpenBrandModal && (
          <button
            id="header-brand-logos-button"
            onClick={onOpenBrandModal}
            className="hidden md:inline-flex items-center gap-1.5 rounded-lg border border-[#141d3d] bg-[#060b1c] hover:bg-[#0a122e] hover:border-indigo-500/50 px-3 py-1.5 text-xs text-indigo-300 transition cursor-pointer"
            title="View Umbrella OS, Core, Bot, and Dashboard Logos & Wallpaper"
          >
            <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
            <span>Suite Logos</span>
          </button>
        )}

        {onOpenBroadcastModal && (
          <button
            id="header-broadcast-button"
            onClick={onOpenBroadcastModal}
            className="hidden sm:inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/40 bg-indigo-950/60 px-3 py-1.5 text-xs font-semibold text-indigo-200 hover:bg-indigo-900/70 transition cursor-pointer"
          >
            <Megaphone className="h-3.5 w-3.5 text-indigo-400" />
            <span>Broadcast</span>
          </button>
        )}

        {onOpenCommandPalette && (
          <button
            id="header-search-button"
            onClick={onOpenCommandPalette}
            className="flex items-center gap-2 rounded-lg border border-[#141d3d] bg-[#060b1c] px-3 py-1.5 text-xs text-slate-400 hover:border-indigo-500/50 hover:text-slate-200 transition cursor-pointer"
          >
            <Search className="h-3.5 w-3.5 text-slate-400" />
            <span className="hidden md:inline">Quick Jump...</span>
            <kbd className="hidden md:inline-block font-mono text-[10px] bg-[#0c1433] text-indigo-300 px-1.5 py-0.5 rounded border border-[#1a2552]">
              ⌘K
            </kbd>
          </button>
        )}

        {/* User Pill / Status */}
        {currentUser ? (
          <div
            id="header-user-badge"
            className="flex items-center gap-2 rounded-lg border border-[#141d3d] bg-[#060b1c] px-3 py-1.5 text-xs cursor-pointer hover:border-indigo-500/40 transition"
            onClick={() => setIsProfileOpen(true)}
          >
            {currentUser.avatar_url ? (
              <img
                src={currentUser.avatar_url}
                alt={currentUser.username}
                className="h-5 w-5 rounded-full object-cover border border-indigo-400/50"
                onError={(e) => { (e.currentTarget as HTMLImageElement).src = `https://cdn.discordapp.com/embed/avatars/${Math.abs(parseInt(currentUser.discord_id, 10) || 0) % 5}.png`; }}
              />
            ) : (
              <div className="h-5 w-5 rounded-full bg-indigo-950/80 border border-indigo-400/50 flex items-center justify-center font-bold text-indigo-200 text-[10px]">
                {currentUser.username ? currentUser.username.charAt(0).toUpperCase() : 'U'}
              </div>
            )}
            <span className="font-medium text-slate-200">{currentUser.username}</span>
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-800/40">
              {currentUser.role || 'Staff'}
            </span>
          </div>
        ) : (
          <button
            id="header-login-button"
            onClick={() => setActiveTab('login')}
            className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/40 bg-indigo-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-indigo-500 transition cursor-pointer shadow-[0_0_10px_rgba(99,102,241,0.3)]"
          >
            <Zap className="h-3.5 w-3.5" />
            <span>Staff Sign In</span>
          </button>
        )}
      </div>

      <ProfileModal
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
      />
    </header>
  );
};
