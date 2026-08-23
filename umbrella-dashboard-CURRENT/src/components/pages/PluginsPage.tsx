import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { dashboard, PluginRecord } from '../../lib/api'
import { Card, Skeleton, ErrorCard, Badge, Button } from '../ui'
import { Puzzle, RefreshCw } from 'lucide-react'

export function PluginsPage() {
  const { token } = useAuth()
  const { data, loading, error, reload } = useFetch<PluginRecord[]>(
    token ? () => dashboard.plugins(token) : null,
    [token],
  )

  const plugins = data ?? []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Plugins</h1>
          <p className="text-xs text-slate-500 mt-0.5">Plugin heartbeat status per server</p>
        </div>
        <Button variant="secondary" onClick={reload}>
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </Button>
      </div>

      {error && <ErrorCard message={error} onRetry={reload} />}
      {loading && (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
        </div>
      )}

      {!loading && !error && plugins.length === 0 && (
        <Card className="text-center py-12 text-slate-500 text-sm">
          <Puzzle className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p>No plugin heartbeats received.</p>
          <p className="text-xs mt-1">Plugins report here via the UmbrellaOS plugin heartbeat.</p>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {plugins.map((p) => (
          <Card key={p.id} className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-violet-500/10 p-2">
                <Puzzle className="h-4 w-4 text-violet-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-200">{p.name}</p>
                <p className="text-[11px] text-slate-500">
                  v{p.version} · {p.server}
                </p>
                <p className="text-[11px] text-slate-600">
                  Heartbeat: {p.heartbeatMs}ms ago
                </p>
              </div>
            </div>
            <Badge variant={p.status === 'connected' ? 'success' : 'danger'}>
              {p.status}
            </Badge>
          </Card>
        ))}
      </div>
    </div>
  )
}
