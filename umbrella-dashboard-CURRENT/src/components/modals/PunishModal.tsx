import { useState, useEffect } from 'react'
import { ShieldAlert, AlertTriangle, X } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { punishments, dashboard, ServerRecord } from '../../lib/api'
import { useToast } from '../ui/Toast'

const ACTION_TYPES = [
  { value: 'TEMP_BAN', label: 'Temporary Ban' },
  { value: 'PERM_BAN', label: 'Permanent Ban' },
  { value: 'HWID_BAN', label: 'Hardware HWID Ban' },
  { value: 'TEMP_MUTE', label: 'Temporary Mute' },
  { value: 'PERM_MUTE', label: 'Permanent Mute' },
  { value: 'KICK', label: 'Kick Player' },
  { value: 'WARN', label: 'Formal Warning' },
]

const DURATIONS = [
  { value: '1d', label: '1 Day (24 Hours)' },
  { value: '7d', label: '7 Days (1 Week)' },
  { value: '30d', label: '30 Days (1 Month)' },
  { value: '90d', label: '90 Days (3 Months)' },
]

const REASON_PRESETS = [
  'GrimAC Flag: Reach & Hitbox Expansion',
  'KillAura & AutoClicker (Unfair Advantages)',
  'Fly / Speed / Movement Exploit',
  'Severe Chat Toxicity / Hate Speech',
  'Multi-Account Ban Evasion',
  'Duplication Exploit',
  'Malicious Lag Machine',
]

const DURATION_NEEDS = ['TEMP_BAN', 'TEMP_MUTE']

function durationToExpires(duration: string): string {
  const now = new Date()
  const map: Record<string, number> = { '1d': 1, '7d': 7, '30d': 30, '90d': 90 }
  const days = map[duration] ?? 1
  now.setDate(now.getDate() + days)
  return now.toISOString()
}

interface PunishModalProps {
  open: boolean
  onClose: () => void
  prefillUsername?: string | null
}

export function PunishModal({ open, onClose, prefillUsername }: PunishModalProps) {
  const { token, user } = useAuth()
  const { addToast } = useToast()
  const [servers, setServers] = useState<ServerRecord[]>([])

  const [form, setForm] = useState({
    username: prefillUsername ?? '',
    actionType: 'TEMP_BAN',
    duration: '7d',
    scope: 'global',
    reason: '',
    evidence: '',
    ipBan: false,
  })
  const [submitting, setSubmitting] = useState(false)

  // Refresh prefill if prop changes
  useEffect(() => {
    if (prefillUsername) setForm((f) => ({ ...f, username: prefillUsername }))
  }, [prefillUsername])

  // Fetch servers for scope select
  useEffect(() => {
    if (!open || !token) return
    dashboard.servers(token).then(setServers).catch(() => {})
  }, [open, token])

  if (!open) return null

  const needsDuration = DURATION_NEEDS.includes(form.actionType)

  const handleSubmit = async () => {
    if (!token) return
    if (!form.username.trim() || !form.reason.trim()) {
      addToast('warning', 'Missing Fields', 'Player username and reason are required.')
      return
    }
    setSubmitting(true)
    try {
      await punishments.create(token, {
        player_uuid: form.username.trim(),
        type: form.actionType,
        reason: form.reason,
        staff_id: user?.id,
        ...(needsDuration ? { expires_at: durationToExpires(form.duration) } : {}),
      })
      const typeLabel = ACTION_TYPES.find((a) => a.value === form.actionType)?.label ?? form.actionType
      addToast('success', 'Punishment Issued', `${typeLabel} applied to ${form.username}`)
      onClose()
    } catch (err) {
      addToast('error', 'Failed', err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-[#0f131a] shadow-2xl">
        {/* Header */}
        <div className="flex items-start gap-3 p-5 border-b border-slate-800">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-rose-900/60 border border-rose-500/40">
            <ShieldAlert className="h-4 w-4 text-rose-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-bold text-white">Issue Punishment / Enforcement</h2>
            <p className="text-[11px] text-slate-400 mt-0.5">Synchronized across Velocity Proxies and Game Nodes</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {/* Player username */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1.5">Player Username / UUID</label>
            <input
              className="w-full rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-rose-500/50"
              placeholder="e.g. VoidReaper_X"
              value={form.username}
              onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
            />
          </div>

          {/* Action type + Duration */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1.5">Action Type</label>
              <select
                className="w-full rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-rose-500/50"
                value={form.actionType}
                onChange={(e) => setForm((f) => ({ ...f, actionType: e.target.value }))}
              >
                {ACTION_TYPES.map((a) => (
                  <option key={a.value} value={a.value}>{a.label}</option>
                ))}
              </select>
            </div>
            {needsDuration && (
              <div>
                <label className="block text-[11px] font-medium text-slate-400 mb-1.5">Duration</label>
                <select
                  className="w-full rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-rose-500/50"
                  value={form.duration}
                  onChange={(e) => setForm((f) => ({ ...f, duration: e.target.value }))}
                >
                  {DURATIONS.map((d) => (
                    <option key={d.value} value={d.value}>{d.label}</option>
                  ))}
                </select>
              </div>
            )}
            {!needsDuration && <div />}
          </div>

          {/* Server scope */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1.5">Server Scope</label>
            <select
              className="w-full rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-rose-500/50"
              value={form.scope}
              onChange={(e) => setForm((f) => ({ ...f, scope: e.target.value }))}
            >
              <option value="global">Network-Wide (Global Across All Instances)</option>
              {servers.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>

          {/* Reason */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1.5">Reason</label>
            <input
              className="w-full rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-rose-500/50"
              placeholder="Describe the violation..."
              value={form.reason}
              onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
            />
            <div className="flex flex-wrap gap-1.5 mt-2">
              {REASON_PRESETS.map((preset) => (
                <button
                  key={preset}
                  onClick={() => setForm((f) => ({ ...f, reason: preset }))}
                  className="px-2 py-0.5 rounded-md border border-slate-700 bg-slate-800/60 text-[10px] text-slate-400 hover:text-slate-200 hover:border-slate-600 transition-colors font-mono"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>

          {/* Evidence URL */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1.5">Evidence URL</label>
            <input
              className="w-full rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-rose-500/50"
              placeholder="https://grim.umbrella-mc.net/logs/... or video url"
              value={form.evidence}
              onChange={(e) => setForm((f) => ({ ...f, evidence: e.target.value }))}
            />
          </div>

          {/* IP Ban checkbox */}
          <label className="flex items-center gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={form.ipBan}
              onChange={(e) => setForm((f) => ({ ...f, ipBan: e.target.checked }))}
              className="rounded border-slate-600 bg-slate-800 text-rose-500 focus:ring-rose-500/30"
            />
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
            <span className="text-[11px] text-slate-300">Also blacklist player's current IP address</span>
          </label>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2.5 px-5 py-4 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs rounded-lg border border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex items-center gap-2 px-4 py-2 text-xs rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ShieldAlert className="h-3.5 w-3.5" />
            {submitting ? 'Enforcing...' : 'Confirm & Enforce'}
          </button>
        </div>
      </div>
    </div>
  )
}
