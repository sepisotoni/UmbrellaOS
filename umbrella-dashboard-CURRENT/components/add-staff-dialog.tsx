'use client'

import { useState } from 'react'
import { UserPlus, Check } from 'lucide-react'
import { useStaff, useRoles, useDiscordMembers, useAddStaff } from '@/lib/queries'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const ASSIGNABLE_ROLES = ['helper', 'moderator', 'admin']

export function AddStaffDialog() {
  const [open, setOpen] = useState(false)
  const [tab, setTab] = useState('id')
  const [discordId, setDiscordId] = useState('')
  const [manualUsername, setManualUsername] = useState('')
  const [selectedMember, setSelectedMember] = useState<{ discord_id: string; username: string } | null>(null)
  const [selectedUser, setSelectedUser] = useState<{ discord_id: string; username: string } | null>(null)
  const [role, setRole] = useState('helper')

  const { data: members, isLoading: membersLoading } = useDiscordMembers()
  const { data: staffList } = useStaff()
  const { data: roles } = useRoles()
  const addStaff = useAddStaff()

  const nonStaffMembers = members?.filter((m) => !m.is_staff) ?? []
  const availableRoles = roles?.filter((r) => r.role && ASSIGNABLE_ROLES.includes(r.role.toLowerCase())) ?? []

  function reset() {
    setDiscordId(''); setManualUsername(''); setSelectedMember(null); setSelectedUser(null); setRole('helper'); setTab('id')
  }

  function getTarget(): { discord_id: string; username?: string } | null {
    if (tab === 'id') return discordId.trim() ? { discord_id: discordId.trim(), username: manualUsername.trim() || undefined } : null
    if (tab === 'members') return selectedMember
    if (tab === 'existing') return selectedUser
    return null
  }

  function handleSubmit() {
    const target = getTarget()
    if (!target || !role) return
    addStaff.mutate({ ...target, role }, { onSuccess: () => { setOpen(false); reset() } })
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset() }}>
      <DialogTrigger>
        <button type="button" onClick={() => setOpen(true)} className="inline-flex items-center gap-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground">
          <UserPlus className="size-4" />Add staff
        </button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add staff member</DialogTitle>
          <DialogDescription>Grant a Discord user a staff role.</DialogDescription>
        </DialogHeader>

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="w-full">
            <TabsTrigger value="id" className="flex-1">Discord ID</TabsTrigger>
            <TabsTrigger value="members" className="flex-1">Server members</TabsTrigger>
            <TabsTrigger value="existing" className="flex-1">Existing users</TabsTrigger>
          </TabsList>

          <TabsContent value="id" className="flex flex-col gap-3 mt-3">
            <div className="flex flex-col gap-1.5">
              <Label>Discord User ID</Label>
              <Input placeholder="e.g. 986672767971758102" value={discordId} onChange={(e) => setDiscordId(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Username <span className="text-muted-foreground text-xs">(optional)</span></Label>
              <Input placeholder="e.g. sepisotoni" value={manualUsername} onChange={(e) => setManualUsername(e.target.value)} />
            </div>
          </TabsContent>

          <TabsContent value="members" className="mt-3">
            {membersLoading ? (
              <p className="text-sm text-muted-foreground py-4 text-center">Loading members…</p>
            ) : nonStaffMembers.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">All server members are already staff.</p>
            ) : (
              <div className="flex flex-col gap-1 max-h-48 overflow-y-auto rounded border p-1">
                {nonStaffMembers.map((m) => (
                  <button key={m.discord_id} type="button" onClick={() => setSelectedMember(m)}
                    className={"flex items-center justify-between rounded px-3 py-2 text-sm text-left hover:bg-accent transition-colors " + (selectedMember?.discord_id === m.discord_id ? "bg-accent" : "")}>
                    <span>{m.username}</span>
                    {selectedMember?.discord_id === m.discord_id && <Check className="size-4 text-primary" />}
                  </button>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="existing" className="mt-3">
            {!staffList ? (
              <p className="text-sm text-muted-foreground py-4 text-center">Loading users…</p>
            ) : (
              <div className="flex flex-col gap-1 max-h-48 overflow-y-auto rounded border p-1">
                {staffList.map((s) => (
                  <button key={s.id} type="button" onClick={() => setSelectedUser({ discord_id: s.id, username: s.username })}
                    className={"flex items-center justify-between rounded px-3 py-2 text-sm text-left hover:bg-accent transition-colors " + (selectedUser?.discord_id === s.id ? "bg-accent" : "")}>
                    <span>{s.username}</span>
                    {selectedUser?.discord_id === s.id && <Check className="size-4 text-primary" />}
                  </button>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>

        <div className="flex flex-col gap-1.5">
          <Label>Role</Label>
          <Select value={role} onValueChange={setRole}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {availableRoles.length > 0
                ? availableRoles.map((r) => <SelectItem key={r.role} value={r.role.toLowerCase()}>{r.role}</SelectItem>)
                : ASSIGNABLE_ROLES.map((r) => <SelectItem key={r} value={r} className="capitalize">{r.charAt(0).toUpperCase() + r.slice(1)}</SelectItem>)
              }
            </SelectContent>
          </Select>
        </div>

        {addStaff.isError && (
          <p className="text-sm text-destructive">Failed to add staff member. Check the ID and try again.</p>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={!getTarget() || !role || addStaff.isPending}>
            {addStaff.isPending ? "Adding…" : "Add staff"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
