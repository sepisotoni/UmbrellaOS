'use client'

import { useRouter } from 'next/navigation'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { navItems } from '@/lib/nav'
import { usePlayers } from '@/lib/queries'

export function GlobalSearch({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const router = useRouter()
  const { data: players } = usePlayers()

  function go(href: string) {
    onOpenChange(false)
    router.push(href)
  }

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Search UmbrellaOS"
      description="Search players, pages, UUIDs and Discord IDs"
    >
      <CommandInput placeholder="Search players, pages, UUID, IP, Discord ID…" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Navigation">
          {navItems.map((item) => (
            <CommandItem
              key={item.href}
              value={`nav ${item.title}`}
              onSelect={() => go(item.href)}
            >
              <item.icon />
              {item.title}
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandGroup heading="Players">
          {(players ?? []).slice(0, 8).map((p) => (
            <CommandItem
              key={p.uuid}
              value={`${p.username} ${p.uuid} ${p.discordTag ?? ''}`}
              onSelect={() => go(`/players/${p.uuid}`)}
            >
              <span className="font-medium">{p.username}</span>
              <span className="ml-auto font-mono text-xs text-muted-foreground">
                {p.uuid.slice(0, 8)}
              </span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
