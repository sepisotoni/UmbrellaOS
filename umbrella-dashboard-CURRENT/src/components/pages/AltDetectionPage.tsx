import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { alts, FlaggedPlayerSchema, AltGroupSchema } from '../../lib/api'
import { Card, Button, Skeleton, ErrorCard, Badge, Tabs, Table, Th, Td, Input } from '../ui'
import { ShieldCheck } from 'lucide-react'

function FlaggedTab() {
  const { token, user } = useAuth()
  const { data, loading, error, reload } = useFetch<FlaggedPlayerSchema[]>(
    token ? () => alts.flagged(token, { limit: 100 }) : null,
    [token],
  )
  const [marking, setMarking] = useState<string | null>(null)

  const handleFalsePositive = async (uuid: string) => {
    if (!token) return
    setMarking(uuid)
    try {
      await alts.falsePositive(token, {
        player_uuid: uuid,
        reviewed_by: user?.username ?? 'staff',
      })
      reload()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed')
    } finally {
      setMarking(null)
    }
  }

  return (
    <div className="space-y-3">
      {error && <ErrorCard message={error} onRetry={reload} />}
      {loading && <Skeleton className="h-40 w-full" />}
      {!loading && !error && (
        <Table>
          <thead>
            <tr>
              <Th>Username</Th>
              <Th>Suspicion Score</Th>
              <Th>First Seen</Th>
              <Th>{''}</Th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((p) => (
              <tr key={p.uuid} className="border-b border-white/[0.04]">
                <Td className="font-medium text-slate-200">{p.username}</Td>
                <Td>
                  <span className={`font-mono text-xs ${p.suspicion_score >= 90 ? 'text-red-400' : 'text-amber-400'}`}>
                    {p.suspicion_score}
                  </span>
                </Td>
                <Td>{new Date(p.first_seen).toLocaleDateString()}</Td>
                <Td>
                  <Button
                    variant="ghost"
                    className="text-emerald-400 hover:text-emerald-300 py-0.5 px-2"
                    loading={marking === p.uuid}
                    onClick={() => handleFalsePositive(p.uuid)}
                  >
                    <ShieldCheck className="h-3.5 w-3.5" />
                    False Positive
                  </Button>
                </Td>
              </tr>
            ))}
            {(data ?? []).length === 0 && (
              <tr>
                <Td colSpan={4} className="text-center text-slate-500 py-6">
                  No flagged players (suspicion ≥ 80).
                </Td>
              </tr>
            )}
          </tbody>
        </Table>
      )}
    </div>
  )
}

function GroupsTab() {
  const { token } = useAuth()
  const { data, loading, error } = useFetch<AltGroupSchema[]>(
    token ? () => alts.groups(token) : null,
    [token],
  )

  return (
    <div className="space-y-3">
      {error && <ErrorCard message={error} />}
      {loading && <Skeleton className="h-40 w-full" />}
      {!loading && !error && (data ?? []).length === 0 && (
        <Card className="text-center py-8 text-slate-500 text-sm">
          No confirmed alt groups.
        </Card>
      )}
      <div className="space-y-2">
        {(data ?? []).map((g) => (
          <Card key={g.id} className="flex items-center justify-between">
            <div className="text-xs">
              <p className="font-medium text-slate-200">Group #{g.id}</p>
              {g.notes && <p className="text-slate-500 mt-0.5">{g.notes}</p>}
              <p className="text-slate-500">{new Date(g.created_at).toLocaleDateString()}</p>
            </div>
            <Badge variant={g.confirmed ? 'danger' : 'warning'}>
              {g.confirmed ? 'Confirmed' : 'Suspected'}
            </Badge>
          </Card>
        ))}
      </div>
    </div>
  )
}

const TABS = [
  { id: 'flagged', label: 'Flagged Players' },
  { id: 'groups', label: 'Alt Groups' },
]

export function AltDetectionPage() {
  const [tab, setTab] = useState('flagged')
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-100">Alt Detection</h1>
      <Tabs tabs={TABS} active={tab} onChange={setTab} />
      {tab === 'flagged' && <FlaggedTab />}
      {tab === 'groups' && <GroupsTab />}
    </div>
  )
}
