'use client'

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  XAxis,
  YAxis,
} from 'recharts'
import { useAnalytics } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
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
import { Skeleton } from '@/components/ui/skeleton'

const axis = { tickLine: false, axisLine: false, tickMargin: 8, fontSize: 11 }
const PIE_COLORS = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)', 'var(--chart-4)', 'var(--chart-5)']

export default function AnalyticsPage() {
  const { data, isLoading } = useAnalytics()

  if (isLoading || !data) {
    return (
      <>
        <PageHeader title="Analytics" description="Advanced network intelligence and trends." />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[320px] rounded-xl" />
          ))}
        </div>
      </>
    )
  }

  return (
    <>
      <PageHeader title="Analytics" description="Advanced network intelligence and trends." />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCard title="Player Growth" description="Daily active players (30 days)" className="lg:col-span-2">
          <ChartContainer
            config={{ value: { label: 'Players', color: 'var(--chart-1)' } } satisfies ChartConfig}
            className="h-[260px] w-full"
          >
            <AreaChart data={data.playerGrowth} margin={{ left: 4, right: 8, top: 8 }}>
              <defs>
                <linearGradient id="fill-growth" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0.04} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="label" interval={4} {...axis} />
              <YAxis width={44} {...axis} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Area dataKey="value" type="monotone" stroke="var(--chart-1)" fill="url(#fill-growth)" strokeWidth={2} />
            </AreaChart>
          </ChartContainer>
        </ChartCard>

        <ChartCard title="Retention" description="Cohort retention by day">
          <ChartContainer
            config={{ value: { label: 'Retained %', color: 'var(--chart-2)' } } satisfies ChartConfig}
            className="h-[240px] w-full"
          >
            <BarChart data={data.retention} margin={{ left: 4, right: 8, top: 8 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="label" {...axis} />
              <YAxis width={32} {...axis} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="value" fill="var(--chart-2)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartContainer>
        </ChartCard>

        <ChartCard title="Punishment Frequency" description="Issued by type (14 days)">
          <ChartContainer
            config={{
              warns: { label: 'Warns', color: 'var(--chart-3)' },
              mutes: { label: 'Mutes', color: 'var(--chart-1)' },
              tempbans: { label: 'Temp Bans', color: 'var(--chart-5)' },
              bans: { label: 'Bans', color: 'var(--chart-4)' },
            } satisfies ChartConfig}
            className="h-[240px] w-full"
          >
            <BarChart data={data.punishmentFrequency} margin={{ left: 4, right: 8, top: 8 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="day" interval={2} {...axis} />
              <YAxis width={28} {...axis} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="warns" stackId="a" fill="var(--chart-3)" />
              <Bar dataKey="mutes" stackId="a" fill="var(--chart-1)" />
              <Bar dataKey="tempbans" stackId="a" fill="var(--chart-5)" />
              <Bar dataKey="bans" stackId="a" fill="var(--chart-4)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ChartContainer>
        </ChartCard>

        <ChartCard title="Appeal Success Rate" description="Outcome distribution">
          <ChartContainer config={{} satisfies ChartConfig} className="mx-auto h-[240px] w-full">
            <PieChart>
              <ChartTooltip content={<ChartTooltipContent />} />
              <Pie data={data.appealSuccess} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
                {data.appealSuccess.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <ChartLegend content={<ChartLegendContent nameKey="name" />} />
            </PieChart>
          </ChartContainer>
        </ChartCard>

        <ChartCard title="Risk Distribution" description="Players by risk tier">
          <ChartContainer config={{} satisfies ChartConfig} className="mx-auto h-[240px] w-full">
            <PieChart>
              <ChartTooltip content={<ChartTooltipContent />} />
              <Pie data={data.riskDistribution} dataKey="value" nameKey="name" outerRadius={90}>
                {data.riskDistribution.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <ChartLegend content={<ChartLegendContent nameKey="name" />} />
            </PieChart>
          </ChartContainer>
        </ChartCard>

        <ChartCard title="Peak Hours" description="Average concurrency by hour">
          <ChartContainer
            config={{ value: { label: 'Players', color: 'var(--chart-1)' } } satisfies ChartConfig}
            className="h-[240px] w-full"
          >
            <LineChart data={data.peakHours} margin={{ left: 4, right: 8, top: 8 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="label" interval={3} {...axis} />
              <YAxis width={44} {...axis} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Line dataKey="value" type="monotone" stroke="var(--chart-1)" strokeWidth={2} dot={false} />
            </LineChart>
          </ChartContainer>
        </ChartCard>

        <ChartCard title="Top Staff Actions" description="Moderation actions this week">
          <ChartContainer
            config={{ actions: { label: 'Actions', color: 'var(--chart-2)' } } satisfies ChartConfig}
            className="h-[240px] w-full"
          >
            <BarChart data={data.topStaff} layout="vertical" margin={{ left: 8, right: 8, top: 4 }}>
              <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" {...axis} />
              <YAxis type="category" dataKey="name" width={64} {...axis} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="actions" fill="var(--chart-2)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ChartContainer>
        </ChartCard>

        <ChartCard title="Server Performance" description="TPS and CPU by server">
          <ChartContainer
            config={{
              tps: { label: 'TPS', color: 'var(--chart-2)' },
              cpu: { label: 'CPU %', color: 'var(--chart-4)' },
            } satisfies ChartConfig}
            className="h-[240px] w-full"
          >
            <BarChart data={data.serverPerformance} margin={{ left: 4, right: 8, top: 8 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" {...axis} />
              <YAxis width={32} {...axis} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar dataKey="tps" fill="var(--chart-2)" radius={[3, 3, 0, 0]} />
              <Bar dataKey="cpu" fill="var(--chart-4)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ChartContainer>
        </ChartCard>
      </div>
    </>
  )
}

function ChartCard({
  title,
  description,
  className,
  children,
}: {
  title: string
  description: string
  className?: string
  children: React.ReactNode
}) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}
