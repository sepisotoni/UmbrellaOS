'use client'

import { Bell, Search } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useMemo, useState } from 'react'
import { GlobalSearch } from '@/components/global-search'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { useAuth } from '@/components/auth-context'

const NOTIFICATIONS = [
  { id: 1, title: 'New appeal submitted', detail: 'EnderByte appealed a tempban', tone: 'warning' as const },
  { id: 2, title: 'Plugin disconnected', detail: 'WorldGuardLink lost heartbeat', tone: 'danger' as const },
  { id: 3, title: 'High risk login', detail: 'VoidSeeker flagged (risk 92)', tone: 'danger' as const },
  { id: 4, title: 'Server restored', detail: 'survival-02 back online', tone: 'success' as const },
]

export function TopBar() {
  const router = useRouter()
  const { user, isLoading: authLoading, refreshUser } = useAuth()
  const [searchOpen, setSearchOpen] = useState(false)

  const handleSignOut = () => {
    localStorage.removeItem('umbrella_token')
    router.push('/login')
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setSearchOpen(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const toneClass = useMemo(
    () => ({
      warning: 'bg-warning',
      danger: 'bg-destructive',
      success: 'bg-success',
    }),
    [],
  )

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-border bg-background/80 px-3 backdrop-blur supports-[backdrop-filter]:bg-background/60 md:px-4">
      <SidebarTrigger className="text-muted-foreground" />
      <Separator orientation="vertical" className="mr-1 h-6" />

      {/* Network status pills */}
      <div className="hidden items-center gap-2 md:flex">
        <span className="flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs">
          <span className="size-1.5 rounded-full bg-success" />
          <span className="text-muted-foreground">Core</span>
          <span className="font-medium text-foreground">Online</span>
        </span>
        <span className="flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs">
          <span className="size-1.5 rounded-full bg-success" />
          <span className="text-muted-foreground">Servers</span>
          <span className="font-medium text-foreground">5 / 6</span>
        </span>
      </div>

      <div className="flex-1" />

      {/* Search trigger */}
      <Button
        variant="outline"
        className="hidden w-56 justify-start gap-2 text-muted-foreground sm:flex"
        onClick={() => setSearchOpen(true)}
      >
        <Search data-icon="inline-start" />
        <span className="flex-1 text-left">Search…</span>
        <kbd className="rounded border border-border bg-muted px-1.5 text-[10px] font-medium text-muted-foreground">
          ⌘K
        </kbd>
      </Button>
      <Button
        variant="outline"
        size="icon"
        className="sm:hidden"
        aria-label="Search"
        onClick={() => setSearchOpen(true)}
      >
        <Search />
      </Button>

      {/* Notifications */}
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button variant="ghost" size="icon" aria-label="Notifications" className="relative">
              <Bell />
              <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-destructive ring-2 ring-background" />
            </Button>
          }
        />
        <DropdownMenuContent align="end" className="w-80">
          <DropdownMenuLabel className="flex items-center justify-between">
            Notifications
            <Badge variant="secondary">{NOTIFICATIONS.length} new</Badge>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {NOTIFICATIONS.map((n) => (
            <DropdownMenuItem key={n.id} className="flex items-start gap-2.5 py-2">
              <span className={`mt-1.5 size-2 shrink-0 rounded-full ${toneClass[n.tone]}`} />
              <span className="flex flex-col gap-0.5">
                <span className="text-sm font-medium">{n.title}</span>
                <span className="text-xs text-muted-foreground">{n.detail}</span>
              </span>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* User menu */}
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button variant="ghost" className="gap-2 px-1.5">
              <Avatar className="size-7">
                <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                  {user?.username?.slice(0, 2).toUpperCase() || 'AU'}
                </AvatarFallback>
              </Avatar>
              <span className="hidden text-sm font-medium md:inline">
                {authLoading ? 'Loading...' : user?.username || 'User'}
              </span>
            </Button>
          }
        />
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuLabel className="flex flex-col">
            <span>{user?.username || 'User'}</span>
            <span className="text-xs font-normal text-muted-foreground">
              {user?.is_active ? (user?.role || 'Staff') : 'Inactive'}
            </span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => router.push('/staff')}>Staff</DropdownMenuItem>
          <DropdownMenuItem onClick={() => router.push('/settings')}>Settings</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive" onClick={handleSignOut}>Sign out</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <GlobalSearch open={searchOpen} onOpenChange={setSearchOpen} />
    </header>
  )
}
