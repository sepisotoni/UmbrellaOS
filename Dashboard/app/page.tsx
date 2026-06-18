'use client'

import {
  ActivityChart,
  AppealChart,
  PunishmentChart,
} from '@/components/dashboard/dashboard-charts'
import { StatCard } from '@/components/dashboard/stat-card'
import { PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useDashboard, useConnectionTest } from '@/lib/queries'

export default function DashboardPage() {
  const { data, isLoading } = useDashboard()
  const { data: connectionData, isLoading: connectionLoading, isError: connectionError } = useConnectionTest()

  const isLive = !connectionLoading && !connectionError && connectionData

  return (
    <>
      <PageHeader
        title="Network Overview"
        description="Live operational snapshot of the entire Minecraft network."
      >
        <div className="flex items-center gap-3">
          {isLive ? (
            <div className="flex items-center gap-1.5 rounded-full bg-green-500/10 border border-green-500/20 px-3 py-1">
              <div className="size-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-xs font-medium text-green-500">Live</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 rounded-full bg-red-500/10 border border-red-500/20 px-3 py-1">
              <div className="size-2 rounded-full bg-red-500" />
              <span className="text-xs font-medium text-red-500">Demo</span>
            </div>
          )}
          <Button variant="outline" size="sm">
            Last 24 hours
          </Button>
          <Button size="sm">Export report</Button>
        </div>
      </PageHeader>

      <section
        aria-label="Key metrics"
        className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6"
      >
        {isLoading || !data
          ? Array.from({ length: 12 }).map((_, i) => (
              <Skeleton key={i} className="h-[124px] rounded-xl" />
            ))
          : data.cards.map((card) => <StatCard key={card.id} card={card} />)}
      </section>

      <section aria-label="Trends" className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {isLoading || !data ? (
          <>
            <Skeleton className="h-[340px] rounded-xl lg:col-span-2" />
            <Skeleton className="h-[340px] rounded-xl" />
            <Skeleton className="h-[340px] rounded-xl" />
          </>
        ) : (
          <>
            <ActivityChart data={data.activity} />
            <PunishmentChart data={data.punishments} />
            <AppealChart data={data.appeals} />
          </>
        )}
      </section>
    </>
  )
}
