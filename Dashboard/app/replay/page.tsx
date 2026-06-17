'use client'

import { useState } from 'react'
import { useReplaySessions } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { timeAgo } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import Link from 'next/link'

export default function ReplayPage() {
  const [filterUuid, setFilterUuid] = useState('')
  const [filterTrigger, setFilterTrigger] = useState('')
  const { data: sessions, isLoading } = useReplaySessions({
    minecraft_uuid: filterUuid || undefined,
    trigger: filterTrigger || undefined,
  })

  return (
    <>
      <PageHeader
        title="Replay System"
        description="View and manage replay sessions for incident review."
      />

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Input
              placeholder="Filter by player UUID"
              value={filterUuid}
              onChange={(e) => setFilterUuid(e.target.value)}
              className="font-mono"
            />
            <Input
              placeholder="Filter by trigger (ban, mute, anticheat, report, manual)"
              value={filterTrigger}
              onChange={(e) => setFilterTrigger(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Replay Sessions</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-64" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Trigger</TableHead>
                  <TableHead>Player UUID</TableHead>
                  <TableHead>Incident Time</TableHead>
                  <TableHead>Event Count</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions && sessions.length > 0 ? (
                  sessions.map((session: any) => (
                    <TableRow key={session.id}>
                      <TableCell className="font-medium">{session.trigger}</TableCell>
                      <TableCell className="font-mono text-sm">{session.minecraft_uuid}</TableCell>
                      <TableCell>{timeAgo(session.incident_at)}</TableCell>
                      <TableCell className="font-mono">{session.event_count}</TableCell>
                      <TableCell>
                        {session.ended_at ? (
                          <span className="text-green-600">Finalized</span>
                        ) : (
                          <span className="text-yellow-600">In Progress</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button asChild variant="outline" size="sm">
                          <Link href={`/replay/${session.id}`}>View</Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground">
                      No replay sessions found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  )
}
