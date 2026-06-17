'use client'

import { useState } from 'react'
import { useServerSummary, useAnalyticsEvents, usePlayerStats } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { timeAgo } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'

export default function AnalyticsPage() {
  const { data: summary, isLoading: summaryLoading } = useServerSummary()
  const { data: events, isLoading: eventsLoading } = useAnalyticsEvents({ limit: 50 })
  const [playerUuid, setPlayerUuid] = useState('')
  const { data: playerStats, isLoading: playerStatsLoading } = usePlayerStats(playerUuid, 'alltime')

  return (
    <>
      <PageHeader
        title="Analytics"
        description="Server-wide analytics and player statistics."
      />

      {/* Server Summary Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
        {summaryLoading ? (
          <Skeleton className="h-24" />
        ) : (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Joins</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary?.joins || 0}</div>
            </CardContent>
          </Card>
        )}
        {summaryLoading ? (
          <Skeleton className="h-24" />
        ) : (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Deaths</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary?.deaths || 0}</div>
            </CardContent>
          </Card>
        )}
        {summaryLoading ? (
          <Skeleton className="h-24" />
        ) : (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Kills</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary?.kills || 0}</div>
            </CardContent>
          </Card>
        )}
        {summaryLoading ? (
          <Skeleton className="h-24" />
        ) : (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Chat Volume</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary?.chat_volume || 0}</div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Recent Events Table */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Recent Events</CardTitle>
        </CardHeader>
        <CardContent>
          {eventsLoading ? (
            <Skeleton className="h-64" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Event Type</TableHead>
                  <TableHead>Player UUID</TableHead>
                  <TableHead>Created At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events && events.length > 0 ? (
                  events.map((event: any) => (
                    <TableRow key={event.id}>
                      <TableCell className="font-medium">{event.event_type}</TableCell>
                      <TableCell className="font-mono text-sm">{event.minecraft_uuid || '-'}</TableCell>
                      <TableCell>{timeAgo(event.created_at)}</TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center text-muted-foreground">
                      No events recorded.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Player Stats Lookup */}
      <Card>
        <CardHeader>
          <CardTitle>Player Statistics Lookup</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 mb-4">
            <Input
              placeholder="Enter player UUID"
              value={playerUuid}
              onChange={(e) => setPlayerUuid(e.target.value)}
              className="font-mono"
            />
            <Button onClick={() => setPlayerUuid(playerUuid)}>Lookup</Button>
          </div>
          {playerUuid && playerStatsLoading ? (
            <Skeleton className="h-32" />
          ) : playerUuid && playerStats && playerStats.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Metric</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Updated At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {playerStats.map((stat: any, index: number) => (
                  <TableRow key={index}>
                    <TableCell className="font-medium">{stat.metric}</TableCell>
                    <TableCell className="font-mono">{stat.value}</TableCell>
                    <TableCell>{stat.period}</TableCell>
                    <TableCell>{timeAgo(stat.updated_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : playerUuid ? (
            <div className="text-center text-muted-foreground py-4">
              No statistics found for this player.
            </div>
          ) : null}
        </CardContent>
      </Card>
    </>
  )
}
