'use client'

import { useEffect, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { toast } from 'sonner'

export default function AnnouncementsPage() {
  const [channelId, setChannelId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getAnnouncementChannel().then(setChannelId).catch(() => setChannelId(null)).finally(() => setLoading(false))
  }, [])

  const discordUrl = channelId ? `https://discord.com/channels/@me/${channelId}` : null

  const saveChannel = async () => {
    if (!draft.trim()) return
    try {
      await api.updateSetting('discord.announcements_channel', draft.trim())
      setChannelId(draft.trim())
      toast.success('Announcements channel saved')
    } catch {
      toast.error('Failed to save (owner only)')
    }
  }

  if (loading) return <Skeleton className="h-48 w-full rounded-xl" />

  return (
    <>
      <PageHeader title="Announcements" description="Link to your Discord announcements channel." />
      <Card>
        <CardContent className="flex flex-col gap-4 p-6">
          <div>
            <Label>Discord Channel ID</Label>
            <div className="mt-2 flex gap-2">
              <Input value={draft || channelId || ''} onChange={(e) => setDraft(e.target.value)} placeholder="123456789012345678" />
              <Button onClick={saveChannel}>Save</Button>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              The Discord bot auto-creates #umbrella-announcements if missing. Use /setup-channels in Discord.
            </p>
          </div>
          {discordUrl && (
            <Button variant="outline" className="w-fit" asChild={false}>
              <a href={discordUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center">
                <ExternalLink className="mr-2 size-4" /> Open announcements channel
              </a>
            </Button>
          )}
        </CardContent>
      </Card>
    </>
  )
}
