'use client'

import { ChevronUp, ChevronDown, UserPlus, ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import { useRoles, useStaff, useManageStaff } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { StatusDot } from '@/components/status-badge'
import { timeAgo, formatNumber } from '@/lib/format'
import type { RoleDefinition, StaffMember } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

const roleTone: Record<string, string> = {
  Owner: 'text-destructive', Admin: 'text-primary', Moderator: 'text-info', Helper: 'text-success',
}

export default function StaffPage() {
  const { data: roles, isLoading: rolesLoading } = useRoles()
  const { data: staff, isLoading: staffLoading } = useStaff()

  return (
    <>
      <PageHeader title="Staff" description="Role hierarchy, permissions and team management.">
        <Button size="sm" disabled title="Invite via Discord OAuth login">
          <UserPlus className="size-4" /> Add staff
        </Button>
      </PageHeader>
      <section aria-label="Roles" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {rolesLoading || !roles
          ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-48 rounded-xl" />)
          : roles.map((r) => <RoleCard key={r.role + '-card'} role={r} />)}
      </section>
      <section aria-label="Members" className="flex flex-col gap-3 mt-6">
        <h2 className="text-sm font-semibold text-muted-foreground">Team members</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {staffLoading || !staff
            ? Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)
            : staff.map((m) => <StaffCard key={m.id} member={m} />)}
        </div>
      </section>
    </>
  )
}

function RoleCard({ role }: { role: RoleDefinition }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className={`flex items-center gap-2 text-base ${roleTone[role.role] ?? ''}`}>
            <ShieldCheck className="size-4" /> {role.role}
          </CardTitle>
          <Badge variant="secondary">{role.memberCount}</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm text-muted-foreground">{role.description}</p>
        <div className="flex flex-wrap gap-1.5">
          {role.permissions.slice(0, 8).map((perm) => (
            <span key={perm} className="rounded-md border border-border bg-muted/50 px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
              {perm}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function StaffCard({ member }: { member: StaffMember }) {
  const manage = useManageStaff()

  const changeRole = async (action: 'promote' | 'demote') => {
    try {
      const res = await manage.mutateAsync({ user_id: member.id, action })
      toast.success(`${member.username}: ${res.previous_role} → ${res.new_role}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Role change failed')
    }
  }

  return (
    <Card>
      <CardContent className="flex items-center justify-between gap-3 p-4">
        <div className="flex flex-col gap-1">
          <span className="flex items-center gap-2 font-medium">
            {member.username}
            <StatusDot tone={member.status === 'online' ? 'success' : 'neutral'} />
          </span>
          <span className={`text-xs font-medium ${roleTone[member.role] ?? 'text-muted-foreground'}`}>{member.role}</span>
          <span className="text-xs text-muted-foreground">
            {formatNumber(member.actionsThisWeek)} actions this week · active {timeAgo(member.lastActive)}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button size="sm" variant="ghost" disabled={manage.isPending} onClick={() => changeRole('promote')} aria-label={`Promote ${member.username}`}>
            <ChevronUp className="size-4" />
          </Button>
          <Button size="sm" variant="ghost" disabled={manage.isPending} onClick={() => changeRole('demote')} aria-label={`Demote ${member.username}`}>
            <ChevronDown className="size-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
