'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'
import { ArrowUpDown, Search } from 'lucide-react'
import { usePlayers } from '@/lib/queries'
import { PlayerAvatar } from '@/components/player-avatar'
import { RiskBadge, StatusDot } from '@/components/status-badge'
import { formatNumber, timeAgo, formatPlaytime, shortUuid } from '@/lib/format'
import type { Player } from '@/lib/types'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

type SortKey = 'lastSeen' | 'playtimeHours' | 'username' | 'riskScore' | 'punishmentCount'

const RECENT_MS = 1000 * 60 * 60 * 24 // 24h

export function PlayersTable() {
  const { data: players, isLoading } = usePlayers()
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<string>('all')
  const [sortKey, setSortKey] = useState<SortKey>('lastSeen')
  const [sortAsc, setSortAsc] = useState(false)

  const filtered = useMemo(() => {
    if (!players) return []
    const q = search.trim().toLowerCase()
    const list = players.filter((p) => {
      if (q) {
        const haystack = [
          p.username,
          p.uuid,
          p.discordTag ?? '',
          ...(p.ips?.map((ip) => ip.address) ?? []),
        ]
          .join(' ')
          .toLowerCase()
        if (!haystack.includes(q)) return false
      }
      switch (filter) {
        case 'online':
          return p.status === 'online'
        case 'offline':
          return p.status === 'offline'
        case 'risk':
          return p.riskScore >= 51
        case 'discord':
          return p.discordLinked
        case 'punished':
          return p.punishmentCount > 0
        case 'recent':
          return Date.now() - new Date(p.lastSeen).getTime() < RECENT_MS
        default:
          return true
      }
    })
    list.sort((a, b) => {
      let cmp = 0
      if (sortKey === 'username') cmp = a.username.localeCompare(b.username)
      else if (sortKey === 'playtimeHours') cmp = a.playtimeHours - b.playtimeHours
      else if (sortKey === 'riskScore') cmp = a.riskScore - b.riskScore
      else if (sortKey === 'punishmentCount') cmp = a.punishmentCount - b.punishmentCount
      else cmp = new Date(a.lastSeen).getTime() - new Date(b.lastSeen).getTime()
      return sortAsc ? cmp : -cmp
    })
    return list
  }, [players, search, filter, sortKey, sortAsc])

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc((v) => !v)
    else {
      setSortKey(key)
      setSortAsc(false)
    }
  }

  function SortHeader({
    label,
    sortField,
    className,
  }: {
    label: string
    sortField: SortKey
    className?: string
  }) {
    return (
      <button
        className="inline-flex items-center gap-1 hover:text-foreground"
        onClick={() => toggleSort(sortField)}
      >
        {label} <ArrowUpDown className="size-3" aria-hidden />
      </button>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-sm">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            placeholder="Search username, UUID, Discord, IP…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            aria-label="Search players"
          />
        </div>
        <Select value={filter} onValueChange={(v) => setFilter(v ?? 'all')}>
          <SelectTrigger className="w-[180px]" aria-label="Filter players">
            <SelectValue placeholder="Filter" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All players</SelectItem>
            <SelectItem value="online">Online</SelectItem>
            <SelectItem value="offline">Offline</SelectItem>
            <SelectItem value="risk">High risk (51+)</SelectItem>
            <SelectItem value="discord">Discord linked</SelectItem>
            <SelectItem value="punished">Punished</SelectItem>
            <SelectItem value="recent">Recently seen (24h)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>
                  <SortHeader label="Player" sortField="username" />
                </TableHead>
                <TableHead className="hidden xl:table-cell">UUID</TableHead>
                <TableHead>
                  <SortHeader label="Risk" sortField="riskScore" />
                </TableHead>
                <TableHead className="hidden lg:table-cell">Discord</TableHead>
                <TableHead className="hidden md:table-cell">
                  <SortHeader label="Playtime" sortField="playtimeHours" />
                </TableHead>
                <TableHead className="hidden lg:table-cell text-right">Deaths</TableHead>
                <TableHead className="hidden sm:table-cell text-right">
                  <SortHeader label="Punishments" sortField="punishmentCount" />
                </TableHead>
                <TableHead className="hidden xl:table-cell text-right">IPs</TableHead>
                <TableHead className="text-right">
                  <SortHeader label="Last seen" sortField="lastSeen" />
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading
                ? Array.from({ length: 10 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell colSpan={9}>
                        <Skeleton className="h-8 w-full" />
                      </TableCell>
                    </TableRow>
                  ))
                : filtered.map((p) => <PlayerRow key={p.uuid} player={p} />)}
              {!isLoading && filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} className="h-24 text-center text-muted-foreground">
                    No players match your filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </Card>
      {!isLoading && (
        <p className="text-sm text-muted-foreground">
          Showing {formatNumber(filtered.length)} of {formatNumber(players?.length ?? 0)} players
        </p>
      )}
    </div>
  )
}

function PlayerRow({ player }: { player: Player }) {
  return (
    <TableRow className="cursor-pointer">
      <TableCell>
        <Link
          href={`/players/${player.uuid}`}
          className="flex items-center gap-3"
        >
          <PlayerAvatar username={player.username} uuid={player.uuid} className="size-9" />
          <div className="flex flex-col">
            <span className="flex items-center gap-2 font-medium text-foreground">
              {player.username}
              <StatusDot tone={player.status === 'online' ? 'success' : 'neutral'} ping={player.status === 'online'} />
            </span>
            <span className="text-xs text-muted-foreground">
              {player.currentServer ? player.currentServer : 'Offline'}
            </span>
          </div>
        </Link>
      </TableCell>
      <TableCell className="hidden font-mono text-xs text-muted-foreground xl:table-cell">
        {shortUuid(player.uuid)}
      </TableCell>
      <TableCell>
        <RiskBadge score={player.riskScore} />
      </TableCell>
      <TableCell className="hidden lg:table-cell">
        {player.discordLinked ? (
          <span className="text-sm text-muted-foreground">{player.discordTag ?? 'Linked'}</span>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </TableCell>
      <TableCell className="hidden text-muted-foreground md:table-cell">
        {formatPlaytime(player.playtimeHours)}
      </TableCell>
      <TableCell className="hidden text-right text-muted-foreground lg:table-cell">
        {formatNumber(player.deaths)}
      </TableCell>
      <TableCell className="hidden text-right sm:table-cell">
        {player.punishmentCount > 0 ? (
          <Badge variant="secondary">{player.punishmentCount}</Badge>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </TableCell>
      <TableCell className="hidden text-right text-muted-foreground xl:table-cell">
        {player.knownIpCount}
      </TableCell>
      <TableCell className="text-right text-muted-foreground">{timeAgo(player.lastSeen)}</TableCell>
    </TableRow>
  )
}
