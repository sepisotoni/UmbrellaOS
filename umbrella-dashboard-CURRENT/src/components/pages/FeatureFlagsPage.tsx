import { useAuth } from '../../context/AuthContext'
import { useFetch } from '../../hooks/useFetch'
import { featureFlags, FeatureFlagRecord } from '../../lib/api'
import { Card, Skeleton, ErrorCard, Badge } from '../ui'
import { useState } from 'react'

export function FeatureFlagsPage() {
  const { token } = useAuth()
  const { data, loading, error, reload } = useFetch<FeatureFlagRecord[]>(
    token ? () => featureFlags.list(token) : null,
    [token],
  )
  const [toggling, setToggling] = useState<string | null>(null)
  const [toggleError, setToggleError] = useState<string | null>(null)

  const handleToggle = async (flag: FeatureFlagRecord) => {
    if (!token) return
    setToggling(flag.id)
    setToggleError(null)
    try {
      await featureFlags.upsert(token, {
        name: flag.name,
        enabled: !flag.enabled,
        description: flag.description,
      })
      reload()
    } catch (err) {
      setToggleError(err instanceof Error ? err.message : 'Toggle failed')
    } finally {
      setToggling(null)
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-100">Feature Flags</h1>

      {toggleError && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
          {toggleError}
        </div>
      )}

      {error && <ErrorCard message={error} onRetry={reload} />}
      {loading && (
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-14 w-full" />)}
        </div>
      )}

      {!loading && !error && (data ?? []).length === 0 && (
        <Card className="text-center py-8 text-slate-500 text-sm">No feature flags configured.</Card>
      )}

      <div className="space-y-2">
        {(data ?? []).map((flag) => (
          <div
            key={flag.id}
            className="rounded-xl border border-white/[0.07] bg-white/[0.03] px-4 py-3 flex items-center justify-between"
          >
            <div>
              <p className="text-sm font-medium text-slate-200 font-mono">{flag.name}</p>
              {flag.description && (
                <p className="text-xs text-slate-500 mt-0.5">{flag.description}</p>
              )}
            </div>
            <button
              onClick={() => handleToggle(flag)}
              disabled={toggling === flag.id}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none disabled:opacity-50 ${
                flag.enabled ? 'bg-violet-500' : 'bg-white/10'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow ring-0 transition-transform duration-200 ${
                  flag.enabled ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
