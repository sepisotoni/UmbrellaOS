import React, { useState } from 'react';
import { DashboardProvider, useDashboard } from './context/DashboardContext';
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
import { SettingsView } from './components/settings/SettingsView';
import { LoginView } from './components/auth/LoginView';
import { AccessDeniedView } from './components/auth/AccessDeniedView';
import { PunishModal } from './components/modals/PunishModal';
import { BroadcastModal } from './components/modals/BroadcastModal';
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';

const DashboardContent: React.FC = () => {
  const { activeTab, toasts, removeToast, currentUser } = useDashboard();
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isPunishModalOpen, setIsPunishModalOpen] = useState(false);
  const [isBroadcastModalOpen, setIsBroadcastModalOpen] = useState(false);
  const [punishTargetPlayer, setPunishTargetPlayer] = useState<string>('');

  const handleOpenBanModalWithTarget = (player: string) => {
    setPunishTargetPlayer(player);
    setIsPunishModalOpen(true);
  };

  // Insufficient permissions gate
  const DENIED_ROLES = ['viewer'];
  if (activeTab !== 'login' && currentUser && DENIED_ROLES.includes(currentUser.role)) {
    return (
      <div className="h-screen w-screen overflow-y-auto font-sans bg-[#070914] text-slate-100">
        <AccessDeniedView />
      </div>
    );
  }

  if (activeTab === 'login') {
    return (
      <div className="h-screen w-screen overflow-y-auto font-sans bg-[#070914] text-slate-100">
        <LoginView />

        {/* Toast Notification Container */}
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-md pointer-events-none">
          {(toasts || []).map((toast) => (
            <div
              key={toast.id}
              className={`pointer-events-auto rounded-xl border p-4 shadow-xl backdrop-blur-md flex items-start gap-3 transition-all font-mono text-xs ${
                toast.type === 'success'
                  ? 'bg-[#0b1812]/95 border-emerald-500/40 text-emerald-300'
                  : toast.type === 'error'
                  ? 'bg-[#180b0f]/95 border-rose-500/40 text-rose-300'
                  : toast.type === 'warning'
                  ? 'bg-[#18130b]/95 border-amber-500/40 text-amber-300'
                  : 'bg-[#0b1318]/95 border-purple-500/40 text-purple-300'
              }`}
            >
              <div className="mt-0.5 shrink-0">
                {toast.type === 'success' && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
                {toast.type === 'error' && <AlertTriangle className="h-4 w-4 text-rose-400" />}
                {toast.type === 'warning' && <AlertTriangle className="h-4 w-4 text-amber-400" />}
                {toast.type === 'info' && <Info className="h-4 w-4 text-purple-400" />}
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

  return (
    <div className="h-screen max-h-screen w-screen flex flex-col overflow-hidden font-sans bg-[#070914] text-slate-100 selection:bg-purple-500/30 selection:text-purple-200">
      {/* Global Navigation Header (Fixed at top) */}
      <Header
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        onOpenBroadcastModal={() => setIsBroadcastModalOpen(true)}
      />

      {/* Main Body with Locked Sidebar and Independently Scrollable Workspace */}
      <div className="flex-1 flex flex-row overflow-hidden min-h-0 w-full">
        {/* Left Sidebar */}
        <Sidebar onOpenBanModal={() => handleOpenBanModalWithTarget('')} />

        {/* Dynamic Main Workspace Container */}
        <main className="flex-1 overflow-y-auto min-h-0 px-4 py-6 md:px-8 max-w-7xl mx-auto w-full bg-[#070914]">
          {activeTab === 'overview' && (
            <OverviewView
              onOpenBanModal={() => handleOpenBanModalWithTarget('')}
              onOpenBroadcastModal={() => setIsBroadcastModalOpen(true)}
            />
          )}
          {activeTab === 'players' && (
            <PlayersView onOpenBanModal={() => handleOpenBanModalWithTarget('')} />
          )}
          {activeTab === 'moderation' && (
            <ModerationView onOpenBanModal={() => handleOpenBanModalWithTarget('')} />
          )}
          {activeTab === 'appeals' && <AppealsView />}
          {activeTab === 'staff' && <StaffView />}
          {activeTab === 'verification' && <VerificationView />}
          {activeTab === 'alts' && <AltDetectionView />}
          {activeTab === 'servers' && <ServersView />}
          {activeTab === 'console' && <ConsoleView />}
          {activeTab === 'plugins' && <PluginsView />}
          {activeTab === 'ai-tasks' && <AITasksView />}
          {activeTab === 'audit' && <AuditView />}
          {activeTab === 'feature-flags' && <FeatureFlagsView />}
          {activeTab === 'settings' && <SettingsView />}
        </main>
      </div>

      {/* Global Command Palette Triggered via Cmd+K or Header */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onOpenBanModal={() => handleOpenBanModalWithTarget('')}
      />

      {/* Ban / Punishment Modal */}
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

      {/* Toast Notification Container */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-md pointer-events-none">
        {(toasts || []).map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto rounded-xl border p-4 shadow-xl backdrop-blur-md flex items-start gap-3 transition-all font-mono text-xs ${
              toast.type === 'success'
                ? 'bg-[#0b1812]/95 border-emerald-500/40 text-emerald-300'
                : toast.type === 'error'
                ? 'bg-[#180b0f]/95 border-rose-500/40 text-rose-300'
                : toast.type === 'warning'
                ? 'bg-[#18130b]/95 border-amber-500/40 text-amber-300'
                : 'bg-[#0b1318]/95 border-purple-500/40 text-purple-300'
            }`}
          >
            <div className="mt-0.5 shrink-0">
              {toast.type === 'success' && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
              {toast.type === 'error' && <AlertTriangle className="h-4 w-4 text-rose-400" />}
              {toast.type === 'warning' && <AlertTriangle className="h-4 w-4 text-amber-400" />}
              {toast.type === 'info' && <Info className="h-4 w-4 text-purple-400" />}
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
