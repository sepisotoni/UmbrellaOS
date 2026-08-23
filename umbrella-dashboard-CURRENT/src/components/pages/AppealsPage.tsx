import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { appeals, aiTasks, AppealSchema } from '../../lib/api'
import {
  Card, Button, Textarea, Input, Skeleton, ErrorCard, Badge, Modal, Select,
} from '../ui'
import { Bot, CheckCircle2, Clock, AlertOctagon, XCircle, ChevronsUp } from 'lucide-react'

const STATUS_VARIANT: Record<string, 'success' | 'danger' | 'warning' | 'info' | 'default'> = {
  pending: 'warning',
  ACCEPTED: 'success',
  REJECTED: 'danger',
  ESCALATED: 'info',
  REVIEW_SCHEDULED: 'info',
  REDUCED: 'purple' as 'warning',
}

function formatDate(d: string) { return new Date(d).toLocaleString() }

const ACTIONS = [
  { id: 'ACCEPT', label: 'Accept', icon: CheckCircle2, variant: 'success' as const },
  { id: 'REDUCE_SENTENCE', label: 'Reduce Sentence', icon: Clock, variant: 'warning' as const },
  { id: 'SCHEDULE_REVIEW', label: 'Schedule Review', icon: Clock, variant: 'info' as const },
  { id: 'ESCALATE', label: 'Escalate', icon: ChevronsUp, variant: 'info' as const },
  { id: 'REJECT', label: 'Reject', icon: XCircle, variant: 'danger' as const },
]

interface AppealDetailProps {
  appeal: AppealSchema
  token: string
  onClosed: () => void
}

function AppealDetail({ appeal, token, onClosed }: AppealDetailProps) {
  const { user } = useAuth()
  const [action, setAction] = useState('')
  const [staffNote, setStaffNote] = useState('')
  const [newExpiry, setNewExpiry] = useState('')
  const [closing, setClosing] = useState(false)
  const [closeError, setCloseError] = useState<string | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)
  const [aiSummary, setAiSummary] = useState<string | null>(null)

  const isClosed = !!appeal.action_taken

  const handleAiReview = async () => {
    setAiLoading(true)
    setAiError(null)
    try {
      const result = await aiTasks.reviewAppeal(token, appeal.id)
      setAiSummary(result.ai_summary ?? 'Review complete.')
    } catch (err) {
      setAiError(err instanceof Error ? err.message : 'AI review failed')
    } finally {
      setAiLoading(false)
    }
  }

  const handleClose = async () => {
    if (!action) return
    setClosing(true)
    setCloseError(null)
    try {
      await appeals.close(token, appeal.id, {
        action,
        staff_note: staffNote || undefined,
        new_expiry: action === 'REDUCE_SENTENCE' ? newExpiry : undefined,
      })
      onClosed()
    } catch (err) {
      setCloseError(err instanceof Error ? err.message : 'Failed to close appeal')
    } finally {
      setClosing(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      {isClosed && (
        <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 px-4 py-2.5 text-xs text-emerald-300 font-medium">
          Closed: {appeal.action_taken} by {appeal.handled_by}
        </div>
      )}

      <div className="text-xs space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="text-slate-500">Status:</span>
          <Badge variant={STATUS_VARIANT[appeal.status] ?? 'default'}>{appeal.status}</Badge>
        </div>
        <div>
          <span className="text-slate-500">Player UUID: </span>
          <span className="font-mono text-slate-300">{appeal.player_uuid}</span>
        </div>
        <div>
          <span className="text-slate-500">Punishment ID: </span>
          <span className="font-mono text-slate-300">{appeal.punishment_id}</span>
        </div>
        <div>
          <span className="text-slate-500">Submitted: </span>
          <span className="text-slate-300">{formatDate(appeal.created_at)}</span>
        </div>
      </div>

      <div className="rounded-lg bg-white/[0.04] p-3 text-xs text-slate-300 whitespace-pre-wrap">
        {appeal.message}
      </div>

      {/* AI Review button */}
      {!isClosed && (
        <div className="flex items-center gap-2">
          <Button variant="secondary" loading={aiLoading} onClick={handleAiReview}>
            <Bot className="h-3.5 w-3.5" /> AI Review
          </Button>
          {aiError && <span className="text-xs text-red-400">{aiError}</span>}
        </div>
      )}
      {aiSummary && (
        <Card className="text-xs text-slate-300 whitespace-pre-wrap">{aiSummary}</Card>
      )}
      {appeal.case_summary && (
        <Card className="text-xs text-slate-400 whitespace-pre-wrap">{appeal.case_summary}</Card>
      )}

      {/* Action buttons */}
      {!isClosed && (
        <div className="space-y-3 pt-2 border-t border-white/[0.07]">
          <p className="text-[11px] text-slate-500 uppercase tracking-wider">Staff Decision</p>
          <div className="flex flex-wrap gap-2">
            {ACTIONS.map((a) => (
              <button
                key={a.id}
                onClick={() => setAction(a.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                  action === a.id
                    ? a.variant === 'success'
                      ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300'
                      : a.variant === 'danger'
                      ? 'bg-red-500/20 border-red-500/50 text-red-300'
                      : a.variant === 'warning'
                      ? 'bg-amber-500/20 border-amber-500/50 text-amber-300'
                      : 'bg-sky-500/20 border-sky-500/50 text-sky-300'
                    : 'bg-white/[0.04] border-white/[0.08] text-slate-400 hover:text-slate-200'
                }`}
              >
                <a.icon className="h-3.5 w-3.5" />
                {a.label}
              </button>
            ))}
          </div>

          {action === 'REDUCE_SENTENCE' && (
            <div>
              <label className="text-[11px] text-slate-500 mb-1 block">New Expiry Date *</label>
              <Input type="datetime-local" value={newExpiry} onChange={(e) => setNewExpiry(e.target.value)} />
            </div>
          )}
          <div>
            <label className="text-[11px] text-slate-500 mb-1 block">Staff Note (optional)</label>
            <Textarea
              value={staffNote}
              onChange={(e) => setStaffNote(e.target.value)}
              rows={2}
              placeholder="Optional note…"
            />
          </div>
          {closeError && <div className="text-xs text-red-400">{closeError}</div>}
          <Button variant="primary" loading={closing} disabled={!action} onClick={handleClose}>
            Confirm Decision
          </Button>
        </div>
      )}
    </div>
  )
}

export function AppealsPage() {
  const { token } = useAuth()
  const [selectedAppeal, setSelectedAppeal] = useState<AppealSchema | null>(null)
  const [statusFilter, setStatusFilter] = useState('')

  const { data, loading, error, reload } = useFetch<AppealSchema[]>(
    token ? () => appeals.list(token, { status: statusFilter || undefined, limit: 100 }) : null,
    [token, statusFilter],
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-100">Appeals</h1>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="ACCEPTED">Accepted</option>
          <option value="REJECTED">Rejected</option>
          <option value="ESCALATED">Escalated</option>
          <option value="REVIEW_SCHEDULED">Scheduled</option>
        </Select>
      </div>

      {error && <ErrorCard message={error} onRetry={reload} />}
      {loading && <Skeleton className="h-40 w-full" />}

      {!loading && !error && (data ?? []).length === 0 && (
        <Card className="text-center py-8 text-slate-500 text-sm">No appeals found.</Card>
      )}

      <div className="space-y-2">
        {(data ?? []).map((a) => (
          <div
            key={a.id}
            className="rounded-xl border border-white/[0.07] bg-white/[0.03] px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-white/[0.05] transition-colors"
            onClick={() => setSelectedAppeal(a)}
          >
            <div className="flex items-center gap-3 min-w-0">
              <AlertOctagon className="h-4 w-4 text-slate-500 shrink-0" />
              <div className="min-w-0">
                <p className="text-xs font-medium text-slate-200 truncate">
                  Appeal #{a.id.slice(0, 8)}
                </p>
                <p className="text-[11px] text-slate-500 truncate">{a.message.slice(0, 80)}</p>
              </div>
            </div>
            <Badge variant={STATUS_VARIANT[a.status] ?? 'default'}>{a.status}</Badge>
          </div>
        ))}
      </div>

      <Modal
        open={selectedAppeal !== null}
        onClose={() => setSelectedAppeal(null)}
        title={`Appeal #${selectedAppeal?.id.slice(0, 8) ?? ''}`}
        className="max-w-xl"
      >
        {selectedAppeal && token && (
          <AppealDetail
            appeal={selectedAppeal}
            token={token}
            onClosed={() => {
              setSelectedAppeal(null)
              reload()
            }}
          />
        )}
      </Modal>
    </div>
  )
}
