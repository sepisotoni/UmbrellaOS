'use client'

import { Wand2, CheckCircle, XCircle, Loader2, Settings as SettingsIcon } from 'lucide-react'
import { usePendingAIConfigs, useRequestAIConfig, useApproveAIConfig, useRejectAIConfig } from '@/lib/queries'
import { PageHeader } from '@/components/page-header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useState } from 'react'
import { toast } from 'sonner'

export default function AIConfigPage() {
  const { data: pendingConfigs, isLoading } = usePendingAIConfigs()
  const requestAIConfig = useRequestAIConfig()
  const approveAIConfig = useApproveAIConfig()
  const rejectAIConfig = useRejectAIConfig()
  
  const [actionType, setActionType] = useState('plugin_config')
  const [naturalLanguage, setNaturalLanguage] = useState('')
  const [isRequesting, setIsRequesting] = useState(false)

  const handleRequest = async () => {
    if (!naturalLanguage.trim()) {
      toast.error('Please enter a description')
      return
    }
    
    setIsRequesting(true)
    try {
      await requestAIConfig.mutateAsync({ action_type: actionType, natural_language: naturalLanguage })
      setNaturalLanguage('')
      toast.success('Configuration request created')
    } catch (error) {
      toast.error('Failed to create request')
    } finally {
      setIsRequesting(false)
    }
  }

  const handleApprove = async (id: number) => {
    try {
      await approveAIConfig.mutateAsync(id)
      toast.success('Configuration applied')
    } catch (error) {
      toast.error('Failed to approve')
    }
  }

  const handleReject = async (id: number) => {
    try {
      await rejectAIConfig.mutateAsync(id)
      toast.success('Configuration rejected')
    } catch (error) {
      toast.error('Failed to reject')
    }
  }

  return (
    <>
      <PageHeader
        title="AI Configuration Assistant"
        description="Use natural language to configure your server. AI will generate suggestions that you can review and approve."
      />

      <section aria-label="AI Config Request" className="flex flex-col gap-4 mb-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Wand2 className="size-5" aria-hidden />
              Request Configuration
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <Textarea
              placeholder="Tell me what you want to configure... e.g. Add an Economy menu, Create a #staff-chat channel, Change welcome message to Welcome to the server!"
              value={naturalLanguage}
              onChange={(e) => setNaturalLanguage(e.target.value)}
              rows={3}
            />
            <div className="flex items-center gap-4">
              <Select value={actionType} onValueChange={setActionType}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="dashboard_layout">Dashboard Layout</SelectItem>
                  <SelectItem value="discord_config">Discord Server</SelectItem>
                  <SelectItem value="plugin_config">Plugin Settings</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={handleRequest} disabled={isRequesting}>
                {isRequesting ? (
                  <>
                    <Loader2 className="size-4 mr-2 animate-spin" aria-hidden />
                    Processing...
                  </>
                ) : (
                  <>
                    <Wand2 className="size-4 mr-2" aria-hidden />
                    Generate
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>

      <section aria-label="Pending Configs" className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-muted-foreground">Pending Actions</h2>
        {isLoading ? (
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-center">
                <Loader2 className="size-6 animate-spin" aria-hidden />
                <span className="ml-2">Loading...</span>
              </div>
            </CardContent>
          </Card>
        ) : !pendingConfigs || pendingConfigs.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center text-muted-foreground">
              <SettingsIcon className="size-12 mx-auto mb-4 opacity-50" aria-hidden />
              <p>No pending configuration actions</p>
            </CardContent>
          </Card>
        ) : (
          <div className="flex flex-col gap-3">
            {pendingConfigs.map((config: any) => (
              <Card key={config.id}>
                <CardContent className="p-6">
                  <div className="flex flex-col gap-4">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-muted-foreground">
                          What you asked:
                        </span>
                        <span className="text-xs bg-muted px-2 py-1 rounded">
                          {config.action_type}
                        </span>
                      </div>
                      <p className="text-sm">{config.natural_language_input}</p>
                    </div>
                    
                    <div>
                      <span className="text-sm font-medium text-muted-foreground">
                        AI interpretation:
                      </span>
                      <p className="text-sm text-muted-foreground mt-1">
                        {config.ai_interpretation}
                      </p>
                    </div>
                    
                    <div>
                      <span className="text-sm font-medium text-muted-foreground">
                        Proposed changes:
                      </span>
                      <pre className="text-xs bg-muted p-3 rounded mt-1 overflow-x-auto">
                        {JSON.stringify(JSON.parse(config.proposed_changes), null, 2)}
                      </pre>
                    </div>
                    
                    <div className="flex items-center gap-2 justify-end">
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleReject(config.id)}
                        disabled={config.status !== 'pending'}
                      >
                        <XCircle className="size-4 mr-2" aria-hidden />
                        Reject
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleApprove(config.id)}
                        disabled={config.status !== 'pending'}
                      >
                        <CheckCircle className="size-4 mr-2" aria-hidden />
                        Approve
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>
    </>
  )
}
