import { useState, useCallback } from 'react'
import { Search, User, Bot, ChevronRight } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { players, aiTasks, PlayerSchema, FullProfileResponse } from '../../lib/api'
import { ApiError } from '../../lib/api'
import {
  Card, Button, Input, Skeleton, ErrorCard, Badge, Modal, Tabs, Table, Th, Td,
} from '../ui'

function formatDate(d: string) {
  return new Date(d).toLocaleDateString()
}
function formatMinutes(m: number) {
  const h = Math.floor(m / 60)
  return h > 0 ? `${h}h ${m % 60}m` : `${m}m`
}

function FullProfile({
  uuid,
  token,
  username,
}: {
  uuid: string
  token: string
  username: string
}) {
  const [tab, setTab] = useState('overview')
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)
  const [aiResult, setAiResult] = useState<string | null>(null)

  const profileState = useFetch<FullProfileResponse>(
    () => players.fullProfile(token, uuid),
    [uuid],
  )
  const profile = profileState.data

  const triggerAiReview = async () => {
    setAiLoading(true)
    setAiError(null)
    try {
      const task = await aiTasks.reviewPlayer(token, uuid)
      setAiResult(task.ai_summary ?? 'Review complete — no summary returned.')
    } catch (err) {
      setAiError(err instanceof Error ? err.message : 'AI review failed')
    } finally {
      setAiLoading(false)
    }
  }

  if (profileState.loading) return <Skeleton className="h-40 w-full" />
  if (profileState.error) return <ErrorCard message={profileState.error} onRetry={profileState.reload} />
  if (!profile) return null

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'punishments', label: `Punishments (${profile.punishment_history.length})` },
    { id: 'anticheat', label: `Anticheat (${profile.anticheat_history.total_flags})` },
    { id: 'appeals', label: `Appeals (${profile.appeal_history.length})` },
    { id: 'alts', label: `Alts (${profile.alt_accounts.length})` },
  ]

  return (
    <div className="space-y-4">
      <Tabs tabs={tabs} active={tab} onChange={setTab} />

      {tab === 'overview' && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="rounded-lg bg-white/[0.04] p-3 space-y-1">
              <p className="text-slate-500">First Seen</p>
              <p className="text-slate-200">{formatDate(profile.player.first_seen)}</p>
            </div>
            <div className="rounded-lg bg-white/[0.04] p-3 space-y-1">
              <p className="text-slate-500">Last Seen</p>
              <p className="text-slate-200">{formatDate(profile.player.last_seen)}</p>
            </div>
            <div className="rounded-lg bg-white/[0.04] p-3 space-y-1">
              <p className="text-slate-500">Playtime</p>
              <p className="text-slate-200">{formatMinutes(profile.player.playtime)}</p>
            </div>
            <div className="rounded-lg bg-white/[0.04] p-3 space-y-1">
              <p className="text-slate-500">Risk Score</p>
              <p className={profile.player.risk_score > 70 ? 'text-red-400' : 'text-slate-200'}>
                {profile.player.risk_score}
              </p>
            </div>
          </div>
          {profile.verification ? (
            <div className="rounded-lg bg-white/[0.04] p-3 text-xs">
              <p className="text-slate-500 mb-1">Discord Verification</p>
              <p className="text-slate-200">
                {profile.verification.discord_username ?? profile.verification.discord_id}
                {' '}
                <Badge variant={profile.verification.status === 'verified' ? 'success' : 'warning'}>
                  {profile.verification.status}
                </Badge>
              </p>
            </div>
          ) : (
            <div className="text-xs text-slate-500">Not Discord-verified.</div>
          )}
          <div className="flex items-center gap-2 pt-2">
            <Button variant="secondary" loading={aiLoading} onClick={triggerAiReview}>
              <Bot className="h-3.5 w-3.5" />
              AI Review
            </Button>
            {aiError && <span className="text-xs text-red-400">{aiError}</span>}
          </div>
          {aiResult && (
            <Card className="text-xs text-slate-300 whitespace-pre-wrap">{aiResult}</Card>
          )}
        </div>
      )}

      {tab === 'punishments' && (
        <Table>
          <thead>
            <tr>
              <Th>Type</Th>
              <Th>Reason</Th>
              <Th>Date</Th>
              <Th>Active</Th>
            </tr>
          </thead>
          <tbody>
            {profile.punishment_history.length === 0 && (
              <tr>
                <Td className="text-slate-500" colSpan={4}>No punishments.</Td>
              </tr>
            )}
            {profile.punishment_history.map((p) => (
              <tr key={p.id}>
                <Td><Badge variant="warning">{p.type}</Badge></Td>
                <Td>{p.reason}</Td>
                <Td>{formatDate(p.created_at)}</Td>
                <Td><Badge variant={p.active ? 'danger' : 'default'}>{p.active ? 'Active' : 'Revoked'}</Badge></Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {tab === 'anticheat' && (
        <div className="space-y-3">
          <p className="text-xs text-slate-500">
            {profile.anticheat_history.total_flags} flags in last 30 days
          </p>
          {Object.entries(profile.anticheat_history.by_check).map(([check, data]) => (
            <div key={check} className="rounded-lg bg-white/[0.04] p-3 text-xs">
              <p className="font-medium text-slate-200">{check}</p>
              <p className="text-slate-500 mt-0.5">
                Count: {data.count} | Avg VL: {data.avg_vl} | Max VL: {data.max_vl}
              </p>
            </div>
          ))}
          {Object.keys(profile.anticheat_history.by_check).length === 0 && (
            <p className="text-xs text-slate-500">No anticheat flags.</p>
          )}
        </div>
      )}

      {tab === 'appeals' && (
        <Table>
          <thead>
            <tr>
              <Th>Status</Th>
              <Th>Created</Th>
              <Th>Action</Th>
            </tr>
          </thead>
          <tbody>
            {profile.appeal_history.length === 0 && (
              <tr>
                <Td className="text-slate-500" colSpan={3}>No appeals.</Td>
              </tr>
            )}
            {profile.appeal_history.map((a) => (
              <tr key={a.id}>
                <Td><Badge variant="info">{a.status}</Badge></Td>
                <Td>{formatDate(a.created_at)}</Td>
                <Td>{a.action_taken ?? '—'}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {tab === 'alts' && (
        <div className="space-y-2">
          {profile.alt_accounts.length === 0 && (
            <p className="text-xs text-slate-500">No known alt accounts.</p>
          )}
          {profile.alt_accounts.map((alt, i) => (
            <div key={i} className="rounded-lg bg-white/[0.04] p-3 flex items-center justify-between text-xs">
              <span className="text-slate-200">{alt.username ?? alt.uuid}</span>
              <Badge variant={alt.cluster_type === 'confirmed' ? 'danger' : 'warning'}>
                {alt.cluster_type ?? 'suspected'}
              </Badge>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function PlayersPage() {
  const { token } = useAuth()
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [selectedPlayer, setSelectedPlayer] = useState<PlayerSchema | null>(null)

  const fetcher = useCallback(
    () => (token ? players.list(token, { username: debouncedSearch || undefined, limit: 50 }) : Promise.reject(new ApiError(401, 'Not logged in'))),
    [token, debouncedSearch],
  )
  const { data, loading, error, reload } = useFetch<PlayerSchema[]>(fetcher, [debouncedSearch])

  const handleSearch = (v: string) => {
    setSearch(v)
    // simple debounce via state
    setTimeout(() => setDebouncedSearch(v), 400)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-100">Players</h1>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
        <Input
          placeholder="Search by username…"
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {error && <ErrorCard message={error} onRetry={reload} />}

      {loading && (
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-11 w-full" />)}
        </div>
      )}

      {!loading && !error && (data ?? []).length === 0 && (
        <Card className="text-center py-8 text-slate-500 text-sm">
          {debouncedSearch ? `No players matching "${debouncedSearch}".` : 'No players found.'}
        </Card>
      )}

      {!loading && !error && (data ?? []).length > 0 && (
        <div className="rounded-xl border border-white/[0.07] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.06]">
                <th className="px-4 py-2.5 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">Username</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">Risk</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">Suspicion</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-medium text-slate-500 uppercase tracking-wider">Last Seen</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {(data ?? []).map((p) => (
                <tr
                  key={p.uuid}
                  className="border-b border-white/[0.04] hover:bg-white/[0.02] cursor-pointer"
                  onClick={() => setSelectedPlayer(p)}
                >
                  <td className="px-4 py-2.5 flex items-center gap-2">
                    <User className="h-3.5 w-3.5 text-slate-500" />
                    <span className="font-medium text-slate-200 text-xs">{p.username}</span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`text-xs ${p.risk_score > 70 ? 'text-red-400' : 'text-slate-400'}`}>
                      {p.risk_score}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`text-xs ${p.suspicion_score >= 80 ? 'text-amber-400' : 'text-slate-400'}`}>
                      {p.suspicion_score}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-slate-500">{formatDate(p.last_seen)}</td>
                  <td className="px-4 py-2.5 text-slate-500">
                    <ChevronRight className="h-4 w-4" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={selectedPlayer !== null}
        onClose={() => setSelectedPlayer(null)}
        title={`Player: ${selectedPlayer?.username ?? ''}`}
        className="max-w-2xl"
      >
        {selectedPlayer && token && (
          <FullProfile uuid={selectedPlayer.uuid} token={token} username={selectedPlayer.username} />
        )}
      </Modal>
    </div>
  )
}
