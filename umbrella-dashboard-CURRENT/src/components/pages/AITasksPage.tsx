import { useState, useRef } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { aiTasks, ai, dashboard, AITaskRecord, ServerRecord } from '../../lib/api'
import {
  Card, Button, Input, Textarea, Skeleton, ErrorCard, Badge, Tabs, Table, Th, Td, Select,
} from '../ui'
import { Bot, Send, AlertTriangle } from 'lucide-react'

// ── AI Tasks tab ─────────────────────────────────────────────────────────────

function TasksTab() {
  const { token, user } = useAuth()
  const [statusFilter, setStatusFilter] = useState('')
  const [actingOn, setActingOn] = useState<number | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const { data, loading, error, reload } = useFetch<AITaskRecord[]>(
    token ? () => aiTasks.list(token, { status: statusFilter || undefined, limit: 100 }) : null,
    [token, statusFilter],
  )

  const handleApprove = async (taskId: number) => {
    if (!token) return
    setActingOn(taskId)
    setActionError(null)
    try {
      await aiTasks.approve(token, taskId, {
        action_taken: 'approved',
        reviewed_by: user?.username ?? 'staff',
      })
      reload()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Approve failed')
    } finally {
      setActingOn(null)
    }
  }

  const handleDeny = async (taskId: number) => {
    if (!token) return
    setActingOn(taskId)
    setActionError(null)
    try {
      await aiTasks.deny(token, taskId, { reviewed_by: user?.username ?? 'staff' })
      reload()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Deny failed')
    } finally {
      setActingOn(null)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="denied">Denied</option>
        </Select>
      </div>

      {actionError && <ErrorCard message={actionError} />}
      {error && <ErrorCard message={error} onRetry={reload} />}
      {loading && <Skeleton className="h-40 w-full" />}

      {!loading && !error && (
        <Table>
          <thead>
            <tr>
              <Th>ID</Th>
              <Th>Type</Th>
              <Th>Status</Th>
              <Th>Summary</Th>
              <Th>Confidence</Th>
              <Th>Actions</Th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((t) => (
              <tr key={t.id} className="border-b border-white/[0.04]">
                <Td className="font-mono">#{t.id}</Td>
                <Td><Badge variant="purple">{t.task_type}</Badge></Td>
                <Td>
                  <Badge
                    variant={
                      t.status === 'approved' ? 'success' :
                      t.status === 'denied' ? 'danger' :
                      t.status === 'pending' ? 'warning' : 'default'
                    }
                  >
                    {t.status}
                  </Badge>
                </Td>
                <Td className="max-w-xs truncate text-slate-400">{t.ai_summary ?? '—'}</Td>
                <Td className="font-mono">
                  {t.ai_confidence !== null ? `${(t.ai_confidence * 100).toFixed(0)}%` : '—'}
                </Td>
                <Td>
                  {t.status === 'pending' && (
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        className="text-emerald-400 py-0.5 px-2 text-xs"
                        loading={actingOn === t.id}
                        onClick={() => handleApprove(t.id)}
                      >
                        Approve
                      </Button>
                      <Button
                        variant="ghost"
                        className="text-red-400 py-0.5 px-2 text-xs"
                        loading={actingOn === t.id}
                        onClick={() => handleDeny(t.id)}
                      >
                        Deny
                      </Button>
                    </div>
                  )}
                </Td>
              </tr>
            ))}
            {(data ?? []).length === 0 && (
              <tr>
                <Td colSpan={6} className="text-center text-slate-500 py-6">No AI tasks found.</Td>
              </tr>
            )}
          </tbody>
        </Table>
      )}
    </div>
  )
}

// ── Copilot chat tab ──────────────────────────────────────────────────────────

interface ChatMessage { role: 'user' | 'assistant'; text: string }

function CopilotTab() {
  const { token } = useAuth()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const send = async () => {
    if (!input.trim() || !token) return
    const userMsg = input.trim()
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: userMsg }])
    setSending(true)
    setSendError(null)
    try {
      const res = await ai.copilot(token, { message: userMsg })
      setMessages((m) => [...m, { role: 'assistant', text: res.response }])
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    } catch (err) {
      setSendError(err instanceof Error ? err.message : 'Copilot unavailable')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="space-y-4 flex flex-col h-full">
      <div className="flex-1 min-h-[300px] rounded-xl border border-white/[0.07] bg-white/[0.02] p-4 overflow-y-auto space-y-3">
        {messages.length === 0 && (
          <p className="text-xs text-slate-500 text-center py-4">
            Ask the UmbrellaOS Copilot anything about your server network.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`rounded-xl px-4 py-2.5 text-xs whitespace-pre-wrap max-w-[85%] ${
              m.role === 'user'
                ? 'bg-violet-600/20 text-violet-200 ml-auto'
                : 'bg-white/[0.06] text-slate-200'
            }`}
          >
            {m.text}
          </div>
        ))}
        {sending && (
          <div className="rounded-xl px-4 py-2.5 text-xs bg-white/[0.06] text-slate-400 animate-pulse w-24">
            Thinking…
          </div>
        )}
        {sendError && <ErrorCard message={sendError} />}
        <div ref={bottomRef} />
      </div>
      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask the copilot…"
          disabled={sending}
        />
        <Button variant="primary" loading={sending} disabled={!input.trim()} onClick={send}>
          <Send className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}

// ── Crash Risk tab ────────────────────────────────────────────────────────────

// Real risk levels from crash_prevention.py CrashRiskLevel enum
const RISK_VARIANT: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
  NONE: 'success',
  WATCH: 'warning',
  CRITICAL: 'danger',
  INSUFFICIENT_DATA: 'default',
}

function CrashRiskTab() {
  const { token } = useAuth()
  const { data: servers, loading: sLoading } = useFetch<ServerRecord[]>(
    token ? () => dashboard.servers(token) : null,
    [token],
  )
  const [selected, setSelected] = useState<string>('')
  const [risk, setRisk] = useState<{ risk_level: string; recommendation: string; tps_trend: number | null } | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const assess = async () => {
    if (!token || !selected) return
    setLoading(true)
    setErr(null)
    try {
      const r = await ai.crashRisk(token, selected)
      setRisk(r)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Assessment failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        Crash risk is assessed on-demand from recent TPS telemetry. Click Assess to run.
      </p>
      <div className="flex items-center gap-3">
        {sLoading ? (
          <Skeleton className="h-9 w-48" />
        ) : (
          <Select value={selected} onChange={(e) => setSelected(e.target.value)}>
            <option value="">Select a server…</option>
            {(servers ?? []).map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </Select>
        )}
        <Button variant="primary" loading={loading} disabled={!selected} onClick={assess}>
          <AlertTriangle className="h-3.5 w-3.5" /> Assess
        </Button>
      </div>

      {err && <ErrorCard message={err} />}

      {risk && (
        <Card className="space-y-3">
          <div className="flex items-center gap-3">
            <Badge variant={RISK_VARIANT[risk.risk_level] ?? 'default'} className="text-sm px-3 py-1">
              {risk.risk_level}
            </Badge>
            {risk.tps_trend !== null && (
              <span className="text-xs text-slate-500">
                TPS trend: {risk.tps_trend > 0 ? '+' : ''}{risk.tps_trend?.toFixed(2)}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-300">{risk.recommendation}</p>
        </Card>
      )}
    </div>
  )
}

const TABS = [
  { id: 'tasks', label: 'AI Task Queue' },
  { id: 'copilot', label: 'Copilot Chat' },
  { id: 'crash-risk', label: 'Crash Risk' },
]

export function AITasksPage() {
  const [tab, setTab] = useState('tasks')
  return (
    <div className="space-y-4 flex flex-col">
      <h1 className="text-lg font-semibold text-slate-100">AI Tasks</h1>
      <Tabs tabs={TABS} active={tab} onChange={setTab} />
      {tab === 'tasks' && <TasksTab />}
      {tab === 'copilot' && <CopilotTab />}
      {tab === 'crash-risk' && <CrashRiskTab />}
    </div>
  )
}
