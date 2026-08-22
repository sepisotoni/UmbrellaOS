import React, { useState, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { api } from '../../lib/api';
import {
  FileText,
  Search,
  Filter,
  RefreshCw,
  Download,
  AlertCircle,
  CheckCircle2,
  Terminal,
  Clock,
  Layers,
  Sparkles,
  ExternalLink,
  ChevronDown
} from 'lucide-react';

interface AuditLogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'GRIM' | 'DEBUG' | 'AUDIT' | 'COMMAND';
  source: string;
  traceId: string;
  message: string;
  metadata?: Record<string, any>;
}

export const AuditView: React.FC = () => {
  const { servers, addToast } = useDashboard();

  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [levelFilter, setLevelFilter] = useState('ALL');
  const [sourceFilter, setSourceFilter] = useState('ALL');
  const [isLoading, setIsLoading] = useState(false);

  const fetchLiveLogs = async () => {
    setIsLoading(true);
    try {
      const res = await api.getLogs({
        query: searchQuery || undefined,
        level: levelFilter,
        source: sourceFilter !== 'ALL' ? sourceFilter : undefined,
        limit: 100
      });
      if (Array.isArray(res)) {
        setLogs(res.map(r => ({
          id: r.id || `log-${Math.random()}`,
          timestamp: r.timestamp || new Date().toISOString(),
          level: (r.level || 'INFO') as any,
          source: r.source || r.serverName || 'core',
          traceId: r.traceId || `tr_${Math.random().toString(36).substr(2, 9)}`,
          message: r.message,
          metadata: undefined
        })));
      }
    } catch {
      // Backend not connected
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLiveLogs();
  }, [levelFilter, sourceFilter]);

  const filteredLogs = logs.filter(l => {
    const matchesQuery = !searchQuery ||
      l.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.traceId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.source.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesLevel = levelFilter === 'ALL' || l.level === levelFilter;
    const matchesSource = sourceFilter === 'ALL' || l.source === sourceFilter;
    return matchesQuery && matchesLevel && matchesSource;
  });

  const handleExportLogs = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(filteredLogs, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `umbrella-logs-${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    addToast('success', 'Logs Exported', `Downloaded ${filteredLogs.length} structured log events.`);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white font-display">
                Audit & Centralized Logs
              </h1>
              <p className="text-xs text-slate-400">
                Traceable event streams, API admin actions, GrimAC flags, and JVM diagnostic traces.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono">
          <button
            onClick={fetchLiveLogs}
            disabled={isLoading}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700 transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleExportLogs}
            className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500 transition-colors shadow-sm"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-3 bg-[#0c1017] p-3 rounded-xl border border-slate-800 font-mono">
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 font-mono focus:border-cyan-500 focus:outline-none"
          >
            <option value="ALL">All Levels</option>
            <option value="AUDIT">AUDIT</option>
            <option value="GRIM">GRIM</option>
            <option value="WARN">WARN</option>
            <option value="ERROR">ERROR</option>
            <option value="COMMAND">COMMAND</option>
            <option value="INFO">INFO</option>
          </select>

          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 font-mono focus:border-cyan-500 focus:outline-none"
          >
            <option value="ALL">All Sources</option>
            <option value="api-gateway">API Gateway</option>
            <option value="proxy-us-01">Velocity Proxy</option>
            {servers.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        <div className="relative w-full md:w-80">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search message or trace ID..."
            className="w-full rounded-lg border border-slate-800 bg-slate-900/90 pl-9 pr-3 py-1.5 text-xs text-white placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
          />
        </div>
      </div>

      {/* Logs Table */}
      <div className="rounded-xl border border-slate-800 bg-[#0d1117] overflow-hidden shadow-sm font-mono text-xs">
        <div className="divide-y divide-slate-800/60">
          {filteredLogs.length === 0 ? (
            <div className="p-8 text-center text-slate-500">
              No matching log records found in database for the specified filters.
            </div>
          ) : (
            filteredLogs.map(log => {
              const isAudit = log.level === 'AUDIT';
              const isGrim = log.level === 'GRIM';
              const isWarn = log.level === 'WARN';
              const isError = log.level === 'ERROR';

              return (
                <div key={log.id} className="p-3.5 hover:bg-slate-900/40 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="space-y-1 max-w-3xl">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                        isAudit ? 'bg-purple-950 text-purple-300 border border-purple-500/30' :
                        isGrim ? 'bg-rose-950 text-rose-300 border border-rose-500/30' :
                        isWarn ? 'bg-amber-950 text-amber-300 border border-amber-500/30' :
                        isError ? 'bg-red-950 text-red-300 border border-red-500/30' :
                        'bg-slate-800 text-slate-400'
                      }`}>
                        {log.level}
                      </span>
                      <span className="text-[10px] text-cyan-400 bg-slate-900 border border-slate-800 px-1.5 py-0.2 rounded">
                        {log.source}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        Trace: {log.traceId}
                      </span>
                    </div>

                    <p className="text-slate-200 text-xs leading-relaxed mt-1">
                      {log.message}
                    </p>

                    {log.metadata && (
                      <div className="text-[10px] text-slate-500 font-mono">
                        Meta: {JSON.stringify(log.metadata)}
                      </div>
                    )}
                  </div>

                  <div className="text-[10px] text-slate-500 whitespace-nowrap shrink-0">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
