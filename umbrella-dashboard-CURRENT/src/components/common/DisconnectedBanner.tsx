import React from 'react';
import { AlertTriangle, RefreshCw, ServerOff } from 'lucide-react';
import { useDashboard } from '../../context/DashboardContext';
import { api } from '../../lib/api';

export const DisconnectedBanner: React.FC = () => {
  const { isDisconnected, checkHealth } = useDashboard();
  const [isRetrying, setIsRetrying] = React.useState(false);

  if (!isDisconnected) return null;

  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      // Use fetch with cache: 'no-store' to bypass the browser's cached
      // CORS preflight failure (browsers cache preflight results for up to
      // Access-Control-Max-Age seconds).
      await fetch(`${api.getBaseUrl()}/health`, {
        method: 'GET',
        cache: 'no-store',
        headers: { 'X-Cache-Bust': Date.now().toString() },
      });
    } catch {
      // ignore — checkHealth below will update isDisconnected state
    }
    await checkHealth();
    setIsRetrying(false);
  };

  return (
    <div
      id="umbrella-disconnected-banner"
      className="mb-6 w-full rounded-xl border border-rose-500/50 bg-rose-950/80 p-4 text-rose-200 shadow-xl backdrop-blur-md"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-start sm:items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-rose-900/60 border border-rose-500/40 text-rose-400">
            <ServerOff className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 font-bold text-white text-sm">
              <span>DISCONNECTED FROM CORE BACKEND</span>
              <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-mono bg-rose-900/80 text-rose-300 border border-rose-700/50 uppercase">
                Offline
              </span>
            </div>
            <p className="text-xs text-rose-300/90 mt-0.5">
              Unable to reach FastAPI Core (<span className="font-mono text-white">GET /health</span> failed). Live data cannot be updated until the connection is restored.
            </p>
          </div>
        </div>

        <button
          id="retry-connection-button"
          onClick={handleRetry}
          disabled={isRetrying}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-rose-500/40 bg-rose-900/40 px-3.5 py-1.5 text-xs font-semibold text-white transition hover:bg-rose-800/60 active:scale-95 disabled:opacity-50 cursor-pointer"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
          <span>{isRetrying ? 'Testing Connection...' : 'Retry Connection'}</span>
        </button>
      </div>
    </div>
  );
};
