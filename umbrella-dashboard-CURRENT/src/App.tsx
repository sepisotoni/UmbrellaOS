import { useState } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { useHealthCheck } from './hooks/useHealthCheck'
import { LoginPage } from './components/pages/LoginPage'
import { OverviewPage } from './components/pages/OverviewPage'
import { PlayersPage } from './components/pages/PlayersPage'
import { ModerationPage } from './components/pages/ModerationPage'
import { AppealsPage } from './components/pages/AppealsPage'
import { StaffPage } from './components/pages/StaffPage'
import { VerificationPage } from './components/pages/VerificationPage'
import { AltDetectionPage } from './components/pages/AltDetectionPage'
import { ServersPage } from './components/pages/ServersPage'
import { ConsolePage } from './components/pages/ConsolePage'
import { PluginsPage } from './components/pages/PluginsPage'
import { AITasksPage } from './components/pages/AITasksPage'
import { AuditPage } from './components/pages/AuditPage'
import { FeatureFlagsPage } from './components/pages/FeatureFlagsPage'
import { SettingsPage } from './components/pages/SettingsPage'
import { Sidebar, Page } from './components/layout/Sidebar'
import { DisconnectedBanner } from './components/layout/DisconnectedBanner'
import { Spinner } from './components/ui'
import { PunishModal } from './components/modals/PunishModal'
import { BroadcastModal } from './components/modals/BroadcastModal'
import { Megaphone, ShieldAlert } from 'lucide-react'

function DashboardApp() {
  const { token, loading: authLoading } = useAuth()
  const { status } = useHealthCheck(30_000)
  const [page, setPage] = useState<Page>('overview')

  const [punishOpen, setPunishOpen] = useState(false)
  const [punishUsername, setPunishUsername] = useState<string | null>(null)
  const [broadcastOpen, setBroadcastOpen] = useState(false)

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#070914] flex items-center justify-center">
        <Spinner className="h-8 w-8 text-violet-400" />
      </div>
    )
  }

  if (!token) {
    return <LoginPage onLogin={() => setPage('overview')} />
  }

  const openPunish = (username?: string) => {
    setPunishUsername(username ?? null)
    setPunishOpen(true)
  }

  const renderPage = () => {
    switch (page) {
      case 'overview': return <OverviewPage />
      case 'players': return <PlayersPage />
      case 'moderation': return (
        <ModerationPage onOpenPunish={openPunish} />
      )
      case 'appeals': return <AppealsPage />
      case 'staff': return <StaffPage />
      case 'verification': return <VerificationPage />
      case 'alts': return <AltDetectionPage />
      case 'servers': return <ServersPage />
      case 'console': return <ConsolePage />
      case 'plugins': return <PluginsPage />
      case 'ai-tasks': return <AITasksPage />
      case 'audit': return <AuditPage />
      case 'feature-flags': return <FeatureFlagsPage />
      case 'settings': return <SettingsPage />
      default: return <OverviewPage />
    }
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-[#070914] overflow-hidden">
      {/* Disconnected banner — shown on every page when core is unreachable */}
      {status === 'disconnected' && <DisconnectedBanner />}

      <div className="flex flex-1 overflow-hidden">
        <Sidebar active={page} onChange={setPage} />
        <main className="flex-1 overflow-y-auto px-6 py-6 max-w-7xl w-full">
          {renderPage()}
        </main>
      </div>

      {/* Floating action buttons — bottom left above sidebar */}
      <div className="fixed bottom-4 left-4 flex flex-col gap-2 z-40">
        <button
          onClick={() => setBroadcastOpen(true)}
          title="Network Broadcast"
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-cyan-700/80 hover:bg-cyan-600/90 border border-cyan-500/40 text-white text-xs font-medium shadow-lg backdrop-blur-sm transition-colors"
        >
          <Megaphone className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Broadcast</span>
        </button>
        <button
          onClick={() => openPunish()}
          title="Issue Punishment"
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-rose-700/80 hover:bg-rose-600/90 border border-rose-500/40 text-white text-xs font-medium shadow-lg backdrop-blur-sm transition-colors"
        >
          <ShieldAlert className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Punish</span>
        </button>
      </div>

      {/* Modals */}
      <PunishModal
        open={punishOpen}
        onClose={() => setPunishOpen(false)}
        prefillUsername={punishUsername}
      />
      <BroadcastModal
        open={broadcastOpen}
        onClose={() => setBroadcastOpen(false)}
      />
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <DashboardApp />
    </AuthProvider>
  )
}
