import {
  Activity,
  Boxes,
  ChartNoAxesCombined,
  FileClock,
  Gavel,
  HeartPulse,
  LayoutDashboard,
  MessagesSquare,
  Server,
  Settings,
  ShieldCheck,
  Users,
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
  { title: 'Analytics', href: '/analytics', icon: ChartNoAxesCombined, group: 'Overview' },
  { title: 'Punishments', href: '/punishments', icon: Gavel, group: 'Moderation' },
  { title: 'Appeals', href: '/appeals', icon: MessagesSquare, group: 'Moderation' },
  { title: 'Staff', href: '/staff', icon: ShieldCheck, group: 'Moderation' },
  { title: 'Servers', href: '/servers', icon: Server, group: 'Network' },
  { title: 'Plugins', href: '/plugins', icon: Boxes, group: 'Network' },
  { title: 'System Health', href: '/system', icon: HeartPulse, group: 'System' },
  { title: 'Audit Log', href: '/audit', icon: FileClock, group: 'System' },
  { title: 'Settings', href: '/settings', icon: Settings, group: 'System' },
]

export const navGroups = ['Overview', 'Moderation', 'Network', 'System'] as const

export { Activity }
