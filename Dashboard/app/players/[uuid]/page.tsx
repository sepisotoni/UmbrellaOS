'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowLeft, Flag } from 'lucide-react'
import { usePlayer, usePlayerPunishments, usePlayerAppeals } from '@/lib/queries'
import { PlayerAvatar } from '@/components/player-avatar'
import {
  GenericStatusBadge,
  PunishmentTypeBadge,
  RiskBadge,
  StatusDot,
  StatusPill,
} from '@/components/status-badge'
import { formatDate, formatNumber, formatPlaytime, timeAgo } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function PlayerDetailPage() {
  const params = useParams<{ uuid: string }>()
  const uuid = params.uuid
  const { data: player, isLoading } = usePlayer(uuid)
  const { data: punishments } = usePlayerPunishments(uuid)
  const { data: appeals } = usePlayerAppeals(uuid)

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-9 w-40" />
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    )
  }

  if (!player) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
        <p className="text-lg font-medium">Player not found</p>
        <p className="text-sm text-muted-foreground">
          No account matches UUID <span className="font-mono">{uuid}</span>.
        </p>
        <Button variant="outline" render={<Link href="/players" />}>
          Back to players
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/players"
        className="inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden /> Players
      </Link>

      {/* Header */}
      <Card>
        <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <PlayerAvatar username={player.username} uuid={player.uuid} className="size-16" />
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-semibold tracking-tight">{player.username}</h1>
                <StatusDot
                  tone={player.status === 'online' ? 'success' : 'neutral'}
                  ping={player.status === 'online'}
                />
              </div>
              <span className="font-mono text-xs text-muted-foreground">{player.uuid}</span>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <GenericStatusBadge status={player.status} />
                {player.currentServer ? (
                  <StatusPill tone="info" dot={false}>
                    {player.currentServer}
                  </StatusPill>
                ) : null}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex flex-col items-end gap-1">
              <span className="text-xs text-muted-foreground">Risk Score</span>
              <RiskBadge score={player.riskScore} />
            </div>
            <Button variant="outline" size="sm">
              <Flag className="size-4" aria-hidden /> Flag
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="ips">IPs</TabsTrigger>
          <TabsTrigger value="punishments">Punishments</TabsTrigger>
          <TabsTrigger value="appeals">Appeals</TabsTrigger>
          <TabsTrigger value="discord">Discord</TabsTrigger>
        </TabsList>

        {/* Overview */}
        <TabsContent value="overview" className="mt-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <Stat label="First Seen" value={formatDate(player.firstSeen)} />
            <Stat label="Last Seen" value={timeAgo(player.lastSeen)} />
            <Stat label="Total Playtime" value={formatPlaytime(player.playtimeHours)} />
            <Stat label="Total Joins" value={formatNumber(player.joins)} />
            <Stat label="Total Deaths" value={formatNumber(player.deaths)} />
            <Stat label="Punishments" value={formatNumber(player.punishmentCount)} />
            <Stat label="Known IPs" value={formatNumber(player.knownIpCount)} />
            <Stat
              label="Discord"
              value={player.discordLinked ? (player.discordTag ?? 'Linked') : 'Not linked'}
            />
          </div>
        </TabsContent>

        {/* IPs */}
        <TabsContent value="ips" className="mt-4">
          <Card className="overflow-hidden p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>IP Address</TableHead>
                    <TableHead className="hidden sm:table-cell">Country</TableHead>
                    <TableHead className="hidden md:table-cell">First Seen</TableHead>
                    <TableHead>Last Seen</TableHead>
                    <TableHead className="text-right">Uses</TableHead>
                    <TableHead className="text-right">Flagged</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(player.ips ?? []).map((ip) => (
                    <TableRow key={ip.address}>
                      <TableCell className="font-mono text-sm">{ip.address}</TableCell>
                      <TableCell className="hidden text-muted-foreground sm:table-cell">
                        {ip.country}
                      </TableCell>
                      <TableCell className="hidden text-muted-foreground md:table-cell">
                        {formatDate(ip.firstSeen)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{timeAgo(ip.lastSeen)}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatNumber(ip.usageCount)}
                      </TableCell>
                      <TableCell className="text-right">
                        {ip.flagged ? (
                          <StatusPill tone="danger" dot={false}>
                            Flagged
                          </StatusPill>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>
        </TabsContent>

        {/* Punishments */}
        <TabsContent value="punishments" className="mt-4">
          <Card className="overflow-hidden p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead className="hidden sm:table-cell">Staff</TableHead>
                    <TableHead className="hidden md:table-cell">Created</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(punishments ?? []).length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="h-20 text-center text-muted-foreground">
                        No punishment history.
                      </TableCell>
                    </TableRow>
                  ) : (
                    (punishments ?? []).map((p) => (
                      <TableRow key={p.id}>
                        <TableCell>
                          <PunishmentTypeBadge type={p.type} />
                        </TableCell>
                        <TableCell className="max-w-[260px] truncate">{p.reason}</TableCell>
                        <TableCell className="hidden text-muted-foreground sm:table-cell">
                          {p.staff}
                        </TableCell>
                        <TableCell className="hidden text-muted-foreground md:table-cell">
                          {formatDate(p.createdAt)}
                        </TableCell>
                        <TableCell>
                          <GenericStatusBadge status={p.status} />
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </Card>
        </TabsContent>

        {/* Appeals */}
        <TabsContent value="appeals" className="mt-4">
          <div className="flex flex-col gap-3">
            {(appeals ?? []).length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground">
                  No appeals submitted.
                </CardContent>
              </Card>
            ) : (
              (appeals ?? []).map((a) => (
                <Card key={a.id}>
                  <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
                    <div className="flex items-center gap-2">
                      <PunishmentTypeBadge type={a.punishmentType} />
                      <CardTitle className="text-base">{a.id}</CardTitle>
                    </div>
                    <GenericStatusBadge status={a.status} />
                  </CardHeader>
                  <CardContent className="flex flex-col gap-2">
                    <p className="text-sm text-muted-foreground">{a.message}</p>
                    {a.staffNotes ? (
                      <p className="rounded-md border border-border bg-muted/40 p-2 text-xs text-muted-foreground">
                        <span className="font-medium text-foreground">Staff notes: </span>
                        {a.staffNotes}
                      </p>
                    ) : null}
                    <span className="text-xs text-muted-foreground">{timeAgo(a.createdAt)}</span>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </TabsContent>

        {/* Discord */}
        <TabsContent value="discord" className="mt-4">
          <Card>
            <CardContent className="flex flex-col gap-3 p-5">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Link Status</span>
                {player.discordLinked ? (
                  <StatusPill tone="success">Linked</StatusPill>
                ) : (
                  <StatusPill tone="neutral">Not linked</StatusPill>
                )}
              </div>
              {player.discordLinked ? (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Discord Tag</span>
                  <span className="font-mono text-sm">{player.discordTag ?? '—'}</span>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-1 p-4">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-pretty text-lg font-semibold tracking-tight">{value}</span>
      </CardContent>
    </Card>
  )
}
