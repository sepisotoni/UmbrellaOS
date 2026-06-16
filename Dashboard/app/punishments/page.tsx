'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'
import { Plus, Search } from 'lucide-react'
import { usePunishments } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { GenericStatusBadge, PunishmentTypeBadge } from '@/components/status-badge'
import { formatDate, formatNumber, timeAgo } from '@/lib/format'
import type { Punishment } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
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

export default function PunishmentsPage() {
  const { data, isLoading } = usePunishments()
  const [search, setSearch] = useState('')
  const [type, setType] = useState('all')
  const [status, setStatus] = useState('all')

  const filtered = useMemo(() => {
    if (!data) return []
    return data.filter((p) => {
      if (search) {
        const q = search.toLowerCase()
        if (
          !p.playerName.toLowerCase().includes(q) &&
          !p.reason.toLowerCase().includes(q) &&
          !p.id.toLowerCase().includes(q)
        )
          return false
      }
      if (type !== 'all' && p.type !== type) return false
      if (status !== 'all' && p.status !== status) return false
      return true
    })
  }, [data, search, type, status])

  return (
    <>
      <PageHeader
        title="Punishments"
        description="Network-wide moderation actions. Issue, edit and revoke punishments."
      >
        <Button size="sm">
          <Plus className="size-4" aria-hidden /> New punishment
        </Button>
      </PageHeader>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative w-full sm:max-w-sm">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            placeholder="Search player, reason, ID…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            aria-label="Search punishments"
          />
        </div>
        <Select value={type} onValueChange={(v) => setType(v ?? 'all')}>
          <SelectTrigger className="w-[150px]" aria-label="Filter by type">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            <SelectItem value="warn">Warn</SelectItem>
            <SelectItem value="mute">Mute</SelectItem>
            <SelectItem value="tempban">Temp Ban</SelectItem>
            <SelectItem value="ban">Ban</SelectItem>
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={(v) => setStatus(v ?? 'all')}>
          <SelectTrigger className="w-[150px]" aria-label="Filter by status">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="expired">Expired</SelectItem>
            <SelectItem value="revoked">Revoked</SelectItem>
            <SelectItem value="appealed">Appealed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Player</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead className="hidden md:table-cell">Staff</TableHead>
                <TableHead className="hidden lg:table-cell">Created</TableHead>
                <TableHead className="hidden lg:table-cell">Expires</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading
                ? Array.from({ length: 10 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell colSpan={7}>
                        <Skeleton className="h-8 w-full" />
                      </TableCell>
                    </TableRow>
                  ))
                : filtered.map((p) => <PunishmentRow key={p.id} p={p} />)}
              {!isLoading && filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                    No punishments match your filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </Card>
      {!isLoading && (
        <p className="text-sm text-muted-foreground">
          {formatNumber(filtered.length)} of {formatNumber(data?.length ?? 0)} punishments
        </p>
      )}
    </>
  )
}

function PunishmentRow({ p }: { p: Punishment }) {
  return (
    <TableRow>
      <TableCell>
        <Link
          href={`/players/${p.playerUuid}`}
          className="font-medium text-foreground hover:underline"
        >
          {p.playerName}
        </Link>
      </TableCell>
      <TableCell>
        <PunishmentTypeBadge type={p.type} />
      </TableCell>
      <TableCell className="max-w-[240px] truncate text-muted-foreground">{p.reason}</TableCell>
      <TableCell className="hidden text-muted-foreground md:table-cell">{p.staff}</TableCell>
      <TableCell className="hidden text-muted-foreground lg:table-cell">
        {timeAgo(p.createdAt)}
      </TableCell>
      <TableCell className="hidden text-muted-foreground lg:table-cell">
        {p.expiresAt ? formatDate(p.expiresAt) : 'Permanent'}
      </TableCell>
      <TableCell>
        <GenericStatusBadge status={p.status} />
      </TableCell>
    </TableRow>
  )
}
