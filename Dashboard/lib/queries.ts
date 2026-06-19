'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import type { BridgeSettings, VerificationCode, SuspicionEvent } from './types'

export function useDashboard() {
  return useQuery({ queryKey: ['dashboard'], queryFn: api.getDashboard, refetchInterval: 300000 })
}
export function usePlayers() {
  return useQuery({ queryKey: ['players'], queryFn: api.getPlayers })
}
export function usePlayer(uuid: string) {
  return useQuery({ queryKey: ['player', uuid], queryFn: () => api.getPlayer(uuid) })
}
export function usePunishments() {
  return useQuery({ queryKey: ['punishments'], queryFn: api.getPunishments })
}
export function usePlayerPunishments(uuid: string) {
  return useQuery({
    queryKey: ['player-punishments', uuid],
    queryFn: () => api.getPlayerPunishments(uuid),
  })
}
export function useRevokePunishment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.revokePunishment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['punishments'] })
    },
  })
}
export function useAppeals() {
  return useQuery({ queryKey: ['appeals'], queryFn: api.getAppeals })
}
export function usePlayerAppeals(uuid: string) {
  return useQuery({
    queryKey: ['player-appeals', uuid],
    queryFn: () => api.getPlayerAppeals(uuid),
  })
}
export function useUpdateAppeal() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.updateAppeal(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appeals'] })
    },
  })
}
export function useStaff() {
  return useQuery({ queryKey: ['staff'], queryFn: api.getStaff })
}
export function useRoles() {
  return useQuery({ queryKey: ['roles'], queryFn: api.getRoles })
}
export function usePlugins() {
  return useQuery({ queryKey: ['plugins'], queryFn: api.getPlugins })
}
export function useServerControl() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { server_id: string; action: 'power' | 'restart' | 'maintenance'; enabled?: boolean }) =>
      api.serverControl(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['servers'] }),
  })
}
export function useManageStaff() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { user_id: string; action: 'promote' | 'demote' }) => api.manageStaff(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff'] })
      queryClient.invalidateQueries({ queryKey: ['roles'] })
    },
  })
}
export function useServers() {
  return useQuery({ queryKey: ['servers'], queryFn: api.getServers })
}
export function useAnalytics() {
  return useQuery({ queryKey: ['analytics'], queryFn: api.getServerSummary })
}
export function useCreatePunishment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { player_uuid: string; type: string; reason: string; expires_at?: string }) =>
      api.createPunishment(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['punishments'] }),
  })
}
export function useSettings() {
  return useQuery({ queryKey: ['settings'], queryFn: api.getSettings, retry: false })
}
export function useAudit() {
  return useQuery({ queryKey: ['audit'], queryFn: api.getAudit })
}
export function useSystemHealth() {
  return useQuery({
    queryKey: ['system-health'],
    queryFn: api.getSystemHealth,
    refetchInterval: 5000,
  })
}
export function useBridgeSettings() {
  return useQuery({ queryKey: ['bridge-settings'], queryFn: api.getBridgeSettings })
}
export function useUpdateBridgeSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (settings: Partial<BridgeSettings>) => api.updateBridgeSettings(settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bridge-settings'] })
    },
  })
}
export function usePendingVerifications() {
  return useQuery({
    queryKey: ['pending-verifications'],
    queryFn: api.getPendingVerifications,
    refetchInterval: 300000,
  })
}
export function useRevokeVerification() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (player_uuid: string) => api.revokeVerification(player_uuid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-verifications'] })
    },
  })
}
export function useFlaggedPlayers(skip = 0, limit = 50) {
  return useQuery({
    queryKey: ['flagged-players', skip, limit],
    queryFn: () => api.getFlaggedPlayers(skip, limit),
  })
}
export function usePlayerSuspicion(uuid: string) {
  return useQuery({
    queryKey: ['player-suspicion', uuid],
    queryFn: () => api.getPlayerSuspicion(uuid),
  })
}
export function useMarkFalsePositive() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ event_id, reviewed_by }: { event_id: number; reviewed_by: string }) => 
      api.markFalsePositive(event_id, reviewed_by),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['player-suspicion'] })
    },
  })
}
export function useCreateAltGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ player_uuids, notes, confirmed }: { player_uuids: string[]; notes?: string; confirmed?: boolean }) => 
      api.createAltGroup(player_uuids, notes, confirmed),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alt-groups'] })
    },
  })
}
export function useAltGroups() {
  return useQuery({
    queryKey: ['alt-groups'],
    queryFn: api.getAltGroups,
  })
}
export function useAnalyticsEvents(params?: { limit?: number, event_type?: string, minecraft_uuid?: string }) {
  return useQuery({
    queryKey: ['analytics-events', params],
    queryFn: () => api.getAnalyticsEvents(params),
  })
}
export function usePlayerStats(uuid: string, period = 'alltime') {
  return useQuery({
    queryKey: ['player-stats', uuid, period],
    queryFn: () => api.getPlayerStats(uuid, period),
  })
}
export function useServerSummary() {
  return useQuery({
    queryKey: ['server-summary'],
    queryFn: api.getServerSummary,
  })
}
export function useConnectionTest() {
  return useQuery({
    queryKey: ['connection-test'],
    queryFn: api.checkConnection,
    refetchInterval: 300000,
    retry: false,
  })
}
export function useReplaySessions(params?: { minecraft_uuid?: string, trigger?: string, limit?: number, offset?: number }) {
  return useQuery({
    queryKey: ['replay-sessions', params],
    queryFn: () => api.listReplaySessions(params),
  })
}
export function useReplaySession(replayId: string) {
  return useQuery({
    queryKey: ['replay-session', replayId],
    queryFn: () => api.getReplaySession(replayId),
  })
}
export function useReplayEvents(replayId: string, params?: { event_type?: string, minecraft_uuid?: string, limit?: number, offset?: number }) {
  return useQuery({
    queryKey: ['replay-events', replayId, params],
    queryFn: () => api.getReplayEvents(replayId, params),
  })
}
export function useSnapshots(uuid: string, params?: { limit?: number, offset?: number, trigger?: string, since?: string, until?: string }) {
  return useQuery({
    queryKey: ['snapshots', uuid, params],
    queryFn: () => api.listSnapshots(uuid, params),
  })
}
export function useLatestSnapshot(uuid: string) {
  return useQuery({
    queryKey: ['latest-snapshot', uuid],
    queryFn: () => api.getLatestSnapshot(uuid),
  })
}
export function useSnapshot(snapshotId: string) {
  return useQuery({
    queryKey: ['snapshot', snapshotId],
    queryFn: () => api.getSnapshot(snapshotId),
  })
}
export function useSnapshotsNearReplay(replayId: string, params?: { window_minutes?: number }) {
  return useQuery({
    queryKey: ['snapshots-near-replay', replayId, params],
    queryFn: () => api.getSnapshotsNearReplay(replayId, params),
  })
}
export function useAITasks(params?: { status?: string, task_type?: string, skip?: number, limit?: number }) {
  return useQuery({
    queryKey: ['ai-tasks', params],
    queryFn: () => api.getAITasks(params),
  })
}
export function useAITask(taskId: number) {
  return useQuery({
    queryKey: ['ai-task', taskId],
    queryFn: () => api.getAITask(taskId),
  })
}
export function usePlayerLanguages() {
  return useQuery({
    queryKey: ['player-languages'],
    queryFn: api.getPlayerLanguages,
  })
}
export function useSetPlayerLanguage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ player_uuid, language_code, language_name }: { player_uuid: string; language_code: string; language_name: string }) =>
      api.setPlayerLanguage(player_uuid, language_code, language_name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['player-languages'] })
    },
  })
}
export function usePendingAIConfigs() {
  return useQuery({
    queryKey: ['pending-ai-configs'],
    queryFn: api.getPendingAIConfigs,
    refetchInterval: 300000,
  })
}
export function useRequestAIConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ action_type, natural_language }: { action_type: string; natural_language: string }) =>
      api.requestAIConfig(action_type, natural_language),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-ai-configs'] })
    },
  })
}
export function useApproveAIConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.approveAIConfig(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-ai-configs'] })
    },
  })
}
export function useRejectAIConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.rejectAIConfig(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-ai-configs'] })
    },
  })
}
