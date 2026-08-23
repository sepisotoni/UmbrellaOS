import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { dashboard, ServerRecord } from '../../lib/api'
import { Card, Skeleton, ErrorCard, Badge, Button } from '../ui'
import { RefreshCw, Server } from 'lucide-react'

function tpsColor(tps: number) {
  if (tps >= 19) return 'text-emerald-400'
  if (tps >= 15) return 'text-amber-400'
  return 'text-red-400'
}

function ServerCard({ s }: { s: ServerRecord }) {
  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server className="h-4 w-4 text-slate-500" />
          <span className="font-semibold text-slate-100 text-sm">{s.name}</span>
        </div>
        <Badge
          variant={
            s.status === 'online' ? 'success' : s.status === 'maintenance' ? 'warning' : 'danger'
          }
        >
          {s.status}
        </Badge>
      </div>

      <div className="grid grid-cols-3 gap-3 text-xs">
        <div className="rounded-lg bg-white/[0.04] p-2.5 text-center">
          <p className={`text-lg font-bold font-mono ${tpsColor(s.tps)}`}>{s.tps.toFixed(1)}</p>
          <p className="text-slate-500 mt-0.5">TPS</p>
        </div>
        <div className="rounded-lg bg-white/[0.04] p-2.5 text-center">
          <p className="text-lg font-bold text-slate-200">{s.players}</p>
          <p className="text-slate-500 mt-0.5">Players</p>
        </div>
        <div className="rounded-lg bg-white/[0.04] p-2.5 text-center">
          <p className="text-lg font-bold text-violet-400">
            {s.pluginsConnected}/{s.pluginsTotal}
          </p>
          <p className="text-slate-500 mt-0.5">Plugins</p>
        </div>
      </div>

      <div className="text-[11px] text-slate-500">
        Version: <span className="font-mono text-slate-400">{s.version}</span>
        {' · '}
        ID: <span className="font-mono text-slate-400">{s.id}</span>
      </div>
    </Card>
  )
}

export function ServersPage() {
  const { token } = useAuth()
  const { data, loading, error, reload } = useFetch<ServerRecord[]>(
    token ? () => dashboard.servers(token) : null,
    [token],
  )

  const servers = data ?? []
  const online = servers.filter((s) => s.status === 'online').length

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Fleet / Servers</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {loading ? '…' : `${online} of ${servers.length} servers online`}
          </p>
        </div>
        <Button variant="secondary" onClick={reload}>
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </Button>
      </div>

      {error && <ErrorCard message={error} onRetry={reload} />}

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-40 w-full" />)}
        </div>
      )}

      {!loading && !error && servers.length === 0 && (
        <Card className="text-center py-12 text-slate-500 text-sm">
          <Server className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p>No servers reporting heartbeats.</p>
          <p className="text-xs mt-1">Check that the UmbrellaOS Minecraft plugin is running and connected.</p>
        </Card>
      )}

      {servers.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {servers.map((s) => <ServerCard key={s.id} s={s} />)}
        </div>
      )}
    </div>
  )
}
