'use client'

import { Languages, Settings as SettingsIcon } from 'lucide-react'
import { usePlayerLanguages } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { timeAgo } from '@/lib/format'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export default function TranslationPage() {
  const { data: playerLanguages, isLoading } = usePlayerLanguages()

  return (
    <>
      <PageHeader
        title="Translation & Language"
        description="Manage player language preferences and translation settings."
      />

      <section aria-label="Translation Settings" className="flex flex-col gap-3 mb-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <SettingsIcon className="size-5" aria-hidden />
              Translation Settings
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium">AI Translation Model</h3>
                <p className="text-sm text-muted-foreground">Claude Haiku (Anthropic)</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="flex items-center gap-2 text-sm">
                  <span className="size-2 rounded-full bg-red-500" />
                  OpenRouter API Key
                </span>
                <span className="text-sm text-muted-foreground">Not configured</span>
              </div>
            </div>
            <div className="text-sm text-muted-foreground">
              Configure the OpenRouter API key in <span className="text-foreground font-medium">Settings → AI</span> to enable AI-powered translation.
            </div>
          </CardContent>
        </Card>
      </section>

      <section aria-label="Player Languages" className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-muted-foreground">Player Language Preferences</h2>
        <Card>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-6">
                <Skeleton className="h-8 w-32 mb-4" />
                <Skeleton className="h-32" />
              </div>
            ) : !playerLanguages || playerLanguages.length === 0 ? (
              <div className="p-12 text-center text-muted-foreground">
                <Languages className="size-12 mx-auto mb-4 opacity-50" aria-hidden />
                <p>No language preferences set yet</p>
                <p className="text-sm">Players set their language in-game with /lang</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Player UUID</TableHead>
                    <TableHead>Language</TableHead>
                    <TableHead>Auto-translate In</TableHead>
                    <TableHead>Auto-translate Out</TableHead>
                    <TableHead>Last Updated</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {playerLanguages.map((player) => (
                    <TableRow key={player.id}>
                      <TableCell className="font-mono text-xs">
                        {player.player_uuid}
                      </TableCell>
                      <TableCell>
                        {player.language_name}
                      </TableCell>
                      <TableCell>
                        {player.auto_translate_incoming ? (
                          <span className="text-green-600">Enabled</span>
                        ) : (
                          <span className="text-muted-foreground">Disabled</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {player.auto_translate_outgoing ? (
                          <span className="text-green-600">Enabled</span>
                        ) : (
                          <span className="text-muted-foreground">Disabled</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {timeAgo(player.updated_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </section>
    </>
  )
}
