'use client'

import { useState } from 'react'
import { useSnapshots } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { timeAgo } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import Link from 'next/link'

export default function SnapshotsPage() {
  const [uuid, setUuid] = useState('')
  const [searchUuid, setSearchUuid] = useState('')
  const { data: snapshots, isLoading } = useSnapshots(searchUuid, { limit: 50 })

  const handleSearch = () => {
    setSearchUuid(uuid)
  }

  return (
    <>
      <PageHeader
        title="Player Snapshots"
        description="View and manage player state snapshots."
      />

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Search Player</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Input
              placeholder="Enter player UUID"
              value={uuid}
              onChange={(e) => setUuid(e.target.value)}
              className="font-mono"
            />
            <Button onClick={handleSearch}>Search</Button>
          </div>
        </CardContent>
      </Card>

      {searchUuid && (
        <Card>
          <CardHeader>
            <CardTitle>Snapshots for {searchUuid}</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-64" />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Trigger</TableHead>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>World</TableHead>
                    <TableHead>Health</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {snapshots && snapshots.length > 0 ? (
                    snapshots.map((snapshot: any) => (
                      <TableRow key={snapshot.id}>
                        <TableCell className="font-medium">{snapshot.trigger}</TableCell>
                        <TableCell>{timeAgo(snapshot.timestamp)}</TableCell>
                        <TableCell>{snapshot.world || '-'}</TableCell>
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
                      <TableCell colSpan={6} className="text-center text-muted-foreground">
                        No snapshots found for this player.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </>
  )
}
