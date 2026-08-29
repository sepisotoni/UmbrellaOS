import React, { useState, useEffect } from 'react';
import { DashboardProvider, useDashboard, NavigationTab } from './context/DashboardContext';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { CommandPalette } from './components/command-palette/CommandPalette';
import { OverviewView } from './components/overview/OverviewView';
import { PlayersView } from './components/players/PlayersView';
import { ModerationView } from './components/moderation/ModerationView';
import { AppealsView } from './components/appeals/AppealsView';
import { StaffView } from './components/staff/StaffView';
import { VerificationView } from './components/verification/VerificationView';
import { AltDetectionView } from './components/alts/AltDetectionView';
import { ServersView } from './components/servers/ServersView';
import { ConsoleView } from './components/console/ConsoleView';
import { PluginsView } from './components/plugins/PluginsView';
import { AITasksView } from './components/ai/AITasksView';
import { AuditView } from './components/audit/AuditView';
import { FeatureFlagsView } from './components/feature-flags/FeatureFlagsView';
import { KnowledgeView } from './components/knowledge/KnowledgeView';
import { SettingsView } from './components/settings/SettingsView';
import { DiscordView } from './components/discord/DiscordView';
import { LoginView } from './components/auth/LoginView';
import { AccessDeniedView } from './components/auth/AccessDeniedView';
import { NotFoundView } from './components/common/NotFoundView';
import { MFAChallengeModal } from './components/auth/MFAChallengeModal';
import { PunishModal } from './components/modals/PunishModal';
import { BroadcastModal } from './components/modals/BroadcastModal';
import { BrandShowcaseModal } from './components/common/BrandShowcaseModal';
import { AtmosphericBackground } from './components/common/AtmosphericBackground';
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';

const DashboardContent: React.FC = () => {
  const {
    activeTab,
    setActiveTab,
    toasts,
    removeToast,
    currentUser,
    sessionToken,
    adminKey,
    canAccessTab,
    showDoodles,
    setShowDoodles,
    doodleOpacity,
    setDoodleOpacity,
    selectedBrand,
    setSelectedBrand,
    sidebarCollapsed,
    toggleSidebar,
  } = useDashboard();

  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isPunishModalOpen, setIsPunishModalOpen] = useState(false);
  const [isBroadcastModalOpen, setIsBroadcastModalOpen] = useState(false);
  const [isBrandModalOpen, setIsBrandModalOpen] = useState(false);
  const [punishTargetPlayer, setPunishTargetPlayer] = useState<string>('');

  const isAuthenticated = Boolean(currentUser || sessionToken || (adminKey && adminKey.trim().length > 0));

  // If unauthenticated and not on the login page, redirect immediately to login
  useEffect(() => {
    if (!isAuthenticated && activeTab !== 'login') {
      setActiveTab('login');
    }
  }, [isAuthenticated, activeTab, setActiveTab]);

  const handleOpenBanModalWithTarget = (player: string) => {
    setPunishTargetPlayer(player);
    setIsPunishModalOpen(true);
  };

  // Render Login View when not authenticated or on login tab
  if (!isAuthenticated || activeTab === 'login') {
    return (
      <div className="h-screen w-screen overflow-y-auto font-sans bg-[#02040a] text-slate-100 relative">
        <AtmosphericBackground showDoodles={showDoodles} doodleOpacity={doodleOpacity} />
        <div className="relative z-10">
          <LoginView />
        </div>

        {/* Toast Notification Container */}
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-md pointer-events-none">
          {(toasts || []).map((toast) => (
            <div
              key={toast.id}
              className={`pointer-events-auto rounded-xl border p-4 shadow-xl backdrop-blur-md flex items-start gap-3 transition-all font-mono text-xs ${
                toast.type === 'success'
                  ? 'bg-[#05130e]/95 border-emerald-500/40 text-emerald-300'
                  : toast.type === 'error'
                  ? 'bg-[#15050a]/95 border-rose-500/40 text-rose-300'
                  : toast.type === 'warning'
                  ? 'bg-[#150f05]/95 border-amber-500/40 text-amber-300'
                  : 'bg-[#060b1c]/95 border-indigo-500/40 text-indigo-300'
              }`}
            >
              <div className="mt-0.5 shrink-0">
                {toast.type === 'success' && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
                {toast.type === 'error' && <AlertTriangle className="h-4 w-4 text-rose-400" />}
                {toast.type === 'warning' && <AlertTriangle className="h-4 w-4 text-amber-400" />}
                {toast.type === 'info' && <Info className="h-4 w-4 text-indigo-400" />}
              </div>

              <div className="flex-1 space-y-0.5">
                <div className="font-bold text-white text-xs">{toast.title}</div>
                <div className="text-[11px] text-slate-300 font-sans">{toast.message}</div>
              </div>

              <button
                onClick={() => removeToast(toast.id)}
                className="text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Permission Gate: If authenticated but lacks permission for requested section
  const hasAccess = canAccessTab(activeTab);
  const isAccessDenied = activeTab === 'access-denied' || !hasAccess;

  // Users with no role at all (null/member) — block the entire dashboard, no layout
  const userRole = (currentUser?.role || '').toLowerCase();
  const hasNoRole = currentUser && !adminKey && (!userRole || userRole === 'member');
  if (hasNoRole) {
    return (
      <div className="h-screen w-screen overflow-y-auto font-sans bg-[#02040a] text-slate-100 relative">
        <AtmosphericBackground showDoodles={showDoodles} doodleOpacity={doodleOpacity} />
        <div className="relative z-10 flex items-center justify-center min-h-screen">
          <AccessDeniedView attemptedTab="overview" noRole />
        </div>
      </div>
    );
  }

  // Per-tab access denied — also shown without layout (sidebar/topbar stripped)
  if (isAccessDenied) {
    return (
      <div className="h-screen w-screen overflow-y-auto font-sans bg-[#02040a] text-slate-100 relative">
        <AtmosphericBackground showDoodles={showDoodles} doodleOpacity={doodleOpacity} />
        <div className="relative z-10 flex items-center justify-center min-h-screen">
          <AccessDeniedView attemptedTab={activeTab} />
        </div>
      </div>
    );
  }

  const renderActiveView = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <OverviewView
            onOpenBanModal={() => handleOpenBanModalWithTarget('')}
            onOpenBroadcastModal={() => setIsBroadcastModalOpen(true)}
          />
        );
      case 'discord':
        return <DiscordView />;
      case 'players':
        return <PlayersView onOpenBanModal={() => handleOpenBanModalWithTarget('')} />;
      case 'moderation':
        return <ModerationView onOpenBanModal={() => handleOpenBanModalWithTarget('')} />;
      case 'appeals':
        return <AppealsView />;
      case 'staff':
        return <StaffView />;
      case 'verification':
        return <VerificationView />;
      case 'alts':
        return <AltDetectionView />;
      case 'servers':
        return <ServersView />;
      case 'console':
        return <ConsoleView />;
      case 'plugins':
        return <PluginsView />;
      case 'ai-tasks':
        return <AITasksView />;
      case 'audit':
        return <AuditView />;
      case 'knowledge':
        return <KnowledgeView />;
      case 'feature-flags':
        return <FeatureFlagsView />;
      case 'settings':
        return <SettingsView />;
      case '404':
        return <NotFoundView attemptedTab={activeTab} />;
      default:
        return <NotFoundView attemptedTab={activeTab} />;
    }
  };

  return (
    <div className="h-screen max-h-screen w-screen flex flex-col overflow-hidden font-sans bg-[#02040a] text-slate-100 selection:bg-indigo-500/30 selection:text-indigo-200 relative">
      {/* Global Atmospheric Background Wallpaper Layer (Spans entire app including sidebar) */}
      <AtmosphericBackground
        showDoodles={showDoodles}
        doodleOpacity={doodleOpacity}
        showStars={true}
        showHorizon={false}
      />

      {/* Global Navigation Header (Fixed at top) */}
      <div className="relative z-30">
        <Header
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
          onOpenBroadcastModal={() => setIsBroadcastModalOpen(true)}
          onOpenBrandModal={() => setIsBrandModalOpen(true)}
        />
      </div>

      {/* Main Body with Unified Backdrop Sidebar and Independently Scrollable Workspace */}
      <div className="flex-1 flex flex-row overflow-hidden min-h-0 w-full relative z-10">
        {/* Mobile sidebar overlay — tapping it collapses the sidebar */}
        <div
          className={`fixed inset-0 z-20 bg-black/60 md:hidden transition-opacity duration-200 ${
            !sidebarCollapsed ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
          }`}
          onClick={toggleSidebar}
          aria-hidden="true"
        />

        {/* Left Sidebar — fixed on mobile (slides in/out), static on desktop */}
        <div
          className={`md:relative fixed inset-y-0 left-0 z-30 transition-transform duration-200 ${
            sidebarCollapsed ? '-translate-x-full md:translate-x-0' : 'translate-x-0'
          }`}
        >
          <Sidebar onOpenBanModal={() => handleOpenBanModalWithTarget('')} />
        </div>

        {/* Dynamic Main Workspace Container */}
        <main className="flex-1 overflow-y-auto min-h-0 px-4 py-6 md:px-8 max-w-7xl mx-auto w-full">
          {renderActiveView()}
        </main>
      </div>

      {/* Global Command Palette Triggered via Cmd+K or Header */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onOpenBanModal={() => handleOpenBanModalWithTarget('')}
        onOpenBrandModal={() => setIsBrandModalOpen(true)}
      />

      {/* Ban / Punishment Modal */}
      <MFAChallengeModal />
      <PunishModal
        isOpen={isPunishModalOpen}
        onClose={() => setIsPunishModalOpen(false)}
        initialPlayerName={punishTargetPlayer}
      />

      {/* Broadcast Message Modal */}
      <BroadcastModal
        isOpen={isBroadcastModalOpen}
        onClose={() => setIsBroadcastModalOpen(false)}
      />

      {/* Brand Logos & Wallpaper Suite Modal */}
      <BrandShowcaseModal
        isOpen={isBrandModalOpen}
        onClose={() => setIsBrandModalOpen(false)}
        selectedBrand={selectedBrand}
        onSelectBrand={setSelectedBrand}
        doodleOpacity={doodleOpacity}
        onDoodleOpacityChange={setDoodleOpacity}
        showDoodles={showDoodles}
        onToggleDoodles={setShowDoodles}
      />

      {/* Toast Notification Container */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-md pointer-events-none">
        {(toasts || []).map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto rounded-xl border p-4 shadow-xl backdrop-blur-md flex items-start gap-3 transition-all font-mono text-xs ${
              toast.type === 'success'
                ? 'bg-[#05130e]/95 border-emerald-500/40 text-emerald-300'
                : toast.type === 'error'
                ? 'bg-[#15050a]/95 border-rose-500/40 text-rose-300'
                : toast.type === 'warning'
                ? 'bg-[#150f05]/95 border-amber-500/40 text-amber-300'
                : 'bg-[#060b1c]/95 border-indigo-500/40 text-indigo-300'
            }`}
          >
            <div className="mt-0.5 shrink-0">
              {toast.type === 'success' && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
              {toast.type === 'error' && <AlertTriangle className="h-4 w-4 text-rose-400" />}
              {toast.type === 'warning' && <AlertTriangle className="h-4 w-4 text-amber-400" />}
              {toast.type === 'info' && <Info className="h-4 w-4 text-indigo-400" />}
            </div>

            <div className="flex-1 space-y-0.5">
              <div className="font-bold text-white text-xs">{toast.title}</div>
              <div className="text-[11px] text-slate-300 font-sans">{toast.message}</div>
            </div>

            <button
              onClick={() => removeToast(toast.id)}
              className="text-slate-400 hover:text-white transition-colors cursor-pointer"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default function App() {
  return (
    <DashboardProvider>
      <DashboardContent />
    </DashboardProvider>
  );
}
