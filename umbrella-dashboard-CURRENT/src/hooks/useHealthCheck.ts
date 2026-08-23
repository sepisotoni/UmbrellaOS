import { useState, useEffect, useRef } from 'react'
import { health, HealthResponse } from '../lib/api'

export type ConnectionStatus = 'checking' | 'connected' | 'disconnected'

export function useHealthCheck(intervalMs = 30_000) {
  const [status, setStatus] = useState<ConnectionStatus>('checking')
  const [healthData, setHealthData] = useState<HealthResponse | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const check = async () => {
    try {
      const data = await health.get()
      setHealthData(data)
      setStatus('connected')
    } catch {
      setHealthData(null)
      setStatus('disconnected')
    }
  }

  useEffect(() => {
    check()
    timerRef.current = setInterval(check, intervalMs)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [intervalMs])

  return { status, healthData, recheck: check }
}
