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
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

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

export function Sidebar({ active, onChange }: SidebarProps) {
  const { user, logout } = useAuth()
  return (
    <aside className="w-56 shrink-0 flex flex-col border-r border-white/[0.07] bg-[#070914] overflow-y-auto">
      <div className="px-4 py-3 border-b border-white/[0.07]">
        <span className="text-xs font-bold tracking-widest text-violet-400 uppercase">UmbrellaOS</span>
      </div>
      <nav className="flex-1 py-2">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const isActive = active === item.id
          return (
            <button
              key={item.id}
              onClick={() => onChange(item.id)}
              className={`w-full flex items-center gap-2.5 px-4 py-2 text-xs font-medium transition-colors cursor-pointer ${
                isActive
                  ? 'bg-violet-500/10 text-violet-400 border-r-2 border-violet-500'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </button>
          )
        })}
      </nav>
      {user && (
        <div className="border-t border-white/[0.07] px-4 py-3 flex items-center gap-2.5">
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
    </aside>
  )
}
