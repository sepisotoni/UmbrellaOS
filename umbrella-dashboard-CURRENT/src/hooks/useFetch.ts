import { useState, useEffect, useCallback, useRef } from 'react'

interface FetchState<T> {
  data: T | null
  loading: boolean
  error: string | null
  reload: () => void
}

export function useFetch<T>(
  fetcher: (() => Promise<T>) | null,
  deps: unknown[] = [],
): FetchState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const mountedRef = useRef(true)
  const counterRef = useRef(0)

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  const run = useCallback(async () => {
    if (!fetcher) return
    const id = ++counterRef.current
    setLoading(true)
    setError(null)
    try {
      const result = await fetcher()
      if (mountedRef.current && id === counterRef.current) {
        setData(result)
      }
    } catch (err) {
      if (mountedRef.current && id === counterRef.current) {
        setError(err instanceof Error ? err.message : 'Unknown error')
        setData(null)
      }
    } finally {
      if (mountedRef.current && id === counterRef.current) {
        setLoading(false)
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetcher, ...deps])

  useEffect(() => { run() }, [run])

  return { data, loading, error, reload: run }
}
