'use client'

import { useState } from 'react'
import { useAITasks } from '@/lib/queries'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/page-header'
import { timeAgo } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { AITask, AITaskStatus } from '@/lib/types'

export default function AITasksPage() {
  const [activeTab, setActiveTab] = useState<AITaskStatus | 'all'>('pending')
  const [selectedTask, setSelectedTask] = useState<AITask | null>(null)
  const [actionTaken, setActionTaken] = useState('')
  const [denyReason, setDenyReason] = useState('')
  const [reviewedBy, setReviewedBy] = useState('')

  const { data: tasks, isLoading, refetch } = useAITasks(
    activeTab === 'all' ? undefined : { status: activeTab }
  )

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.8) {
      return <Badge className="bg-green-500">{Math.round(confidence * 100)}%</Badge>
    } else if (confidence >= 0.5) {
      return <Badge className="bg-yellow-500">{Math.round(confidence * 100)}%</Badge>
    } else {
      return <Badge className="bg-red-500">{Math.round(confidence * 100)}%</Badge>
    }
  }

  const handleApprove = async (task: AITask) => {
    if (!actionTaken || !reviewedBy) return
    
    await api.approveAITask(task.id, { action_taken: actionTaken, reviewed_by: reviewedBy })
    refetch()
    setSelectedTask(null)
    setActionTaken('')
    setReviewedBy('')
  }

  const handleDeny = async (task: AITask) => {
    if (!reviewedBy) return
    
    await api.denyAITask(task.id, { reviewed_by: reviewedBy, reason: denyReason })
    refetch()
    setSelectedTask(null)
    setDenyReason('')
    setReviewedBy('')
  }

  return (
    <>
      <PageHeader
        title="AI Tasks"
        description="Review AI-generated moderation recommendations."
      />

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Filter by Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Button
              variant={activeTab === 'pending' ? 'default' : 'outline'}
              onClick={() => setActiveTab('pending')}
            >
              Pending
            </Button>
            <Button
              variant={activeTab === 'approved' ? 'default' : 'outline'}
              onClick={() => setActiveTab('approved')}
            >
              Approved
            </Button>
            <Button
              variant={activeTab === 'denied' ? 'default' : 'outline'}
              onClick={() => setActiveTab('denied')}
            >
              Denied
            </Button>
            <Button
              variant={activeTab === 'all' ? 'default' : 'outline'}
              onClick={() => setActiveTab('all')}
            >
              All
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            {activeTab === 'all' ? 'All Tasks' : `${activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Tasks`}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-64" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Player</TableHead>
                  <TableHead>Summary</TableHead>
                  <TableHead>Recommendation</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Created At</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasks && tasks.length > 0 ? (
                  tasks.map((task: AITask) => (
                    <TableRow key={task.id}>
                      <TableCell className="font-medium">{task.task_type}</TableCell>
                      <TableCell className="font-mono text-sm">{task.player_uuid || '-'}</TableCell>
                      <TableCell className="max-w-xs truncate">{task.ai_summary}</TableCell>
                      <TableCell>{task.ai_recommendation}</TableCell>
                      <TableCell>{getConfidenceBadge(task.ai_confidence)}</TableCell>
                      <TableCell>{timeAgo(task.created_at)}</TableCell>
                      <TableCell>
                        <Sheet>
                          <SheetTrigger asChild>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setSelectedTask(task)}
                            >
                              Review
                            </Button>
                          </SheetTrigger>
                          <SheetContent className="w-[600px] sm:w-[800px]">
                            <SheetHeader>
                              <SheetTitle>AI Task Review</SheetTitle>
                            </SheetHeader>
                            {selectedTask && (
                              <div className="mt-6 space-y-6">
                                <div className="grid grid-cols-2 gap-4">
                                  <div>
                                    <Label>Task Type</Label>
                                    <p className="font-medium">{selectedTask.task_type}</p>
                                  </div>
                                  <div>
                                    <Label>Status</Label>
                                    <p className="font-medium">{selectedTask.status}</p>
                                  </div>
                                  <div>
                                    <Label>Player UUID</Label>
                                    <p className="font-mono text-sm">{selectedTask.player_uuid || '-'}</p>
                                  </div>
                                  <div>
                                    <Label>Confidence</Label>
                                    <p className="font-medium">{getConfidenceBadge(selectedTask.ai_confidence)}</p>
                                  </div>
                                </div>

                                <div>
                                  <Label>AI Summary</Label>
                                  <p className="text-sm mt-1">{selectedTask.ai_summary}</p>
                                </div>

                                <div>
                                  <Label>AI Recommendation</Label>
                                  <p className="font-medium mt-1">{selectedTask.ai_recommendation}</p>
                                </div>

                                <div>
                                  <Label>Evidence (JSON)</Label>
                                  <Textarea
                                    value={selectedTask.evidence || 'No evidence provided'}
                                    readOnly
                                    className="font-mono text-xs mt-1 h-32"
                                  />
                                </div>

                                {selectedTask.status === 'pending' && (
                                  <div className="space-y-4 pt-4 border-t">
                                    <div>
                                      <Label>Reviewer Discord ID</Label>
                                      <Input
                                        placeholder="Enter your Discord ID"
                                        value={reviewedBy}
                                        onChange={(e) => setReviewedBy(e.target.value)}
                                        className="mt-1"
                                      />
                                    </div>

                                    <div className="flex gap-2">
                                      <Button
                                        onClick={() => handleApprove(selectedTask)}
                                        disabled={!actionTaken || !reviewedBy}
                                        className="bg-green-600 hover:bg-green-700"
                                      >
                                        Approve
                                      </Button>
                                      <Button
                                        variant="destructive"
                                        onClick={() => handleDeny(selectedTask)}
                                        disabled={!reviewedBy}
                                      >
                                        Deny
                                      </Button>
                                    </div>

                                    <div>
                                      <Label>Action Taken (for approval)</Label>
                                      <Input
                                        placeholder="e.g., 'Banned for 7 days'"
                                        value={actionTaken}
                                        onChange={(e) => setActionTaken(e.target.value)}
                                        className="mt-1"
                                      />
                                    </div>

                                    <div>
                                      <Label>Deny Reason (optional)</Label>
                                      <Textarea
                                        placeholder="Reason for denying the recommendation"
                                        value={denyReason}
                                        onChange={(e) => setDenyReason(e.target.value)}
                                        className="mt-1"
                                      />
                                    </div>
                                  </div>
                                )}

                                {selectedTask.status !== 'pending' && (
                                  <div className="pt-4 border-t">
                                    <Label>Review Details</Label>
                                    <div className="mt-2 space-y-2 text-sm">
                                      <p><span className="font-medium">Reviewed By:</span> {selectedTask.reviewed_by || '-'}</p>
                                      <p><span className="font-medium">Reviewed At:</span> {selectedTask.reviewed_at ? timeAgo(selectedTask.reviewed_at) : '-'}</p>
                                      <p><span className="font-medium">Action Taken:</span> {selectedTask.action_taken || '-'}</p>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </SheetContent>
                        </Sheet>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      No AI tasks found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  )
}
