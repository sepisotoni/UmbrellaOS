'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useReplaySession, useReplayEvents, useSnapshotsNearReplay } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { timeAgo } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import Link from 'next/link'

export default function ReplayDetailPage() {
  const params = useParams()
  const replayId = params.id as string
  const [filterEventType, setFilterEventType] = useState('')
  const { data: session, isLoading: sessionLoading } = useReplaySession(replayId)
  const { data: events, isLoading: eventsLoading } = useReplayEvents(replayId, {
    event_type: filterEventType || undefined,
  })
  const { data: nearbySnapshots, isLoading: snapshotsLoading } = useSnapshotsNearReplay(replayId)

  if (sessionLoading) {
    return (
      <>
        <PageHeader title="Replay Detail" description="Loading replay session..." />
        <Skeleton className="h-64" />
      </>
    )
  }

  if (!session) {
    return (
      <>
        <PageHeader title="Replay Detail" description="Session not found" />
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Replay session not found.</p>
            <Button asChild variant="outline" className="mt-4">
              <Link href="/replay">Back to Replays</Link>
            </Button>
          </CardContent>
        </Card>
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="Replay Detail"
        description={`Session ${session.id}`}
      />

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Session Metadata</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Trigger</p>
              <p className="font-medium">{session.trigger}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Triggered By</p>
              <p className="font-medium">{session.triggered_by}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Player UUID</p>
              <p className="font-mono text-sm">{session.minecraft_uuid}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Started At</p>
              <p className="font-medium">{timeAgo(session.started_at)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Incident At</p>
              <p className="font-medium">{timeAgo(session.incident_at)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Ended At</p>
              <p className="font-medium">{session.ended_at ? timeAgo(session.ended_at) : 'In Progress'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Event Count</p>
              <p className="font-mono">{session.event_count}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Created At</p>
              <p className="font-medium">{timeAgo(session.created_at)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Notes</p>
              <p className="font-medium">{session.notes || '-'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Event Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <Input
              placeholder="Filter by event type (movement, inventory, combat, command, damage, block)"
              value={filterEventType}
              onChange={(e) => setFilterEventType(e.target.value)}
            />
          </div>
          {eventsLoading ? (
            <Skeleton className="h-64" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Event Type</TableHead>
                  <TableHead>Player UUID</TableHead>
                  <TableHead>World</TableHead>
                  <TableHead>Data Summary</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events && events.length > 0 ? (
                  events.map((event: any) => (
                    <TableRow key={event.id}>
                      <TableCell className="font-mono text-sm">{timeAgo(event.timestamp)}</TableCell>
                      <TableCell className="font-medium">{event.event_type}</TableCell>
                      <TableCell className="font-mono text-sm">{event.minecraft_uuid}</TableCell>
                      <TableCell>{event.world || '-'}</TableCell>
                      <TableCell className="font-mono text-xs max-w-xs truncate">
                        {event.event_data_json}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground">
                      No events found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Nearby Snapshots</CardTitle>
        </CardHeader>
        <CardContent>
          {snapshotsLoading ? (
            <Skeleton className="h-32" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Trigger</TableHead>
                  <TableHead>Health</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {nearbySnapshots && nearbySnapshots.length > 0 ? (
                  nearbySnapshots.map((snapshot: any) => (
                    <TableRow key={snapshot.id}>
                      <TableCell className="font-mono text-sm">{timeAgo(snapshot.timestamp)}</TableCell>
                      <TableCell className="font-medium">{snapshot.trigger}</TableCell>
                      <TableCell className="font-mono">{snapshot.health ?? '-'}</TableCell>
                      <TableCell className="font-mono text-sm">
                        {snapshot.x !== null && snapshot.y !== null && snapshot.z !== null
                          ? `${snapshot.x}, ${snapshot.y}, ${snapshot.z}`
                          : '-'}
                      </TableCell>
                      <TableCell>
                        <Button asChild variant="outline" size="sm">
                          <Link href={`/snapshots/${snapshot.id}`}>View</Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground">
                      No snapshots found near this replay.
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
