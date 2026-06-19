'use client'

import { Power, RefreshCw, Search as SearchIcon, Activity } from 'lucide-react'
import { usePlugins, usePluginControl } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { GenericStatusBadge } from '@/components/status-badge'
import { timeAgo } from '@/lib/format'
import type { Plugin } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export default function PluginsPage() {
  const { data, isLoading, refetch } = usePlugins() // Added refetch

  return (
    <>
      <PageHeader
        title="Plugins"
        description="Plugins connected to Umbrella Core across the network mesh."
      />
      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Plugin</TableHead>
                <TableHead className="hidden sm:table-cell">Version</TableHead>
                <TableHead className="hidden md:table-cell">Server</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="hidden lg:table-cell text-right">Heartbeat</TableHead>
                <TableHead className="hidden lg:table-cell text-right">Last seen</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading || !data
                ? Array.from({ length: 8 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell colSpan={7}>
                        <Skeleton className="h-8 w-full" />
                      </TableCell>
                    </TableRow>
                  ))
                : data.map((p) => <PluginRow key={p.id} p={p} refetchPlugins={refetch} />)} {/* Pass refetch as prop */}
            </TableBody>
          </Table>
        </div>
      </Card>
    </>
  )
}

function heartbeatTone(ms: number, status: string) {
  if (status === 'disconnected') return 'text-destructive'
  if (ms > 800) return 'text-warning'
  return 'text-success'
}

function PluginRow({ p, refetchPlugins }: { p: Plugin; refetchPlugins: () => Promise<unknown> }) { // Receive refetch prop
  const pluginControl = usePluginControl()

  async function handlePluginControl(action: 'reload' | 'toggle') {
    try {
      await pluginControl.mutateAsync({ plugin_name: p.id, action })
      toast.success(`${p.name} ${action} command sent.`)
      refetchPlugins() // Refresh plugin data after successful action
    } catch (e) {
      toast.error(e instanceof Error ? e.message : `Failed to ${action} ${p.name}`)
    }
  }

  return (
    <TableRow>
      <TableCell>
        <div className="flex flex-col">
          <span className="font-medium">{p.name}</span>
          <span className="font-mono text-xs text-muted-foreground">{p.id}</span>
        </div>
      </TableCell>
      <TableCell className="hidden font-mono text-sm text-muted-foreground sm:table-cell">
        {p.version}
      </TableCell>
      <TableCell className="hidden font-mono text-sm text-muted-foreground md:table-cell">
        {p.server}
      </TableCell>
      <TableCell>
        <GenericStatusBadge status={p.status} />
      </TableCell>
      <TableCell className="hidden text-right lg:table-cell">
        <span className={`inline-flex items-center gap-1 tabular-nums ${heartbeatTone(p.heartbeatMs, p.status)}`}>
          <Activity className="size-3.5" aria-hidden />
          {p.status === 'disconnected' ? '—' : `${p.heartbeatMs}ms`}
        </span>
      </TableCell>
      <TableCell className="hidden text-right text-muted-foreground lg:table-cell">
        {timeAgo(p.lastSeen)}
      </TableCell>
      <TableCell className="text-right">
        <div className="flex items-center justify-end gap-1">
          <Button size="sm" variant="ghost" aria-label="Inspect plugin">
            <SearchIcon className="size-4" aria-hidden />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            aria-label="Reload plugin"
            onClick={() => handlePluginControl('reload')}
            disabled={pluginControl.isPending}
          >
            <RefreshCw className="size-4" aria-hidden />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            aria-label="Toggle plugin"
            onClick={() => handlePluginControl('toggle')}
            disabled={pluginControl.isPending}
          >
            <Power className="size-4" aria-hidden />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  )
}
