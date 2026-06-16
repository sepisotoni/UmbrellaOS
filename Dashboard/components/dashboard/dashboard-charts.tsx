'use client'

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import type { ActivityPoint, AppealPoint, PunishmentPoint } from '@/lib/types'

const axis = {
  tickLine: false,
  axisLine: false,
  tickMargin: 8,
  fontSize: 11,
}

export function ActivityChart({ data }: { data: ActivityPoint[] }) {
  const config = {
    peak: { label: 'Peak Players', color: 'var(--chart-1)' },
    joins: { label: 'Joins', color: 'var(--chart-2)' },
    leaves: { label: 'Leaves', color: 'var(--chart-4)' },
  } satisfies ChartConfig

  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <CardTitle>Player Activity</CardTitle>
        <CardDescription>Hourly joins, leaves and peak concurrency (24h)</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={config} className="h-[260px] w-full">
          <AreaChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
            <defs>
              {Object.entries(config).map(([key, v]) => (
                <linearGradient key={key} id={`fill-${key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={v.color} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={v.color} stopOpacity={0.04} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="hour" interval={3} {...axis} />
            <YAxis width={36} {...axis} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Area dataKey="peak" type="monotone" stroke="var(--chart-1)" fill="url(#fill-peak)" strokeWidth={2} />
            <Area dataKey="joins" type="monotone" stroke="var(--chart-2)" fill="url(#fill-joins)" strokeWidth={2} />
            <Area dataKey="leaves" type="monotone" stroke="var(--chart-4)" fill="url(#fill-leaves)" strokeWidth={2} />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

export function PunishmentChart({ data }: { data: PunishmentPoint[] }) {
  const config = {
    warns: { label: 'Warns', color: 'var(--chart-3)' },
    mutes: { label: 'Mutes', color: 'var(--chart-1)' },
    tempbans: { label: 'Temp Bans', color: 'var(--chart-5)' },
    bans: { label: 'Bans', color: 'var(--chart-4)' },
  } satisfies ChartConfig

  return (
    <Card>
      <CardHeader>
        <CardTitle>Punishments</CardTitle>
        <CardDescription>Issued by type (14 days)</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={config} className="h-[260px] w-full">
          <BarChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
            <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="day" interval={2} {...axis} />
            <YAxis width={28} {...axis} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Bar dataKey="warns" stackId="a" fill="var(--chart-3)" />
            <Bar dataKey="mutes" stackId="a" fill="var(--chart-1)" />
            <Bar dataKey="tempbans" stackId="a" fill="var(--chart-5)" />
            <Bar dataKey="bans" stackId="a" fill="var(--chart-4)" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

export function AppealChart({ data }: { data: AppealPoint[] }) {
  const config = {
    open: { label: 'Open', color: 'var(--chart-3)' },
    accepted: { label: 'Accepted', color: 'var(--chart-2)' },
    denied: { label: 'Denied', color: 'var(--chart-4)' },
  } satisfies ChartConfig

  return (
    <Card>
      <CardHeader>
        <CardTitle>Appeals</CardTitle>
        <CardDescription>Open, accepted and denied (14 days)</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={config} className="h-[260px] w-full">
          <LineChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
            <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="day" interval={2} {...axis} />
            <YAxis width={28} {...axis} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Line dataKey="open" type="monotone" stroke="var(--chart-3)" strokeWidth={2} dot={false} />
            <Line dataKey="accepted" type="monotone" stroke="var(--chart-2)" strokeWidth={2} dot={false} />
            <Line dataKey="denied" type="monotone" stroke="var(--chart-4)" strokeWidth={2} dot={false} />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
