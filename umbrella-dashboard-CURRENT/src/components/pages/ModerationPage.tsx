import { useState, useCallback } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { punishments, anticheat, PunishmentSchema, ViolationRecord } from '../../lib/api'
import { ApiError } from '../../lib/api'
import {
  Card, Button, Input, Textarea, Select, Skeleton, ErrorCard, Badge, Modal, Tabs, Table, Th, Td,
} from '../ui'
import { Plus, ShieldOff, ShieldAlert } from 'lucide-react'

function formatDate(d: string) {
  return new Date(d).toLocaleString()
}

function PunishmentsTab({ onOpenPunish }: { onOpenPunish?: (username?: string) => void }) {
  const { token, user } = useAuth()
  const [showNew, setShowNew] = useState(false)
  const [revoking, setRevoking] = useState<string | null>(null)
  const [newForm, setNewForm] = useState({ player_uuid: '', type: 'ban', reason: '', expires_at: '' })
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const { data, loading, error, reload } = useFetch<PunishmentSchema[]>(
    token ? () => punishments.list(token, { active_only: false, limit: 100 }) : null,
    [token],
  )

  const handleRevoke = async (id: string) => {
    if (!token) return
    setRevoking(id)
    try {
      await punishments.revoke(token, id)
      reload()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Revoke failed')
    } finally {
      setRevoking(null)
    }
  }

  const handleCreate = async () => {
    if (!token) return
    setSaving(true)
    setSaveError(null)
    try {
      await punishments.create(token, {
        player_uuid: newForm.player_uuid,
        type: newForm.type,
        reason: newForm.reason,
        staff_id: user?.id,
        ...(newForm.expires_at ? { expires_at: newForm.expires_at } : {}),
      })
      setShowNew(false)
      setNewForm({ player_uuid: '', type: 'ban', reason: '', expires_at: '' })
      reload()
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to create punishment')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">{(data ?? []).length} punishments loaded</span>
        <div className="flex items-center gap-2">
          <Button variant="primary" onClick={() => setShowNew(true)}>
            <Plus className="h-3.5 w-3.5" /> New Punishment
          </Button>
          {onOpenPunish && (
            <Button variant="primary" onClick={() => onOpenPunish()}>
              <ShieldAlert className="h-3.5 w-3.5" /> Issue New Punishment
            </Button>
          )}
        </div>
      </div>

      {error && <ErrorCard message={error} onRetry={reload} />}
      {loading && <Skeleton className="h-40 w-full" />}

      {!loading && !error && (
        <div className="rounded-xl border border-white/[0.07] overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/[0.06]">
                <Th>Player UUID</Th>
                <Th>Type</Th>
                <Th>Reason</Th>
                <Th>Created</Th>
                <Th>Status</Th>
                <Th>{''}</Th>
              </tr>
            </thead>
            <tbody>
              {(data ?? []).map((p) => (
                <tr key={p.id} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                  <Td className="font-mono text-[10px]">{p.player_uuid.slice(0, 8)}…</Td>
                  <Td><Badge variant="warning">{p.type}</Badge></Td>
                  <Td className="max-w-xs truncate">{p.reason}</Td>
                  <Td>{formatDate(p.created_at)}</Td>
                  <Td>
                    <Badge variant={p.active ? 'danger' : 'default'}>
                      {p.active ? 'Active' : 'Revoked'}
                    </Badge>
                  </Td>
                  <Td>
                    <div className="flex items-center gap-1">
                      {onOpenPunish && (
                        <Button
                          variant="ghost"
                          className="py-0.5 px-2 text-rose-400 hover:text-rose-300"
                          onClick={() => onOpenPunish(p.player_uuid)}
                        >
                          <ShieldAlert className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      {p.active && (
                        <Button
                          variant="ghost"
                          className="py-0.5 px-2 text-red-400 hover:text-red-300"
                          loading={revoking === p.id}
                          onClick={() => handleRevoke(p.id)}
                        >
                          <ShieldOff className="h-3.5 w-3.5" />
                          Revoke
                        </Button>
                      )}
                    </div>
                  </Td>
                </tr>
              ))}
              {(data ?? []).length === 0 && (
                <tr>
                  <Td colSpan={6} className="text-center text-slate-500 py-6">No punishments found.</Td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={showNew} onClose={() => setShowNew(false)} title="New Punishment">
        <div className="space-y-3">
          {saveError && <ErrorCard message={saveError} />}
          <div>
            <label className="text-[11px] text-slate-500 mb-1 block">Player UUID</label>
            <Input
              value={newForm.player_uuid}
              onChange={(e) => setNewForm((f) => ({ ...f, player_uuid: e.target.value }))}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            />
          </div>
          <div>
            <label className="text-[11px] text-slate-500 mb-1 block">Type</label>
            <Select
              value={newForm.type}
              onChange={(e) => setNewForm((f) => ({ ...f, type: e.target.value }))}
              className="w-full"
            >
              <option value="ban">Ban</option>
              <option value="tempban">Temp Ban</option>
              <option value="mute">Mute</option>
              <option value="warn">Warn</option>
            </Select>
          </div>
          <div>
            <label className="text-[11px] text-slate-500 mb-1 block">Reason</label>
            <Textarea
              value={newForm.reason}
              onChange={(e) => setNewForm((f) => ({ ...f, reason: e.target.value }))}
              rows={3}
              placeholder="Reason for punishment…"
            />
          </div>
          <div>
            <label className="text-[11px] text-slate-500 mb-1 block">Expires At (optional)</label>
            <Input
              type="datetime-local"
              value={newForm.expires_at}
              onChange={(e) => setNewForm((f) => ({ ...f, expires_at: e.target.value }))}
            />
          </div>
          <div className="flex gap-2 pt-2">
            <Button variant="primary" loading={saving} onClick={handleCreate}>
              Create
            </Button>
            <Button variant="secondary" onClick={() => setShowNew(false)}>
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

function GrimACTab() {
  const { token } = useAuth()
  const { data, loading, error, reload } = useFetch<ViolationRecord[]>(
    token ? () => anticheat.violations(token, { limit: 100 }) : null,
    [token],
  )
  return (
    <div className="space-y-4">
      {error && <ErrorCard message={error} onRetry={reload} />}
      {loading && <Skeleton className="h-40 w-full" />}
      {!loading && !error && (
        <Table>
          <thead>
            <tr>
              <Th>Player</Th>
              <Th>Check</Th>
              <Th>VL</Th>
              <Th>Server</Th>
              <Th>Time</Th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((v) => (
              <tr key={v.id} className="border-b border-white/[0.04]">
                <Td className="font-medium">{v.player_name}</Td>
                <Td><Badge variant="warning">{v.check_name}</Badge></Td>
                <Td className={`font-mono ${v.vl > 50 ? 'text-red-400' : 'text-amber-400'}`}>{v.vl}</Td>
                <Td>{v.server_id ?? '—'}</Td>
                <Td>{formatDate(v.created_at)}</Td>
              </tr>
            ))}
            {(data ?? []).length === 0 && (
              <tr>
                <Td colSpan={5} className="text-center text-slate-500 py-6">No violations recorded.</Td>
              </tr>
            )}
          </tbody>
        </Table>
      )}
    </div>
  )
}

const TABS = [
  { id: 'punishments', label: 'Punishments' },
  { id: 'grimac', label: 'GrimAC Violations' },
]

export function ModerationPage({ onOpenPunish }: { onOpenPunish?: (username?: string) => void }) {
  const [tab, setTab] = useState('punishments')
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-100">Moderation</h1>
      <Tabs tabs={TABS} active={tab} onChange={setTab} />
      {tab === 'punishments' && <PunishmentsTab onOpenPunish={onOpenPunish} />}
      {tab === 'grimac' && <GrimACTab />}
    </div>
  )
}
