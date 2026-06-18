import {
  Activity,
  AlertTriangle,
  BarChart2,
  Bot,
  Boxes,
  Camera,
  ChartNoAxesCombined,
  FileClock,
  Film,
  Gavel,
  HeartPulse,
  Languages,
  LayoutDashboard,
  MessagesSquare,
  Server,
  Settings,
  ShieldCheck,
  Users,
  Wand2,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  title: string
  href: string
  icon: LucideIcon
  group: 'Overview' | 'Moderation' | 'Network' | 'System'
}

export const navItems: NavItem[] = [
  { title: 'Dashboard', href: '/', icon: LayoutDashboard, group: 'Overview' },
  { title: 'Players', href: '/players', icon: Users, group: 'Overview' },
  { title: 'Analytics', href: '/analytics', icon: BarChart2, group: 'Overview' },
  { title: 'Replay', href: '/replay', icon: Film, group: 'Overview' },
  { title: 'Snapshots', href: '/snapshots', icon: Camera, group: 'Overview' },
  { title: 'AI Tasks', href: '/ai-tasks', icon: Bot, group: 'Overview' },
  { title: 'AI Config', href: '/ai-config', icon: Wand2, group: 'Overview' },
  { title: 'Punishments', href: '/punishments', icon: Gavel, group: 'Moderation' },
  { title: 'Appeals', href: '/appeals', icon: MessagesSquare, group: 'Moderation' },
  { title: 'Staff', href: '/staff', icon: ShieldCheck, group: 'Moderation' },
  { title: 'Verification', href: '/verification', icon: Activity, group: 'Moderation' },
  { title: 'Alts', href: '/alts', icon: AlertTriangle, group: 'Moderation' },
  { title: 'Servers', href: '/servers', icon: Server, group: 'Network' },
  { title: 'Plugins', href: '/plugins', icon: Boxes, group: 'Network' },
  { title: 'Translation', href: '/translation', icon: Languages, group: 'Network' },
  { title: 'System Health', href: '/system', icon: HeartPulse, group: 'System' },
  { title: 'Audit Log', href: '/audit', icon: FileClock, group: 'System' },
  { title: 'Settings', href: '/settings', icon: Settings, group: 'System' },
]

export const navGroups = ['Overview', 'Moderation', 'Network', 'System'] as const

export { Activity }
