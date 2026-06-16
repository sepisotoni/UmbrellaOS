'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from './api'

export function useDashboard() {
  return useQuery({ queryKey: ['dashboard'], queryFn: api.getDashboard })
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
export function useAppeals() {
  return useQuery({ queryKey: ['appeals'], queryFn: api.getAppeals })
}
export function usePlayerAppeals(uuid: string) {
  return useQuery({
    queryKey: ['player-appeals', uuid],
    queryFn: () => api.getPlayerAppeals(uuid),
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
export function useServers() {
  return useQuery({ queryKey: ['servers'], queryFn: api.getServers })
}
export function useAnalytics() {
  return useQuery({ queryKey: ['analytics'], queryFn: api.getAnalytics })
}
export function useSettings() {
  return useQuery({ queryKey: ['settings'], queryFn: api.getSettings })
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
