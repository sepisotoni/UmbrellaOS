import React, { useState, useEffect, useRef } from 'react';
import { api, ServerRecord } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  Terminal,
  Send,
  AlertCircle,
  Server,
  Trash2,
} from 'lucide-react';

export const ConsoleView: React.FC = () => {
  const { selectedServerId, setSelectedServerId } = useDashboard();
  const [servers, setServers] = useState<ServerRecord[]>([]);
  const [activeServerId, setActiveServerId] = useState<string>('');
  const [serversLoading, setServersLoading] = useState(true);
  const [serverLoadError, setServerLoadError] = useState<string | null>(null);
  const [commandInput, setCommandInput] = useState<string>('');
  const [logs, setLogs] = useState<string[]>([]);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [streamMode, setStreamMode] = useState<'live' | 'plugin' | 'none'>('none');
  const wsRef = useRef<WebSocket | null>(null);
  const terminalEndRef = useRef<HTMLDivElement | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const seenLinesRef = useRef<Set<string>>(new Set());

  // Fetch servers list for selector
  useEffect(() => {
    let mounted = true;
    api.getServers()
      .then((result) => {
        if (!mounted) return;
        const availableServers = Array.isArray(result) ? result : [];
        setServers(availableServers);
        setServerLoadError(null);
        const preferred = availableServers.some(
          server => server.id === selectedServerId,
        )
          ? selectedServerId
          : availableServers[0]?.id ?? '';
        setActiveServerId(preferred);
        setSelectedServerId(preferred);
      })
      .catch((error: unknown) => {
        if (!mounted) return;
        setServerLoadError(
          error instanceof Error ? error.message : 'Unexpected API error',
        );
      })
      .finally(() => {
        if (mounted) setServersLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (selectedServerId && servers.some(server => server.id === selectedServerId)) {
      setActiveServerId(selectedServerId);
    }
  }, [selectedServerId, servers]);

  // Start plugin-log polling fallback (called when WS is error/disconnected)
  const startPolling = (serverId: string) => {
    if (pollRef.current) return; // already polling
    setStreamMode('plugin');
    pollRef.current = setInterval(async () => {
      try {
        const data = await api.getPluginConsoleLogs(serverId, 100);
        if (data && data.lines) {
          setLogs((prev) => {
            const newLines: string[] = [];
            data.lines.forEach(({ ts, line }) => {
              const key = `${ts}::${line}`;
              if (!seenLinesRef.current.has(key)) {
                seenLinesRef.current.add(key);
                newLines.push(`[${ts.slice(11, 19)}] ${line}`);
              }
            });
            return newLines.length > 0 ? [...prev, ...newLines] : prev;
          });
        }
      } catch {
        // silently ignore poll errors — WS is already down
      }
    }, 3000);
  };

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setStreamMode('none');
  };

  // Connect WebSocket on mount & when activeServerId changes; disconnect on unmount
  useEffect(() => {
    if (
      serversLoading
      || !servers.some(server => server.id === activeServerId)
    ) return;

    stopPolling();
    seenLinesRef.current = new Set();

    setLogs((prev) => [
      ...prev,
      `[UmbrellaOS Console] Initializing real-time telemetry stream for ${activeServerId}...`,
    ]);
    setWsStatus('connecting');
    setStreamMode('none');

    let disposed = false;
    const wsUrl = api.getServerConsoleWebSocketUrl(activeServerId);
    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (disposed) return;
        setWsStatus('connected');
        setStreamMode('live');
        stopPolling();
        setLogs((prev) => [
          ...prev,
          `[UmbrellaOS Console] Connected to ${activeServerId} terminal stream.`,
        ]);
      };

      ws.onmessage = (event) => {
        if (disposed) return;
        setLogs((prev) => [...prev, event.data]);
      };

      ws.onerror = () => {
        if (disposed) return;
        setWsStatus('error');
        setLogs((prev) => [
          ...prev,
          `[UmbrellaOS Console] WebSocket unavailable — switching to plugin log polling.`,
        ]);
        startPolling(activeServerId);
      };

      ws.onclose = () => {
        if (disposed) return;
        setWsStatus('disconnected');
        setLogs((prev) => [
          ...prev,
          `[UmbrellaOS Console] Stream disconnected — switching to plugin log polling.`,
        ]);
        startPolling(activeServerId);
      };
    } catch (err: any) {
      if (disposed) return;
      setWsStatus('error');
      setLogs((prev) => [
        ...prev,
        `[UmbrellaOS Console] WebSocket unavailable — switching to plugin log polling.`,
      ]);
      startPolling(activeServerId);
    }

    return () => {
      disposed = true;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      stopPolling();
    };
  }, [activeServerId, servers, serversLoading]);

  // Auto scroll to bottom
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleSendCommand = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      !servers.some(server => server.id === activeServerId)
      || !commandInput.trim()
    ) return;

    const cmd = commandInput.trim();
    setCommandInput('');
    setLogs((prev) => [...prev, `> ${cmd}`]);

    // Send via WebSocket if open
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: cmd }));
    } else {
      // Or fallback to HTTP command dispatch
      try {
        await api.sendServerCommand(activeServerId, cmd);
        setLogs((prev) => [...prev, `[HTTP Dispatch] Command delivered to ${activeServerId}.`]);
      } catch (err: any) {
        setLogs((prev) => [
          ...prev,
          `[Error] Command failed to dispatch: ${err.message}`,
        ]);
      }
    }
  };

  const handleClearLogs = () => {
    setLogs([`[UmbrellaOS Console] Terminal buffer cleared.`]);
  };

  return (
    <div id="umbrella-console-view" className="space-y-4">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Server Terminal & Console</span>
            <span
              className={`text-xs px-2 py-0.5 rounded font-mono font-bold border ${
                wsStatus === 'connected'
                  ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/40'
                  : wsStatus === 'connecting'
                  ? 'bg-amber-950/80 text-amber-300 border-amber-800/40'
                  : 'bg-rose-950/80 text-rose-300 border-rose-800/40'
              }`}
            >
              {wsStatus.toUpperCase()}
            </span>
            {streamMode === 'live' && (
              <span className="text-xs px-2 py-0.5 rounded font-mono border bg-emerald-950/60 text-emerald-300 border-emerald-800/40">
                ⚡ Live stream
              </span>
            )}
            {streamMode === 'plugin' && (
              <span className="text-xs px-2 py-0.5 rounded font-mono border bg-purple-950/60 text-purple-300 border-purple-800/40">
                🔌 Plugin stream
              </span>
            )}
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time live logs, standard output, and interactive administrative command execution.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Server Selector */}
          <div className="flex items-center gap-2">
            <Server className="h-4 w-4 text-purple-400" />
            <select
              id="console-server-select"
              value={activeServerId}
              onChange={(e) => {
                setActiveServerId(e.target.value);
                setSelectedServerId(e.target.value);
              }}
              disabled={serversLoading || servers.length === 0}
              className="rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-mono text-white focus:border-purple-500 focus:outline-none cursor-pointer"
            >
              {servers.length > 0 ? (
                servers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.id})
                  </option>
                ))
              ) : (
                <option value="">
                  {serversLoading ? 'Loading servers…' : 'No connected servers'}
                </option>
              )}
            </select>
          </div>

          <button
            onClick={handleClearLogs}
            className="inline-flex items-center gap-1 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs text-slate-400 hover:text-white transition cursor-pointer"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {serverLoadError && (
        <div role="alert" className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-950/30 px-3 py-2 text-xs text-rose-200">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>Could not load servers: {serverLoadError}</span>
        </div>
      )}
      {!serversLoading && !serverLoadError && servers.length === 0 && (
        <div className="rounded-lg border border-[#293252] bg-[#0d1127] px-3 py-2 text-xs text-slate-400">
          No connected servers are available. The console will appear after a server registers with Core.
        </div>
      )}

      {/* Terminal Display */}
      <div className="rounded-xl border border-[#1e1b4b] bg-[#04060c] p-4 shadow-2xl font-mono text-xs text-slate-200">
        <div className="h-[520px] overflow-y-auto space-y-1 select-text scrollbar-thin scrollbar-thumb-purple-900 scrollbar-track-transparent">
          {!activeServerId && (
            <div className="flex h-full items-center justify-center text-slate-500">
              {serversLoading ? 'Loading server console…' : 'Select a connected server to view its console.'}
            </div>
          )}
          {logs.map((log, index) => {
            const isCommand = log.startsWith('>');
            const isError = log.toLowerCase().includes('error') || log.toLowerCase().includes('exception');
            const isWarn = log.toLowerCase().includes('warn');
            const isInfo = log.startsWith('[UmbrellaOS');

            return (
              <div
                key={index}
                className={`leading-relaxed break-all ${
                  isCommand
                    ? 'text-purple-300 font-bold'
                    : isError
                    ? 'text-rose-400'
                    : isWarn
                    ? 'text-amber-300'
                    : isInfo
                    ? 'text-purple-400/90'
                    : 'text-slate-300'
                }`}
              >
                {log}
              </div>
            );
          })}
          <div ref={terminalEndRef} />
        </div>

        {/* Command Input Bar */}
        <form
          onSubmit={handleSendCommand}
          className="mt-4 pt-3 border-t border-[#1e1b4b] flex items-center gap-2"
        >
          <span className="text-purple-400 font-bold">{'>'}</span>
          <input
            id="console-command-input"
            type="text"
            value={commandInput}
            onChange={(e) => setCommandInput(e.target.value)}
            placeholder={activeServerId ? `Execute Minecraft command on ${activeServerId}...` : 'Connect a server to enable commands'}
            disabled={!servers.some(server => server.id === activeServerId)}
            className="flex-1 bg-transparent text-white placeholder-slate-600 focus:outline-none text-xs font-mono"
          />
          <button
            id="submit-console-command"
            type="submit"
            disabled={!servers.some(server => server.id === activeServerId) || !commandInput.trim()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-purple-500/50 bg-purple-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-purple-500 transition disabled:opacity-50 cursor-pointer"
          >
            <Send className="h-3.5 w-3.5" />
            <span>Send</span>
          </button>
        </form>
      </div>
    </div>
  );
};
