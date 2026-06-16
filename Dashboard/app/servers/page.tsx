'use client'

import { Cpu, MemoryStick, RefreshCw, Wrench, Power, Search as SearchIcon } from 'lucide-react'
import { useServers } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { GenericStatusBadge } from '@/components/status-badge'
import { formatNumber } from '@/lib/format'
import type { MinecraftServer } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'

export default function ServersPage() {
  const { data, isLoading } = useServers()

  return (
    <>
      <PageHeader
        title="Servers"
        description="Live status and control for every node in the network."
      />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {isLoading || !data
          ? Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-64 rounded-xl" />
            ))
          : data.map((s) => <ServerCard key={s.id} server={s} />)}
      </div>
    </>
  )
}

function tpsTone(tps: number) {
  if (tps >= 19) return 'text-success'
  if (tps >= 15) return 'text-warning'
  return 'text-destructive'
}

function ServerCard({ server }: { server: MinecraftServer }) {
  const ramPct = Math.round((server.ramUsedMb / server.ramTotalMb) * 100)
  const online = server.status === 'online'
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="font-mono text-base">{server.name}</CardTitle>
          <GenericStatusBadge status={server.status} />
        </div>
        <p className="text-xs text-muted-foreground">
          {server.version} · {server.pluginsConnected}/{server.pluginsTotal} plugins
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3">
          <Metric label="TPS" value={online ? server.tps.toFixed(1) : '—'} valueClass={online ? tpsTone(server.tps) : ''} />
          <Metric
            label="Players"
            value={online ? `${formatNumber(server.players)} / ${formatNumber(server.maxPlayers)}` : '—'}
          />
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <Cpu className="size-3.5" aria-hidden /> CPU
            </span>
            <span className="tabular-nums">{online ? `${server.cpu}%` : '—'}</span>
          </div>
          <Progress value={online ? server.cpu : 0} />
          <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <MemoryStick className="size-3.5" aria-hidden /> RAM
            </span>
            <span className="tabular-nums">
              {(server.ramUsedMb / 1024).toFixed(1)} / {(server.ramTotalMb / 1024).toFixed(0)} GB
            </span>
          </div>
          <Progress value={ramPct} />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="outline">
            <SearchIcon className="size-4" aria-hidden /> Inspect
          </Button>
          <Button size="sm" variant="outline">
            <RefreshCw className="size-4" aria-hidden /> Restart
          </Button>
          <Button size="sm" variant="ghost" aria-label="Maintenance mode">
            <Wrench className="size-4" aria-hidden />
          </Button>
          <Button size="sm" variant="ghost" aria-label="Power">
            <Power className="size-4" aria-hidden />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function Metric({
  label,
  value,
  valueClass,
}: {
  label: string
  value: string
  valueClass?: string
}) {
  return (
    <div className="flex flex-col gap-0.5 rounded-lg border border-border bg-muted/30 p-2.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={`text-lg font-semibold tabular-nums ${valueClass ?? ''}`}>{value}</span>
    </div>
  )
}
