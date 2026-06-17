'use client'

import { useParams } from 'next/navigation'
import { useSnapshot } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { timeAgo } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import Link from 'next/link'

export default function SnapshotDetailPage() {
  const params = useParams()
  const snapshotId = params.id as string
  const { data: snapshot, isLoading } = useSnapshot(snapshotId)

  if (isLoading) {
    return (
      <>
        <PageHeader title="Snapshot Detail" description="Loading snapshot..." />
        <Skeleton className="h-64" />
      </>
    )
  }

  if (!snapshot) {
    return (
      <>
        <PageHeader title="Snapshot Detail" description="Snapshot not found" />
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Snapshot not found.</p>
            <Button asChild variant="outline" className="mt-4">
              <Link href="/snapshots">Back to Snapshots</Link>
            </Button>
          </CardContent>
        </Card>
      </>
    )
  }

  const parseJson = (jsonString: string | null) => {
    if (!jsonString) return null
    try {
      return JSON.stringify(JSON.parse(jsonString), null, 2)
    } catch {
      return jsonString
    }
  }

  return (
    <>
      <PageHeader
        title="Snapshot Detail"
        description={`Snapshot ${snapshot.id}`}
      />

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Player Info</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Player UUID</p>
              <p className="font-mono text-sm">{snapshot.minecraft_uuid}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Timestamp</p>
              <p className="font-medium">{timeAgo(snapshot.timestamp)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Trigger</p>
              <p className="font-medium">{snapshot.trigger}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Stats</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Health</p>
              <p className="font-mono">{snapshot.health ?? '-'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Food</p>
              <p className="font-mono">{snapshot.food ?? '-'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">XP</p>
              <p className="font-mono">{snapshot.xp ?? '-'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Location</p>
              <p className="font-mono text-sm">
                {snapshot.x !== null && snapshot.y !== null && snapshot.z !== null
                  ? `${snapshot.x}, ${snapshot.y}, ${snapshot.z}`
                  : '-'}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">World</p>
              <p className="font-medium">{snapshot.world || '-'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Dimension</p>
              <p className="font-medium">{snapshot.dimension || '-'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Yaw</p>
              <p className="font-mono">{snapshot.yaw ?? '-'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Pitch</p>
              <p className="font-mono">{snapshot.pitch ?? '-'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Inventory</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="bg-muted p-4 rounded text-xs overflow-auto max-h-64">
            {parseJson(snapshot.inventory_json) || 'No inventory data'}
          </pre>
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Armor</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="bg-muted p-4 rounded text-xs overflow-auto max-h-64">
            {parseJson(snapshot.armor_json) || 'No armor data'}
          </pre>
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Offhand</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="bg-muted p-4 rounded text-xs overflow-auto max-h-64">
            {parseJson(snapshot.offhand_json) || 'No offhand data'}
          </pre>
        </CardContent>
      </Card>

      {snapshot.replay_id && (
        <Card>
          <CardHeader>
            <CardTitle>Associated Replay</CardTitle>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link href={`/replay/${snapshot.replay_id}`}>View Replay</Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </>
  )
}
