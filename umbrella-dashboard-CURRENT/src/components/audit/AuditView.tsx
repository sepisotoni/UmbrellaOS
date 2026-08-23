import React, { useState, useEffect } from 'react';
import { api, AuditLogEntry } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  ScrollText,
  Filter,
  RefreshCw,
  AlertCircle,
  Search,
  ChevronLeft,
  ChevronRight,
  Shield,
} from 'lucide-react';

export const AuditView: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [actorTypeFilter, setActorTypeFilter] = useState<string>('');
  const [actionFilter, setActionFilter] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const pageSize = 50;

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAuditLogs = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getAuditLogs({
        actor_type: actorTypeFilter || undefined,
        action: actionFilter || undefined,
        limit: pageSize,
        offset: page * pageSize,
      });
      setLogs(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load audit logs');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, [actorTypeFilter, actionFilter, page]);

  return (
    <div id="umbrella-audit-view" className="space-y-6">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Security & Administrative Audit Trail</span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-purple-950/80 border border-purple-800/40 text-purple-300">
              Immutable Log
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Tamper-evident records of all staff actions, automated enforcement, and configuration changes.
          </p>
        </div>

        <button
          id="audit-refresh-btn"
          onClick={fetchAuditLogs}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-purple-500/40 hover:text-white transition cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <label className="text-xs font-mono text-slate-400">Actor Type:</label>
          <select
            value={actorTypeFilter}
            onChange={(e) => {
              setActorTypeFilter(e.target.value);
              setPage(0);
            }}
            className="rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-mono text-white focus:border-purple-500 focus:outline-none"
          >
            <option value="">All Actors</option>
            <option value="STAFF">Staff Member</option>
            <option value="SYSTEM">System / AutoMod</option>
            <option value="AI_COPILOT">AI Copilot</option>
          </select>
        </div>

        <div className="flex items-center gap-2 flex-1 max-w-xs">
          <input
            type="text"
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(0);
            }}
            placeholder="Filter by action (e.g. BAN, UNLINK, APPEAL_CLOSE)..."
            className="w-full rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-mono text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none"
          />
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
          <div>
            <span className="font-bold">Error retrieving audit log records:</span>
            <p className="mt-0.5 text-rose-200/80">{error}</p>
          </div>
        </div>
      )}

      {/* Audit Log Table */}
      <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
        {isLoading ? (
          <div className="py-12 text-center text-xs text-slate-500 font-mono">
            Loading audit records from core...
          </div>
        ) : logs.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500 font-mono">
            No audit log records found for this query.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-[#1e1b4b] text-slate-400">
                  <th className="pb-3 font-semibold">Action</th>
                  <th className="pb-3 font-semibold">Actor</th>
                  <th className="pb-3 font-semibold">Target</th>
                  <th className="pb-3 font-semibold">Details & Metadata</th>
                  <th className="pb-3 font-semibold text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e1b4b]/60">
                {logs.map((entry) => (
                  <tr key={entry.id} className="hover:bg-[#121638]/50 transition">
                    <td className="py-3 font-bold text-purple-300 uppercase">
                      {entry.action}
                    </td>
                    <td className="py-3 text-slate-200">
                      <span className="px-1.5 py-0.5 rounded bg-purple-950/80 text-purple-300 text-[10px] border border-purple-800/40 mr-1.5">
                        {entry.actor_type}
                      </span>
                      <span>{entry.actor_id}</span>
                    </td>
                    <td className="py-3 text-slate-300 font-mono">
                      {entry.target_id || 'System'}
                    </td>
                    <td className="py-3 text-slate-400 max-w-md truncate font-sans text-xs">
                      {typeof entry.details === 'object'
                        ? JSON.stringify(entry.details)
                        : entry.details || '—'}
                    </td>
                    <td className="py-3 text-slate-500 text-[11px] text-right">
                      {entry.created_at ? new Date(entry.created_at).toLocaleString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <div className="mt-4 pt-3 border-t border-[#1e1b4b] flex items-center justify-between text-xs font-mono">
          <div className="text-slate-400">
            Page <span className="text-white font-bold">{page + 1}</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || isLoading}
              className="px-3 py-1.5 rounded-lg border border-[#1e1b4b] bg-[#070914] text-slate-300 hover:text-white disabled:opacity-50 transition cursor-pointer"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={logs.length < pageSize || isLoading}
              className="px-3 py-1.5 rounded-lg border border-[#1e1b4b] bg-[#070914] text-slate-300 hover:text-white disabled:opacity-50 transition cursor-pointer"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
