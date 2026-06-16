'use client'

import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { toast } from 'sonner'
import { useSettings } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { StatusPill } from '@/components/status-badge'
import type { SettingItem, SettingsCategory } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function SettingsPage() {
  const { data, isLoading } = useSettings()

  if (isLoading || !data) {
    return (
      <>
        <PageHeader title="Settings" description="Configure the Umbrella Core platform." />
        <Skeleton className="h-96 w-full rounded-xl" />
      </>
    )
  }

  return (
    <>
      <PageHeader title="Settings" description="Configure the Umbrella Core platform.">
        <Button size="sm" onClick={() => toast.success('Settings saved')}>
          Save changes
        </Button>
      </PageHeader>

      <Tabs defaultValue={data[0]?.id} className="w-full">
        <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1">
          {data.map((cat) => (
            <TabsTrigger key={cat.id} value={cat.id}>
              {cat.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {data.map((cat) => (
          <TabsContent key={cat.id} value={cat.id} className="mt-4">
            <CategoryPanel category={cat} />
          </TabsContent>
        ))}
      </Tabs>
    </>
  )
}

function CategoryPanel({ category }: { category: SettingsCategory }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-1 p-0">
        {category.items.map((item, i) => (
          <div key={item.key}>
            {i > 0 ? <div className="h-px bg-border" /> : null}
            <SettingRow item={item} />
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function SettingRow({ item }: { item: SettingItem }) {
  return (
    <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <Label htmlFor={item.key} className="text-sm font-medium">
            {item.label}
          </Label>
          {item.restartRequired ? (
            <StatusPill tone="warning" dot={false} className="normal-case">
              Restart required
            </StatusPill>
          ) : null}
        </div>
        <p className="text-xs text-muted-foreground">{item.description}</p>
      </div>
      <div className="w-full sm:w-64">
        <SettingControl item={item} />
      </div>
    </div>
  )
}

function SettingControl({ item }: { item: SettingItem }) {
  const [reveal, setReveal] = useState(false)

  if (item.type === 'boolean') {
    return (
      <div className="flex sm:justify-end">
        <Switch id={item.key} defaultChecked={Boolean(item.value)} />
      </div>
    )
  }

  if (item.type === 'select') {
    return (
      <Select defaultValue={String(item.value)}>
        <SelectTrigger id={item.key} className="w-full capitalize">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {(item.options ?? []).map((opt) => (
            <SelectItem key={opt} value={opt} className="capitalize">
              {opt}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    )
  }

  if (item.type === 'secret') {
    return (
      <div className="relative">
        <Input
          id={item.key}
          type={reveal ? 'text' : 'password'}
          defaultValue={String(item.value)}
          className="pr-9 font-mono"
        />
        <button
          type="button"
          onClick={() => setReveal((v) => !v)}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          aria-label={reveal ? 'Hide secret' : 'Reveal secret'}
        >
          {reveal ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>
    )
  }

  return (
    <Input
      id={item.key}
      type={item.type === 'number' ? 'number' : 'text'}
      defaultValue={String(item.value)}
    />
  )
}
