import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { audit, AuditResponse } from '../../lib/api'
import { Card, Button, Select, Skeleton, ErrorCard, Badge, Table, Th, Td } from '../ui'
import { ChevronLeft, ChevronRight } from 'lucide-react'

const ACTOR_TYPE_VARIANT: Record<string, 'success' | 'info' | 'warning' | 'default' | 'purple'> = {
  staff: 'purple',
  plugin: 'success',
  bot: 'info',
  system: 'default',
  ai: 'warning',
}

const PAGE_SIZE = 50

export function AuditPage() {
  const { token } = useAuth()
  const [actorTypeFilter, setActorTypeFilter] = useState('')
  const [offset, setOffset] = useState(0)

  const { data, loading, error, reload } = useFetch<AuditResponse>(
    token
      ? () => audit.list(token, {
          limit: PAGE_SIZE,
          offset,
          actor_type: actorTypeFilter || undefined,
        })
      : null,
    [token, actorTypeFilter, offset],
  )

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const hasPrev = offset > 0
  const hasNext = offset + PAGE_SIZE < total

  const formatDetails = (json: string | null) => {
    if (!json) return '—'
    try {
      const obj = JSON.parse(json)
      return JSON.stringify(obj, null, 0).slice(0, 120)
    } catch {
      return json.slice(0, 120)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Audit Log</h1>
          {data && <p className="text-xs text-slate-500 mt-0.5">{total.toLocaleString()} total entries</p>}
        </div>
        <Select value={actorTypeFilter} onChange={(e) => { setActorTypeFilter(e.target.value); setOffset(0) }}>
          <option value="">All actor types</option>
          <option value="staff">Staff</option>
          <option value="plugin">Plugin</option>
          <option value="bot">Bot</option>
          <option value="system">System</option>
          <option value="ai">AI</option>
        </Select>
      </div>

      {error && <ErrorCard message={error} onRetry={reload} />}
      {loading && <Skeleton className="h-60 w-full" />}

      {!loading && !error && (
        <>
          <Table>
            <thead>
              <tr>
                <Th>Time</Th>
                <Th>Actor</Th>
                <Th>Type</Th>
                <Th>Action</Th>
                <Th>Target</Th>
                <Th>Details</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.id} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                  <Td className="whitespace-nowrap text-[10px] font-mono text-slate-500">
                    {new Date(e.created_at).toLocaleString()}
                  </Td>
                  <Td className="font-medium text-slate-200">{e.actor}</Td>
                  <Td>
                    <Badge variant={ACTOR_TYPE_VARIANT[e.actor_type] ?? 'default'}>
                      {e.actor_type}
                    </Badge>
                  </Td>
                  <Td className="font-mono text-[11px] text-violet-300">{e.action}</Td>
                  <Td className="font-mono text-[10px] text-slate-400">{e.target ?? '—'}</Td>
                  <Td className="font-mono text-[10px] text-slate-500 max-w-xs truncate">
                    {formatDetails(e.details_json)}
                  </Td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <Td colSpan={6} className="text-center text-slate-500 py-8">No audit entries found.</Td>
                </tr>
              )}
            </tbody>
          </Table>

          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">
              {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={!hasPrev} onClick={() => setOffset((o) => o - PAGE_SIZE)}>
                <ChevronLeft className="h-3.5 w-3.5" /> Prev
              </Button>
              <Button variant="secondary" disabled={!hasNext} onClick={() => setOffset((o) => o + PAGE_SIZE)}>
                Next <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
