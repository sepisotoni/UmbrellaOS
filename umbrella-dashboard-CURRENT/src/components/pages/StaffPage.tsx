import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { staff, StaffMemberSchema } from '../../lib/api'
import {
  Card, Button, Input, Select, Skeleton, ErrorCard, Badge, Modal, Table, Th, Td,
} from '../ui'
import { UserPlus, ChevronUp, ChevronDown } from 'lucide-react'

export function StaffPage() {
  const { token } = useAuth()
  const { data, loading, error, reload } = useFetch<StaffMemberSchema[]>(
    token ? () => staff.list(token) : null,
    [token],
  )

  const [promoting, setPromoting] = useState<string | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState({ discord_id: '', role: 'moderator', username: '' })
  const [addLoading, setAddLoading] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)

  const handleManage = async (userId: string, action: 'promote' | 'demote') => {
    if (!token) return
    setPromoting(userId)
    try {
      await staff.manage(token, { user_id: userId, action })
      reload()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Action failed')
    } finally {
      setPromoting(null)
    }
  }

  const handleAdd = async () => {
    if (!token) return
    setAddLoading(true)
    setAddError(null)
    try {
      await staff.add(token, {
        discord_id: addForm.discord_id,
        role: addForm.role,
        username: addForm.username || undefined,
      })
      setShowAdd(false)
      setAddForm({ discord_id: '', role: 'moderator', username: '' })
      reload()
    } catch (err) {
      setAddError(err instanceof Error ? err.message : 'Failed to add staff')
    } finally {
      setAddLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-100">Staff</h1>
        <Button variant="primary" onClick={() => setShowAdd(true)}>
          <UserPlus className="h-3.5 w-3.5" /> Add Staff
        </Button>
      </div>

      {error && <ErrorCard message={error} onRetry={reload} />}
      {loading && <Skeleton className="h-40 w-full" />}

      {!loading && !error && (
        <Table>
          <thead>
            <tr>
              <Th>Username</Th>
              <Th>Discord ID</Th>
              <Th>Role</Th>
              <Th>Permissions</Th>
              <Th>Actions</Th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((m) => (
              <tr key={m.id} className="border-b border-white/[0.04]">
                <Td className="font-medium text-slate-200">{m.username}</Td>
                <Td className="font-mono text-[10px]">{m.discord_id}</Td>
                <Td>
                  <Badge variant="purple">{m.role ?? '—'}</Badge>
                </Td>
                <Td>{m.permissions.length} permissions</Td>
                <Td>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      className="py-0.5 px-2"
                      loading={promoting === m.id}
                      onClick={() => handleManage(m.id, 'promote')}
                    >
                      <ChevronUp className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      className="py-0.5 px-2"
                      loading={promoting === m.id}
                      onClick={() => handleManage(m.id, 'demote')}
                    >
                      <ChevronDown className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </Td>
              </tr>
            ))}
            {(data ?? []).length === 0 && (
              <tr>
                <Td colSpan={5} className="text-center text-slate-500 py-6">No staff members found.</Td>
              </tr>
            )}
          </tbody>
        </Table>
      )}

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Staff Member">
        <div className="space-y-3">
          {addError && <ErrorCard message={addError} />}
          <div>
            <label className="text-[11px] text-slate-500 mb-1 block">Discord ID *</label>
            <Input
              value={addForm.discord_id}
              onChange={(e) => setAddForm((f) => ({ ...f, discord_id: e.target.value }))}
              placeholder="Discord user ID"
            />
          </div>
          <div>
            <label className="text-[11px] text-slate-500 mb-1 block">Username (optional)</label>
            <Input
              value={addForm.username}
              onChange={(e) => setAddForm((f) => ({ ...f, username: e.target.value }))}
              placeholder="Discord username"
            />
          </div>
          <div>
            <label className="text-[11px] text-slate-500 mb-1 block">Role *</label>
            <Select
              value={addForm.role}
              onChange={(e) => setAddForm((f) => ({ ...f, role: e.target.value }))}
              className="w-full"
            >
              <option value="helper">Helper</option>
              <option value="moderator">Moderator</option>
              <option value="senior_moderator">Senior Moderator</option>
              <option value="admin">Admin</option>
            </Select>
          </div>
          <div className="flex gap-2 pt-2">
            <Button variant="primary" loading={addLoading} onClick={handleAdd}>Add</Button>
            <Button variant="secondary" onClick={() => setShowAdd(false)}>Cancel</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
