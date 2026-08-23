import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { verification, VerificationLinkSchema, VerificationCodeSchema } from '../../lib/api'
import { Card, Button, Skeleton, ErrorCard, Badge, Tabs, Table, Th, Td } from '../ui'
import { Unlink } from 'lucide-react'

function formatDate(d: string | null) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString()
}

function LinksTab() {
  const { token } = useAuth()
  const { data, loading, error, reload } = useFetch<VerificationLinkSchema[]>(
    token ? () => verification.links(token, { limit: 100 }) : null,
    [token],
  )
  const [unlinking, setUnlinking] = useState<string | null>(null)

  const handleUnlink = async (discordId: string) => {
    if (!token) return
    if (!confirm(`Unlink Discord ID ${discordId}?`)) return
    setUnlinking(discordId)
    try {
      await verification.unlink(token, discordId)
      reload()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Unlink failed')
    } finally {
      setUnlinking(null)
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
              <Th>Discord</Th>
              <Th>Minecraft</Th>
              <Th>Linked</Th>
              <Th>Status</Th>
              <Th>{''}</Th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((link) => (
              <tr key={link.id} className="border-b border-white/[0.04]">
                <Td>
                  <div>
                    <p className="font-medium text-slate-200">{link.discord_username ?? link.discord_id}</p>
                    <p className="text-[10px] text-slate-500 font-mono">{link.discord_id}</p>
                  </div>
                </Td>
                <Td>
                  <div>
                    <p className="font-medium text-slate-200">{link.minecraft_username ?? '—'}</p>
                    <p className="text-[10px] text-slate-500 font-mono">{link.minecraft_uuid?.slice(0, 8) ?? '—'}…</p>
                  </div>
                </Td>
                <Td>{formatDate(link.linked_at)}</Td>
                <Td>
                  <Badge variant={link.status === 'VERIFIED' ? 'success' : 'warning'}>
                    {link.status}
                  </Badge>
                </Td>
                <Td>
                  <Button
                    variant="ghost"
                    className="text-red-400 hover:text-red-300 py-0.5 px-2"
                    loading={unlinking === link.discord_id}
                    onClick={() => handleUnlink(link.discord_id)}
                  >
                    <Unlink className="h-3.5 w-3.5" />
                    Unlink
                  </Button>
                </Td>
              </tr>
            ))}
            {(data ?? []).length === 0 && (
              <tr>
                <Td colSpan={5} className="text-center text-slate-500 py-6">No verified accounts.</Td>
              </tr>
            )}
          </tbody>
        </Table>
      )}
    </div>
  )
}

function PendingTab() {
  const { token } = useAuth()
  const { data, loading, error, reload } = useFetch<VerificationCodeSchema[]>(
    token ? () => verification.pending(token) : null,
    [token],
  )

  return (
    <div className="space-y-3">
      {error && <ErrorCard message={error} onRetry={reload} />}
      {loading && <Skeleton className="h-40 w-full" />}
      {!loading && !error && (
        <Table>
          <thead>
            <tr>
              <Th>Player</Th>
              <Th>Code</Th>
              <Th>Created</Th>
              <Th>Expires</Th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((c) => (
              <tr key={c.id} className="border-b border-white/[0.04]">
                <Td>
                  <p className="font-medium text-slate-200">{c.player_username}</p>
                  <p className="text-[10px] font-mono text-slate-500">{c.player_uuid.slice(0, 8)}…</p>
                </Td>
                <Td><span className="font-mono text-violet-300">{c.code}</span></Td>
                <Td>{formatDate(c.created_at)}</Td>
                <Td>{formatDate(c.expires_at)}</Td>
              </tr>
            ))}
            {(data ?? []).length === 0 && (
              <tr>
                <Td colSpan={4} className="text-center text-slate-500 py-6">No pending verifications.</Td>
              </tr>
            )}
          </tbody>
        </Table>
      )}
    </div>
  )
}

const TABS = [
  { id: 'links', label: 'Verified Links' },
  { id: 'pending', label: 'Pending Codes' },
]

export function VerificationPage() {
  const [tab, setTab] = useState('links')
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-100">Verification</h1>
      <Tabs tabs={TABS} active={tab} onChange={setTab} />
      {tab === 'links' && <LinksTab />}
      {tab === 'pending' && <PendingTab />}
    </div>
  )
}
