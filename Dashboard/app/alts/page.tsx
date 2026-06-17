'use client'

import { useState } from 'react'
import Link from 'next/link'
import { toast } from 'sonner'
import { useFlaggedPlayers, useAltGroups, useMarkFalsePositive } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { timeAgo } from '@/lib/format'
import type { FlaggedPlayer } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function AltsPage() {
  const { data: flaggedPlayers, isLoading: isLoadingFlagged } = useFlaggedPlayers()
  const { data: altGroups, isLoading: isLoadingGroups } = useAltGroups()
  const markFalsePositive = useMarkFalsePositive()

  const handleMarkFalsePositive = async (event_id: number) => {
    try {
      await markFalsePositive.mutateAsync({ event_id, reviewed_by: 'Staff' })
      toast.success('Marked as false positive')
    } catch (error) {
      toast.error('Failed to mark as false positive')
    }
  }

  return (
    <>
      <PageHeader
        title="Alt Detection"
        description="Manage flagged players and alt groups based on suspicion scoring."
      />

      <Tabs defaultValue="flagged" className="w-full">
        <TabsList>
          <TabsTrigger value="flagged">Flagged Players</TabsTrigger>
          <TabsTrigger value="groups">Alt Groups</TabsTrigger>
        </TabsList>

        <TabsContent value="flagged">
          {isLoadingFlagged ? (
            <Card>
              <CardContent className="p-6">
                <Skeleton className="h-64 w-full" />
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-6">
                {flaggedPlayers && flaggedPlayers.length > 0 ? (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Username</TableHead>
                        <TableHead>Score</TableHead>
                        <TableHead>Risk Level</TableHead>
                        <TableHead>Flagged At</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {flaggedPlayers.map((player: FlaggedPlayer) => (
                        <TableRow key={player.uuid}>
                          <TableCell className="font-medium">{player.username}</TableCell>
                          <TableCell className="font-mono">{player.suspicion_score}/100</TableCell>
                          <TableCell>
                            {player.suspicion_score >= 95 ? (
                              <span className="text-red-600 font-bold">CRITICAL</span>
                            ) : player.suspicion_score >= 80 ? (
                              <span className="text-yellow-600 font-bold">HIGH</span>
                            ) : (
                              <span className="text-orange-600 font-bold">MEDIUM</span>
                            )}
                          </TableCell>
                          <TableCell>{timeAgo(player.created_at)}</TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              <Button size="sm" variant="outline">
                                <Link href={`/players/${player.uuid}`}>View Profile</Link>
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleMarkFalsePositive(0)}
                              >
                                Mark False Positive
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <div className="py-10 text-center text-sm text-muted-foreground">
                    No flagged players.
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="groups">
          {isLoadingGroups ? (
            <Card>
              <CardContent className="p-6">
                <Skeleton className="h-64 w-full" />
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-6">
                {altGroups && altGroups.length > 0 ? (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Group ID</TableHead>
                        <TableHead>Created At</TableHead>
                        <TableHead>Notes</TableHead>
                        <TableHead>Confirmed</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {altGroups.map((group: any) => (
                        <TableRow key={group.id}>
                          <TableCell className="font-mono">{group.id}</TableCell>
                          <TableCell>{timeAgo(group.created_at)}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">{group.notes || '-'}</TableCell>
                          <TableCell>
                            {group.confirmed ? (
                              <span className="text-green-600 font-bold">Yes</span>
                            ) : (
                              <span className="text-gray-600">No</span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <div className="py-10 text-center text-sm text-muted-foreground">
                    No confirmed alt groups.
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </>
  )
}
