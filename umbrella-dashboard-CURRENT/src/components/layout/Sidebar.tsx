import { useState, useEffect, useCallback } from 'react'
import {
  LayoutDashboard,
  Users,
  Shield,
  MessageSquare,
  Server,
  Terminal,
  Puzzle,
  Bot,
  FileText,
  Flag,
  Settings,
  Link2,
  AlertOctagon,
  LogOut,
  Activity,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { dashboard, health, ServerRecord, HealthResponse } from '../../lib/api'

export type Page =
  | 'overview'
  | 'players'
  | 'moderation'
  | 'appeals'
  | 'staff'
  | 'verification'
  | 'alts'
  | 'servers'
  | 'console'
  | 'plugins'
  | 'ai-tasks'
  | 'audit'
  | 'feature-flags'
  | 'settings'

const NAV_ITEMS: { id: Page; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'players', label: 'Players', icon: Users },
  { id: 'moderation', label: 'Moderation', icon: Shield },
  { id: 'appeals', label: 'Appeals', icon: MessageSquare },
  { id: 'staff', label: 'Staff', icon: Users },
  { id: 'verification', label: 'Verification', icon: Link2 },
  { id: 'alts', label: 'Alt Detection', icon: AlertOctagon },
  { id: 'servers', label: 'Fleet / Servers', icon: Server },
  { id: 'console', label: 'Console', icon: Terminal },
  { id: 'plugins', label: 'Plugins', icon: Puzzle },
  { id: 'ai-tasks', label: 'AI Tasks', icon: Bot },
  { id: 'audit', label: 'Audit Log', icon: FileText },
  { id: 'feature-flags', label: 'Feature Flags', icon: Flag },
  { id: 'settings', label: 'Settings', icon: Settings },
]

interface SidebarProps {
  active: Page
  onChange: (p: Page) => void
}

function getStatusDot(server: ServerRecord): string {
  if (server.status === 'offline') return 'bg-rose-500'
  if (server.tps < 18) return 'bg-amber-400 animate-pulse'
  return 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]'
}

export function Sidebar({ active, onChange }: SidebarProps) {
  const { token, user, logout } = useAuth()
  const [servers, setServers] = useState<ServerRecord[]>([])
  const [healthData, setHealthData] = useState<HealthResponse | null>(null)
  const [healthOk, setHealthOk] = useState(true)

  const fetchServers = useCallback(() => {
    if (!token) return
    dashboard.servers(token).then(setServers).catch(() => {})
  }, [token])

  const fetchHealth = useCallback(() => {
    health.get()
      .then((d) => { setHealthData(d); setHealthOk(true) })
      .catch(() => { setHealthOk(false) })
  }, [])

  useEffect(() => {
    fetchServers()
    fetchHealth()
    const serversInterval = setInterval(fetchServers, 30_000)
    const healthInterval = setInterval(fetchHealth, 30_000)
    return () => { clearInterval(serversInterval); clearInterval(healthInterval) }
  }, [fetchServers, fetchHealth])

  return (
    <aside className="w-64 shrink-0 flex flex-col border-r border-white/[0.07] bg-[#070914] overflow-hidden">
      {/* Brand */}
      <div className="px-4 py-3 border-b border-white/[0.07]">
        <span className="text-xs font-bold tracking-widest text-violet-400 uppercase">UmbrellaOS</span>
      </div>

      {/* Nav section */}
      <div className="px-3 pt-3 pb-1">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 px-1 mb-1.5">Navigation</p>
      </div>
      <nav className="flex-none max-h-[52vh] overflow-y-auto py-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const isActive = active === item.id
          return (
            <button
              key={item.id}
              onClick={() => onChange(item.id)}
              className={`w-full flex items-center gap-2.5 px-4 py-2 text-xs font-medium transition-colors cursor-pointer ${
                isActive
                  ? 'bg-slate-800/90 text-cyan-300 border border-slate-700 shadow-sm'
                  : 'text-slate-400 hover:bg-slate-900/60 hover:text-slate-100'
              }`}
            >
              <Icon className="h-3.5 w-3.5 shrink-0" />
              {item.label}
            </button>
          )
        })}
      </nav>

      {/* Instances section */}
      {servers.length > 0 && (
        <div className="flex-1 overflow-hidden flex flex-col mt-2">
          <div className="flex items-center justify-between px-4 py-1.5">
            <span className="text-[10px] uppercase tracking-widest text-slate-500">
              Instances ({servers.length})
            </span>
            <Activity className="h-3 w-3 text-emerald-400" />
          </div>
          <div className="overflow-y-auto flex-1 px-3 pb-2 space-y-1">
            {servers.map((server) => (
              <button
                key={server.id}
                onClick={() => onChange('console')}
                className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition-colors hover:bg-slate-800/60 ${
                  active === 'console' ? 'border border-cyan-500/50 bg-cyan-950/30' : ''
                }`}
              >
                <span className={`h-2 w-2 shrink-0 rounded-full ${getStatusDot(server)}`} />
                <span className="flex-1 min-w-0 font-mono text-[11px] text-slate-300 truncate">{server.name}</span>
                <span className="flex items-center gap-1 shrink-0 font-mono text-[10px]">
                  <span className={server.tps < 18 ? 'text-amber-400' : 'text-slate-500'}>
                    {server.tps.toFixed(1)}
                  </span>
                  <span className="text-slate-600">|</span>
                  <span className="text-slate-400">{server.players}p</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Spacer if no servers */}
      {servers.length === 0 && <div className="flex-1" />}

      {/* User row */}
      {user && (
        <div className="px-4 py-3 flex items-center gap-2.5 border-t border-white/[0.07]">
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-slate-200 truncate">{user.username}</p>
            <p className="text-[10px] text-slate-500 truncate">{user.role ?? 'No role'}</p>
          </div>
          <button
            onClick={() => logout()}
            title="Logout"
            className="text-slate-500 hover:text-red-400 transition-colors cursor-pointer"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Footer — version badge */}
      <div className="border-t border-slate-800/80 bg-slate-900/40 px-4 py-2.5 flex items-center gap-2">
        <Server className="h-3.5 w-3.5 text-slate-500 shrink-0" />
        <span className="text-[11px] text-slate-400 flex-1">Umbrella Core</span>
        {healthOk && healthData ? (
          <span className="px-2 py-0.5 rounded border bg-emerald-950/60 text-emerald-400 border-emerald-500/30 font-mono text-[10px]">
            {healthData.version}
          </span>
        ) : (
          <span className="px-2 py-0.5 rounded border bg-rose-950/60 text-rose-400 border-rose-500/30 font-mono text-[10px]">
            Offline
          </span>
        )}
      </div>
    </aside>
  )
}
