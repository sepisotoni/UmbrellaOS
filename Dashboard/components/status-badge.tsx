import { cn } from '@/lib/utils'

type Tone = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'primary'

const toneClasses: Record<Tone, string> = {
  success: 'bg-success/12 text-success border-success/25',
  warning: 'bg-warning/12 text-warning border-warning/25',
  danger: 'bg-destructive/12 text-destructive border-destructive/25',
  info: 'bg-info/12 text-info border-info/25',
  primary: 'bg-primary/12 text-primary border-primary/25',
  neutral: 'bg-muted text-muted-foreground border-border',
}

const dotClasses: Record<Tone, string> = {
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-destructive',
  info: 'bg-info',
  primary: 'bg-primary',
  neutral: 'bg-muted-foreground',
}

export function StatusPill({
  tone,
  children,
  dot = true,
  className,
}: {
  tone: Tone
  children: React.ReactNode
  dot?: boolean
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium capitalize',
        toneClasses[tone],
        className,
      )}
    >
      {dot ? <span className={cn('size-1.5 rounded-full', dotClasses[tone])} /> : null}
      {children}
    </span>
  )
}

export function StatusDot({ tone, ping }: { tone: Tone; ping?: boolean }) {
  return (
    <span className="relative flex size-2">
      {ping ? (
        <span
          className={cn(
            'absolute inline-flex size-full animate-ping rounded-full opacity-60',
            dotClasses[tone],
          )}
        />
      ) : null}
      <span className={cn('relative inline-flex size-2 rounded-full', dotClasses[tone])} />
    </span>
  )
}

const punishmentTone: Record<string, Tone> = {
  warn: 'warning',
  mute: 'info',
  tempban: 'warning',
  ban: 'danger',
}
export function PunishmentTypeBadge({ type }: { type: string }) {
  return <StatusPill tone={punishmentTone[type] ?? 'neutral'} dot={false}>{type}</StatusPill>
}

const statusTone: Record<string, Tone> = {
  active: 'danger',
  expired: 'neutral',
  revoked: 'success',
  appealed: 'info',
  open: 'warning',
  accepted: 'success',
  denied: 'danger',
  escalated: 'info',
  online: 'success',
  offline: 'neutral',
  maintenance: 'warning',
  connected: 'success',
  degraded: 'warning',
  disconnected: 'danger',
  healthy: 'success',
  down: 'danger',
}
export function GenericStatusBadge({ status }: { status: string }) {
  return (
    <StatusPill tone={statusTone[status] ?? 'neutral'}>{status}</StatusPill>
  )
}

export function RiskBadge({ score }: { score: number }) {
  const tone: Tone =
    score >= 76 ? 'danger' : score >= 51 ? 'warning' : score >= 26 ? 'info' : 'success'
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className={cn(
          'inline-flex h-5 min-w-9 items-center justify-center rounded-md px-1.5 text-xs font-semibold tabular-nums',
          toneClasses[tone],
        )}
      >
        {score}
      </span>
    </span>
  )
}
