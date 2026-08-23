import { useState } from 'react'
import { Megaphone, Send, X } from 'lucide-react'
import { getBaseUrl } from '../../lib/api'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../ui/Toast'

const PRESET_ANNOUNCEMENTS = [
  '⚠️ Server maintenance in 15 minutes! Please finish your games and save items.',
  '🎉 Double XP & Drops event is now active across all game nodes!',
  '🛡️ Network security update applied. Enjoy smooth 20.0 TPS gameplay.',
  '⚡ New Anarchy Season 2 raid event starting at the Nether spawn!',
]

const SCOPES = [
  { value: 'all', label: 'All Network Nodes' },
  { value: 'game', label: 'Game Nodes Only (Survival/Skyblock/Bedwars)' },
  { value: 'proxy', label: 'Proxies Only' },
]

interface BroadcastModalProps {
  open: boolean
  onClose: () => void
}

export function BroadcastModal({ open, onClose }: BroadcastModalProps) {
  const { token } = useAuth()
  const { addToast } = useToast()
  const [message, setMessage] = useState('')
  const [scope, setScope] = useState('all')
  const [bigTitle, setBigTitle] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  if (!open) return null

  const handleSubmit = async () => {
    if (!message.trim()) {
      addToast('warning', 'Empty Message', 'Please enter a message to broadcast.')
      return
    }
    setSubmitting(true)
    try {
      const res = await fetch(`${getBaseUrl()}/api/v1/bridge/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message: message.trim(), scope, source: 'DASHBOARD', big_title: bigTitle }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error((data as { detail?: string }).detail ?? `HTTP ${res.status}`)
      }
      addToast('success', 'Broadcast Sent', 'Message dispatched to network')
      setMessage('')
      onClose()
    } catch (err) {
      addToast('error', 'Broadcast Failed', err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-[#0f131a] shadow-2xl">
        {/* Header */}
        <div className="flex items-start gap-3 p-5 border-b border-slate-800">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-cyan-900/60 border border-cyan-500/40">
            <Megaphone className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-bold text-white">Global Network Broadcast</h2>
            <p className="text-[11px] text-slate-400 mt-0.5">Dispatch live titles, chat notices, and audio cues</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {/* Message */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1.5">Broadcast Message</label>
            <textarea
              rows={3}
              className="w-full rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 resize-none"
              placeholder="Type your message here..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
          </div>

          {/* Preset announcements */}
          <div>
            <p className="text-[11px] font-medium text-slate-400 mb-2">Preset Announcements</p>
            <div className="space-y-1.5">
              {PRESET_ANNOUNCEMENTS.map((preset) => (
                <button
                  key={preset}
                  onClick={() => setMessage(preset)}
                  className="w-full text-left px-3 py-2 rounded-lg border border-slate-700/60 bg-slate-800/40 text-[11px] text-slate-400 hover:text-slate-200 hover:border-cyan-500/30 hover:bg-cyan-950/20 transition-colors"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>

          {/* Scope + big title */}
          <div className="grid grid-cols-2 gap-3 items-end">
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1.5">Target Scope</label>
              <select
                className="w-full rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                value={scope}
                onChange={(e) => setScope(e.target.value)}
              >
                {SCOPES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-2 cursor-pointer pb-2">
              <input
                type="checkbox"
                checked={bigTitle}
                onChange={(e) => setBigTitle(e.target.checked)}
                className="rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500/30"
              />
              <span className="text-[11px] text-slate-300">Flash on screen as Big Title</span>
            </label>
          </div>
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
            className="flex items-center gap-2 px-4 py-2 text-xs rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="h-3.5 w-3.5" />
            {submitting ? 'Sending...' : 'Send Broadcast'}
          </button>
        </div>
      </div>
    </div>
  )
}
