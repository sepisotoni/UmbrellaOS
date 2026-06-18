'use client'

import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { useAudit } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { StatusPill } from '@/components/status-badge'
import { formatDate, formatNumber } from '@/lib/format'
import type { AuditCategory, AuditEntry } from '@/lib/types'
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

const categoryTone: Record<AuditCategory, 'danger' | 'info' | 'primary' | 'warning' | 'success' | 'neutral'> = {
  moderation: 'danger',
  appeal: 'info',
  settings: 'primary',
  staff: 'warning',
  server: 'info',
  plugin: 'success',
  auth: 'neutral',
}

const CATEGORIES: AuditCategory[] = [
  'moderation',
  'appeal',
  'settings',
  'staff',
  'server',
  'plugin',
  'auth',
]

export default function AuditPage() {
  const { data, isLoading } = useAudit()
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')

  const filtered = useMemo(() => {
    if (!data) return []
    return (Array.isArray(data) ? data : (data?.data || data?.logs || [])).filter((e) => {
      if (category !== 'all' && e.category !== category) return false
      if (search) {
        const q = search.toLowerCase()
        if (
          !e.actor.toLowerCase().includes(q) &&
          !e.action.toLowerCase().includes(q) &&
          !e.target.toLowerCase().includes(q) &&
          !e.ip.includes(q)
        )
          return false
      }
      return true
    })
  }, [data, search, category])

  return (
    <>
      <PageHeader
        title="Audit Log"
        description="Immutable record of every action performed in the system."
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative w-full sm:max-w-sm">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            placeholder="Search actor, action, target, IP…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            aria-label="Search audit log"
          />
        </div>
        <Select value={category} onValueChange={(v) => setCategory(v ?? 'all')}>
          <SelectTrigger className="w-[170px]" aria-label="Filter by category">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {CATEGORIES.map((c) => (
              <SelectItem key={c} value={c} className="capitalize">
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="hidden md:table-cell">Timestamp</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead>Action</TableHead>
                <TableHead className="hidden sm:table-cell">Target</TableHead>
                <TableHead>Category</TableHead>
                <TableHead className="hidden lg:table-cell text-right">IP</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading || !data
                ? Array.from({ length: 12 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell colSpan={6}>
                        <Skeleton className="h-8 w-full" />
                      </TableCell>
                    </TableRow>
                  ))
                : filtered.map((e) => <AuditRow key={e.id} e={e} />)}
              {!isLoading && filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                    No audit entries match your filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </Card>
      {!isLoading && (
        <p className="text-sm text-muted-foreground">
          {formatNumber(filtered.length)} of {formatNumber(data?.length ?? 0)} entries
        </p>
      )}
    </>
  )
}

function AuditRow({ e }: { e: AuditEntry }) {
  return (
    <TableRow>
      <TableCell className="hidden whitespace-nowrap text-muted-foreground md:table-cell">
        {formatDate(e.timestamp)}
      </TableCell>
      <TableCell>
        <div className="flex flex-col">
          <span className="font-medium">{e.actor}</span>
          <span className="text-xs text-muted-foreground">{e.actorRole}</span>
        </div>
      </TableCell>
      <TableCell>{e.action}</TableCell>
      <TableCell className="hidden font-mono text-sm text-muted-foreground sm:table-cell">
        {e.target}
      </TableCell>
      <TableCell>
        <StatusPill tone={categoryTone[e.category]} dot={false}>
          {e.category}
        </StatusPill>
      </TableCell>
      <TableCell className="hidden text-right font-mono text-xs text-muted-foreground lg:table-cell">
        {e.ip}
      </TableCell>
    </TableRow>
  )
}
