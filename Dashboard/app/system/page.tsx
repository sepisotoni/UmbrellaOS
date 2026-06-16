'use client'

import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from 'recharts'
import { Activity, Cpu, HardDrive, MemoryStick, Network, Timer } from 'lucide-react'
import { useSystemHealth } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { StatusDot } from '@/components/status-badge'
import { formatNumber } from '@/lib/format'
import type { HealthComponent } from '@/lib/types'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'

const axis = { tickLine: false, axisLine: false, tickMargin: 8, fontSize: 11 }

const healthTone = {
  healthy: 'success',
  degraded: 'warning',
  down: 'danger',
} as const

export default function SystemHealthPage() {
  const { data, isLoading } = useSystemHealth()

  if (isLoading || !data) {
    return (
      <>
        <PageHeader title="System Health" description="Live infrastructure monitoring." />
        <Skeleton className="h-96 w-full rounded-xl" />
      </>
    )
  }

  return (
    <>
      <PageHeader title="System Health" description="Live infrastructure monitoring. Auto-refreshes every 5s.">
        <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
          <StatusDot tone="success" ping /> Live
        </span>
      </PageHeader>

      <section aria-label="Resource usage" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <ResourceCard icon={<Cpu className="size-4" />} label="CPU" pct={data.cpuPct} />
        <ResourceCard icon={<MemoryStick className="size-4" />} label="Memory" pct={data.memoryUsedPct} />
        <ResourceCard icon={<HardDrive className="size-4" />} label="Disk" pct={data.diskPct} />
        <Card>
          <CardContent className="flex flex-col gap-2 p-4">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <Network className="size-4" aria-hidden /> Connections
              </span>
            </div>
            <span className="text-2xl font-semibold tabular-nums">{formatNumber(data.connections)}</span>
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <Timer className="size-3.5" aria-hidden /> {data.apiLatencyMs}ms API latency
            </span>
          </CardContent>
        </Card>
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>API Latency</CardTitle>
            <CardDescription>Response time over recent samples (ms)</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer
              config={{ value: { label: 'Latency (ms)', color: 'var(--chart-1)' } } satisfies ChartConfig}
              className="h-[240px] w-full"
            >
              <AreaChart data={data.latencyHistory} margin={{ left: 4, right: 8, top: 8 }}>
                <defs>
                  <linearGradient id="fill-latency" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="label" interval={4} {...axis} />
                <YAxis width={36} {...axis} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Area dataKey="value" type="monotone" stroke="var(--chart-1)" fill="url(#fill-latency)" strokeWidth={2} />
              </AreaChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Components</CardTitle>
            <CardDescription>Subsystem status</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {data.components.map((c) => (
              <ComponentRow key={c.id} c={c} />
            ))}
          </CardContent>
        </Card>
      </div>
    </>
  )
}

function ResourceCard({
  icon,
  label,
  pct,
}: {
  icon: React.ReactNode
  label: string
  pct: number
}) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-2 p-4">
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
          {icon} {label}
        </div>
        <span className="text-2xl font-semibold tabular-nums">{pct}%</span>
        <Progress value={pct} />
      </CardContent>
    </Card>
  )
}

function ComponentRow({ c }: { c: HealthComponent }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-muted/30 p-3">
      <div className="flex items-center gap-3">
        <StatusDot tone={healthTone[c.status]} ping={c.status === 'healthy'} />
        <div className="flex flex-col">
          <span className="text-sm font-medium">{c.label}</span>
          <span className="text-xs text-muted-foreground">{c.detail}</span>
        </div>
      </div>
      {typeof c.latencyMs === 'number' ? (
        <span className="text-xs tabular-nums text-muted-foreground">{c.latencyMs}ms</span>
      ) : null}
    </div>
  )
}
