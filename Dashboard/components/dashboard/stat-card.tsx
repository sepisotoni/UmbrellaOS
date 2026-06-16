'use client'

import { Minus, TrendingDown, TrendingUp } from 'lucide-react'
import { Area, AreaChart, ResponsiveContainer } from 'recharts'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { StatCard as StatCardType } from '@/lib/types'

const intentColor: Record<string, string> = {
  default: 'var(--color-chart-1)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  danger: 'var(--color-destructive)',
}

export function StatCard({ card }: { card: StatCardType }) {
  const intent = card.intent ?? 'default'
  const color = intentColor[intent]
  const data = card.spark.map((v, i) => ({ i, v }))
  const TrendIcon =
    card.trend === 'up' ? TrendingUp : card.trend === 'down' ? TrendingDown : Minus
  const trendTone =
    card.trend === 'flat'
      ? 'text-muted-foreground'
      : (card.trend === 'up') === (card.intent !== 'danger' && card.intent !== 'warning')
        ? 'text-success'
        : 'text-destructive'

  return (
    <Card className="gap-0 overflow-hidden p-4">
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-medium text-muted-foreground">{card.label}</span>
        {card.changePct !== 0 ? (
          <span className={cn('flex items-center gap-0.5 text-xs font-medium tabular-nums', trendTone)}>
            <TrendIcon className="size-3" />
            {Math.abs(card.changePct)}%
          </span>
        ) : (
          <span className="flex items-center gap-0.5 text-xs text-muted-foreground">
            <Minus className="size-3" />
          </span>
        )}
      </div>
      <div className="mt-1.5 text-2xl font-semibold tracking-tight tabular-nums">
        {card.value}
      </div>
      <div className="mt-3 h-9 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 2, bottom: 2, left: 0, right: 0 }}>
            <defs>
              <linearGradient id={`spark-${card.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="v"
              stroke={color}
              strokeWidth={1.5}
              fill={`url(#spark-${card.id})`}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}
