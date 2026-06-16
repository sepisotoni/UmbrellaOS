'use client'

import Link from 'next/link'
import { useMemo } from 'react'
import { Check, X, ArrowUpRight, UserPlus } from 'lucide-react'
import { useAppeals } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { GenericStatusBadge, PunishmentTypeBadge } from '@/components/status-badge'
import { timeAgo } from '@/lib/format'
import type { Appeal } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export default function AppealsPage() {
  const { data, isLoading } = useAppeals()

  const groups = useMemo(() => {
    const base = { open: [] as Appeal[], accepted: [] as Appeal[], denied: [] as Appeal[] }
    if (!data) return base
    for (const a of data) {
      if (a.status === 'accepted') base.accepted.push(a)
      else if (a.status === 'denied') base.denied.push(a)
      else base.open.push(a) // open + escalated
    }
    return base
  }, [data])

  return (
    <>
      <PageHeader
        title="Appeals"
        description="Queue-based moderation workflow for reviewing punishment appeals."
      />

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-64 rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <AppealColumn title="Open" tone="warning" appeals={groups.open} actionable />
          <AppealColumn title="Accepted" tone="success" appeals={groups.accepted} />
          <AppealColumn title="Denied" tone="danger" appeals={groups.denied} />
        </div>
      )}
    </>
  )
}

function AppealColumn({
  title,
  tone,
  appeals,
  actionable,
}: {
  title: string
  tone: 'warning' | 'success' | 'danger'
  appeals: Appeal[]
  actionable?: boolean
}) {
  const dot =
    tone === 'warning' ? 'bg-warning' : tone === 'success' ? 'bg-success' : 'bg-destructive'
  return (
    <section className="flex flex-col gap-3" aria-label={`${title} appeals`}>
      <div className="flex items-center gap-2">
        <span className={`size-2 rounded-full ${dot}`} aria-hidden />
        <h2 className="text-sm font-semibold">{title}</h2>
        <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
          {appeals.length}
        </span>
      </div>
      <div className="flex flex-col gap-3">
        {appeals.length === 0 ? (
          <Card>
            <CardContent className="py-10 text-center text-sm text-muted-foreground">
              No appeals.
            </CardContent>
          </Card>
        ) : (
          appeals.map((a) => <AppealCard key={a.id} a={a} actionable={actionable} />)
        )}
      </div>
    </section>
  )
}

function AppealCard({ a, actionable }: { a: Appeal; actionable?: boolean }) {
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-2 space-y-0 pb-3">
        <div className="flex flex-col gap-1">
          <Link
            href={`/players/${a.playerUuid}`}
            className="font-medium hover:underline"
          >
            {a.playerName}
          </Link>
          <div className="flex items-center gap-2">
            <PunishmentTypeBadge type={a.punishmentType} />
            <span className="text-xs text-muted-foreground">{a.id}</span>
          </div>
        </div>
        <GenericStatusBadge status={a.status} />
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="line-clamp-3 text-sm text-muted-foreground">{a.message}</p>
        {a.staffNotes ? (
          <p className="rounded-md border border-border bg-muted/40 p-2 text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Notes: </span>
            {a.staffNotes}
          </p>
        ) : null}
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{timeAgo(a.createdAt)}</span>
          {a.assignedTo ? (
            <span className="text-xs text-muted-foreground">@{a.assignedTo}</span>
          ) : null}
        </div>
        {actionable ? (
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" className="flex-1">
              <Check className="size-4" aria-hidden /> Accept
            </Button>
            <Button size="sm" variant="outline" className="flex-1">
              <X className="size-4" aria-hidden /> Deny
            </Button>
            <Button size="sm" variant="ghost" aria-label="Escalate">
              <ArrowUpRight className="size-4" aria-hidden />
            </Button>
            <Button size="sm" variant="ghost" aria-label="Assign">
              <UserPlus className="size-4" aria-hidden />
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
