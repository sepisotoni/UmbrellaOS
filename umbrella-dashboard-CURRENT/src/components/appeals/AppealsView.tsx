import React, { useState, useEffect } from 'react';
import { api, AppealSchema } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { AppealDetailPanel } from './AppealDetailPanel';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  Scale,
  RefreshCw,
  AlertCircle,
  Clock,
  CheckCircle2,
  XCircle,
  Search,
  ExternalLink,
} from 'lucide-react';

export const AppealsView: React.FC = () => {
  const { selectedAppealId, setSelectedAppealId, navigateToPlayer } = useDashboard();
  const [appeals, setAppeals] = useState<AppealSchema[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAppeals = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getAppeals({
        status: statusFilter === 'all' ? undefined : statusFilter,
        limit: 100,
      });
      setAppeals(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load appeals');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAppeals();
  }, [statusFilter]);

  const selectedAppeal = appeals.find((a) => a.id === selectedAppealId);

  return (
    <div id="umbrella-appeals-view" className="space-y-6">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Appeals Management</span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-purple-950/80 border border-purple-800/40 text-purple-300">
              {appeals.length} Cases
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Review player punishment appeals with on-demand AI evidence synthesis.
          </p>
        </div>

        <button
          id="appeals-refresh-btn"
          onClick={fetchAppeals}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-purple-500/40 hover:text-white transition cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {[
          { id: 'pending', label: 'Pending Review' },
          { id: 'ACCEPTED', label: 'Accepted' },
          { id: 'REJECTED', label: 'Rejected' },
          { id: 'REDUCED', label: 'Sentence Reduced' },
          { id: 'all', label: 'All Cases' },
        ].map((f) => (
          <button
            key={f.id}
            id={`filter-appeal-${f.id}`}
            onClick={() => {
              setStatusFilter(f.id);
              setSelectedAppealId(null);
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold font-mono transition cursor-pointer border ${
              statusFilter === f.id
                ? 'bg-purple-950/80 border-purple-500/50 text-purple-200 shadow-sm'
                : 'bg-[#0d1127] border-[#1e1b4b] text-slate-400 hover:text-slate-200'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
          <div>
            <span className="font-bold">Error loading appeals:</span>
            <p className="mt-0.5 text-rose-200/80">{error}</p>
          </div>
        </div>
      )}

      {/* Active Detail Panel if selected */}
      {selectedAppeal ? (
        <AppealDetailPanel
          appeal={selectedAppeal}
          onClose={() => setSelectedAppealId(null)}
          onRefresh={fetchAppeals}
        />
      ) : (
        /* Appeals Table */
        <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
          {isLoading ? (
            <div className="py-12 text-center text-xs text-slate-500 font-mono">
              Loading appeal cases from database...
            </div>
          ) : appeals.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500 font-mono">
              No appeals found in this category.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-[#1e1b4b] text-slate-400">
                    <th className="pb-3 font-semibold">Appeal ID</th>
                    <th className="pb-3 font-semibold">Player</th>
                    <th className="pb-3 font-semibold">Reason Statement</th>
                    <th className="pb-3 font-semibold">Submitted</th>
                    <th className="pb-3 font-semibold">Status</th>
                    <th className="pb-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e1b4b]/60">
                  {appeals.map((app) => (
                    <tr
                      key={app.id}
                      onClick={() => setSelectedAppealId(app.id)}
                      className="hover:bg-[#121638]/50 transition cursor-pointer group"
                    >
                      <td className="py-3 font-bold text-purple-300">
                        #{app.id.slice(0, 8)}
                      </td>
                      <td className="py-3 text-white font-bold">
                        {app.player_uuid.slice(0, 12)}...
                      </td>
                      <td className="py-3 text-slate-300 max-w-xs truncate font-sans">
                        {app.message}
                      </td>
                      <td className="py-3 text-slate-400">
                        {app.created_at ? new Date(app.created_at).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="py-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                            app.status === 'pending' || app.status === 'PENDING'
                              ? 'bg-amber-950/80 text-amber-300 border border-amber-800/40'
                              : app.status === 'ACCEPTED'
                              ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/40'
                              : 'bg-purple-950/80 text-purple-300 border border-purple-800/40'
                          }`}
                        >
                          {app.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedAppealId(app.id);
                          }}
                          className="inline-flex items-center gap-1 text-[11px] text-purple-400 hover:text-purple-300 underline cursor-pointer"
                        >
                          <span>Review Case</span>
                          <ExternalLink className="h-3 w-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
