import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { dashboard, anticheat, appeals } from '../../lib/api'
import { Card, Skeleton, ErrorCard, Badge } from '../ui'
import { Server, Users, ShieldAlert, Gavel } from 'lucide-react'

function StatCard({
  label,
  value,
  icon: Icon,
  loading,
  color = 'violet',
}: {
  label: string
  value: string | number
  icon: React.ComponentType<{ className?: string }>
  loading: boolean
  color?: string
}) {
  const colorMap: Record<string, string> = {
    violet: 'text-violet-400 bg-violet-500/10',
    emerald: 'text-emerald-400 bg-emerald-500/10',
    amber: 'text-amber-400 bg-amber-500/10',
    red: 'text-red-400 bg-red-500/10',
  }
  const cls = colorMap[color] ?? colorMap.violet
  return (
    <Card className="flex items-center gap-4">
      <div className={`rounded-xl p-3 ${cls}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-[11px] text-slate-500 uppercase tracking-wider">{label}</p>
        {loading ? (
          <Skeleton className="h-6 w-12 mt-1" />
        ) : (
          <p className="text-xl font-bold text-slate-100 mt-0.5">{value}</p>
        )}
      </div>
    </Card>
  )
}

export function OverviewPage() {
  const { token } = useAuth()

  const serversState = useFetch(token ? () => dashboard.servers(token) : null, [token])
  const violationsState = useFetch(
    token ? () => anticheat.violations(token, { limit: 1 }) : null,
    [token],
  )
  const appealsState = useFetch(
    token ? () => appeals.list(token, { status: 'pending', limit: 100 }) : null,
    [token],
  )

  const servers = serversState.data ?? []
  const serversOnline = servers.filter((s) => s.status === 'online').length
  const totalPlayers = servers.reduce((sum, s) => sum + s.players, 0)
  const flagCount = (violationsState.data ?? []).length > 0 ? '1+' : '0'
  const activeAppeals = (appealsState.data ?? []).length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">Overview</h1>
        <p className="text-xs text-slate-500 mt-0.5">Live network status</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Servers Online"
          value={serversOnline}
          icon={Server}
          loading={serversState.loading}
          color="emerald"
        />
        <StatCard
          label="Players Online"
          value={totalPlayers}
          icon={Users}
          loading={serversState.loading}
          color="violet"
        />
        <StatCard
          label="GrimAC Flags (last fetch)"
          value={flagCount}
          icon={ShieldAlert}
          loading={violationsState.loading}
          color="amber"
        />
        <StatCard
          label="Pending Appeals"
          value={activeAppeals}
          icon={Gavel}
          loading={appealsState.loading}
          color="red"
        />
      </div>

      {/* Servers table */}
      <div>
        <h2 className="text-sm font-medium text-slate-300 mb-3">Server Fleet</h2>
        {serversState.error && (
          <ErrorCard message={serversState.error} onRetry={serversState.reload} />
        )}
        {serversState.loading && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        )}
        {!serversState.loading && !serversState.error && servers.length === 0 && (
          <Card className="text-center py-8 text-slate-500 text-sm">
            No servers reporting heartbeats. Check that the Minecraft plugin is connected.
          </Card>
        )}
        {servers.length > 0 && (
          <div className="rounded-xl border border-white/[0.07] overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="px-4 py-2.5 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">Server</th>
                  <th className="px-4 py-2.5 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-2.5 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">TPS</th>
                  <th className="px-4 py-2.5 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">Players</th>
                  <th className="px-4 py-2.5 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">Version</th>
                </tr>
              </thead>
              <tbody>
                {servers.map((s) => (
                  <tr key={s.id} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                    <td className="px-4 py-2.5 font-medium text-slate-200 text-xs">{s.name}</td>
                    <td className="px-4 py-2.5">
                      <Badge
                        variant={
                          s.status === 'online' ? 'success' : s.status === 'maintenance' ? 'warning' : 'danger'
                        }
                      >
                        {s.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 text-xs font-mono text-slate-300">
                      <span className={s.tps < 18 ? 'text-amber-400' : 'text-emerald-400'}>
                        {s.tps.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-slate-300">{s.players}</td>
                    <td className="px-4 py-2.5 text-xs text-slate-500 font-mono">{s.version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
