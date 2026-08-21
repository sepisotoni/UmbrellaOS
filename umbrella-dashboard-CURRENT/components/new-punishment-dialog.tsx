'use client'

import { useState } from 'react'
import { Check, ChevronsUpDown, Plus } from 'lucide-react'
import { usePlayers, useCreatePunishment } from '@/lib/queries'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'

const PUNISHMENT_TYPES = [
  { value: 'warn', label: 'Warn' },
  { value: 'mute', label: 'Mute' },
  { value: 'tempban', label: 'Temp Ban' },
  { value: 'ban', label: 'Ban' },
]

export function NewPunishmentDialog() {
  const [open, setOpen] = useState(false)
  const [playerOpen, setPlayerOpen] = useState(false)
  const [playerUuid, setPlayerUuid] = useState('')
  const [type, setType] = useState('warn')
  const [reason, setReason] = useState('')
  const [durationHours, setDurationHours] = useState('')

  const { data: players, isLoading: playersLoading } = usePlayers()
  const createPunishment = useCreatePunishment()

  const selectedPlayer = players?.find((p) => p.uuid === playerUuid)
  const needsDuration = type === 'tempban'

  function reset() {
    setPlayerUuid('')
    setType('warn')
    setReason('')
    setDurationHours('')
  }

  function handleSubmit() {
    if (!playerUuid || !reason.trim()) return

    const body: { player_uuid: string; type: string; reason: string; expires_at?: string } = {
      player_uuid: playerUuid,
      type,
      reason: reason.trim(),
    }

    if (needsDuration && durationHours) {
      const hours = Number(durationHours)
      if (hours > 0) {
        body.expires_at = new Date(Date.now() + hours * 60 * 60 * 1000).toISOString()
      }
    }

    createPunishment.mutate(body, {
      onSuccess: () => {
        setOpen(false)
        reset()
      },
    })
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset() }}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="size-4" aria-hidden /> New punishment
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New punishment</DialogTitle>
          <DialogDescription>
            Issue a moderation action against a player.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="player">Player</Label>
            <Popover open={playerOpen} onOpenChange={setPlayerOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={playerOpen}
                  className="w-full justify-between font-normal"
                >
                  {selectedPlayer ? selectedPlayer.username : 'Select player…'}
                  <ChevronsUpDown className="size-4 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[--radix-popover-trigger-width] p-0">
                <Command>
                  <CommandInput placeholder="Search players…" />
                  <CommandList>
                    <CommandEmpty>
                      {playersLoading ? 'Loading…' : 'No player found.'}
                    </CommandEmpty>
                    <CommandGroup>
                      {players?.map((p) => (
                        <CommandItem
                          key={p.uuid}
                          value={p.username}
                          onSelect={() => {
                            setPlayerUuid(p.uuid)
                            setPlayerOpen(false)
                          }}
                        >
                          <Check
                            className={cn(
                              'mr-2 size-4',
                              playerUuid === p.uuid ? 'opacity-100' : 'opacity-0',
                            )}
                          />
                          {p.username}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="type">Type</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger id="type" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PUNISHMENT_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {needsDuration && (
            <div className="flex flex-col gap-2">
              <Label htmlFor="duration">Duration (hours)</Label>
              <Input
                id="duration"
                type="number"
                min={1}
                placeholder="e.g. 24"
                value={durationHours}
                onChange={(e) => setDurationHours(e.target.value)}
              />
            </div>
          )}

          <div className="flex flex-col gap-2">
            <Label htmlFor="reason">Reason</Label>
            <Textarea
              id="reason"
              placeholder="Reason for this punishment…"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!playerUuid || !reason.trim() || createPunishment.isPending}
          >
            {createPunishment.isPending ? 'Creating…' : 'Create punishment'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
