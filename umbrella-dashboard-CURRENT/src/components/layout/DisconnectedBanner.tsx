import { WifiOff } from 'lucide-react'

export function DisconnectedBanner() {
  return (
    <div className="flex items-center gap-3 bg-red-600/20 border-b border-red-500/40 px-4 py-2.5">
      <WifiOff className="h-4 w-4 text-red-400 shrink-0" />
      <span className="text-xs font-medium text-red-300">
        DISCONNECTED — Cannot reach UmbrellaOS Core at{' '}
        <span className="font-mono">{import.meta.env.VITE_UMBRELLA_CORE_URL ?? 'localhost:8000'}</span>.
        Data shown may be stale.
      </span>
    </div>
  )
}
