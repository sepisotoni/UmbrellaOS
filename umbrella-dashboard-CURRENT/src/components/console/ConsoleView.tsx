import React, { useState, useRef, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { ConsoleLogMessage } from '../../types/dashboard';
import { api } from '../../lib/api';
import {
  Terminal,
  Send,
  Trash2,
  Download,
  Play,
  Pause,
  Filter,
  Server,
  Activity,
  ShieldAlert,
  CornerDownLeft,
  Flame,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Radio,
  Wifi,
  WifiOff
} from 'lucide-react';

interface ConsoleViewProps {
  onQuickBan: (playerName: string) => void;
}

export const ConsoleView: React.FC<ConsoleViewProps> = ({ onQuickBan }) => {
  const {
    servers,
    selectedServerId,
    setSelectedServerId,
    consoleLogs,
    executeConsoleCommand,
    restartServer,
    stopServer,
    startServer,
    currentUser,
    backendStatus
  } = useDashboard();

  const [inputCommand, setInputCommand] = useState('');
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);
  const [activeFilter, setActiveFilter] = useState<string>('ALL');
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'offline'>('connecting');
  const [liveWsLogs, setLiveWsLogs] = useState<ConsoleLogMessage[]>([]);

  const terminalEndRef = useRef<HTMLDivElement>(null);
  const selectedServer = servers.find(s => s.id === selectedServerId) || servers[0];

  // Real WebSocket Console connection to /api/v1/hosting/servers/{id}/console
  useEffect(() => {
    if (!selectedServerId) return;

    setWsStatus('connecting');
    const ws = api.createConsoleWebSocket(
      selectedServerId,
      (data: string) => {
        try {
          const parsed = typeof data === 'string' && data.startsWith('{') ? JSON.parse(data) : null;
          const newEntry: ConsoleLogMessage = {
            id: `ws-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
            timestamp: new Date().toLocaleTimeString(),
            serverId: selectedServerId,
            serverName: selectedServer?.name || selectedServerId,
            level: (parsed?.level as any) || 'INFO',
            message: parsed?.message || data,
            rawAnsi: data
          };
          setLiveWsLogs(prev => [...prev.slice(-400), newEntry]);
        } catch {
          const newEntry: ConsoleLogMessage = {
            id: `ws-${Date.now()}`,
            timestamp: new Date().toLocaleTimeString(),
            serverId: selectedServerId,
            serverName: selectedServer?.name || selectedServerId,
            level: 'INFO',
            message: data
          };
          setLiveWsLogs(prev => [...prev.slice(-400), newEntry]);
        }
      },
      () => {
        setWsStatus('offline');
      },
      () => {
        setWsStatus('offline');
      }
    );

    if (ws) {
      ws.onopen = () => setWsStatus('connected');
    } else {
      setWsStatus('offline');
    }

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [selectedServerId, selectedServer?.name]);

  // Combined logs (real WS logs + contextual server logs)
  const combinedLogs = [...consoleLogs, ...liveWsLogs];

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [combinedLogs, autoScroll, selectedServerId]);

  const handleCommandSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputCommand.trim() || !selectedServer) return;

    executeConsoleCommand(selectedServer.id, inputCommand.trim());
    setCommandHistory(prev => [inputCommand.trim(), ...prev].slice(0, 50));
    setHistoryIndex(-1);
    setInputCommand('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (commandHistory.length > 0) {
        const nextIdx = Math.min(historyIndex + 1, commandHistory.length - 1);
        setHistoryIndex(nextIdx);
        setInputCommand(commandHistory[nextIdx]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const nextIdx = historyIndex - 1;
        setHistoryIndex(nextIdx);
        setInputCommand(commandHistory[nextIdx]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setInputCommand('');
      }
    }
  };

  const filteredLogs = combinedLogs.filter(log => {
    const matchesServer = !selectedServer || log.serverId === selectedServer.id || log.serverId === 'all';
    const matchesLevel = activeFilter === 'ALL' || log.level === activeFilter;
    const matchesSearch = !searchFilter || log.message.toLowerCase().includes(searchFilter.toLowerCase());
    return matchesServer && matchesLevel && matchesSearch;
  });

  const getLevelColor = (level: ConsoleLogMessage['level']) => {
    switch (level) {
      case 'ERROR': return 'text-rose-400 font-bold';
      case 'WARN': return 'text-amber-400 font-semibold';
      case 'GRIM': return 'text-purple-400 font-bold';
      case 'CHAT': return 'text-emerald-300';
      case 'COMMAND': return 'text-cyan-400';
      case 'DEBUG': return 'text-slate-500';
      default: return 'text-slate-200';
    }
  };

  const downloadLogFile = () => {
    const textContent = filteredLogs.map(l => `[${l.timestamp}] [${l.level}] [${l.serverName}]: ${l.message}`).join('\n');
    const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedServer?.id || 'cluster'}-console-${Date.now()}.log`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4 pb-8">
      {/* Top Header & Server Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Terminal className="h-6 w-6 text-cyan-400" />
            <h1 className="text-xl font-bold tracking-tight text-white font-display">Live Node Terminal</h1>
            <span className="rounded-md bg-slate-800 border border-slate-700 px-2 py-0.5 text-xs font-mono text-cyan-300">
              Plugin Log Stream
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Real-time stdout/stderr pipe proxied to node runtime with colorized log demuxing.
          </p>
        </div>

        {/* Server Switcher Pill Selector */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 max-w-full">
          {servers.map(server => {
            const isCurrent = selectedServer && server.id === selectedServer.id;
            return (
              <button
                key={server.id}
                onClick={() => setSelectedServerId(server.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all border ${
                  isCurrent
                    ? 'bg-cyan-950/80 border-cyan-500/50 text-cyan-300 shadow-sm'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                <span className={`h-2 w-2 rounded-full ${
                  server.status === 'online' ? 'bg-emerald-400' :
                  server.status === 'warning' ? 'bg-amber-400' :
                  server.status === 'restarting' ? 'bg-cyan-400 animate-spin' :
                  'bg-rose-500'
                }`} />
                <span className="font-mono">{server.name}</span>
                <span className="font-mono text-[10px] text-slate-500">({server.playersCount}p)</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Server Status Ribbon */}
      {selectedServer && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-xs">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-cyan-400" />
              <span className="font-bold text-white font-mono">{selectedServer.name}</span>
              <span className="text-slate-500">|</span>
              <span className="font-mono text-slate-300">{selectedServer.version}</span>
            </div>

            <div className="hidden sm:flex items-center gap-3 font-mono text-[11px] text-slate-400">
              <span>TPS: <strong className={selectedServer.tps >= 19.5 ? 'text-emerald-400' : 'text-amber-400'}>{selectedServer.tps}</strong></span>
              <span>RAM: <strong className="text-slate-200">{selectedServer.memoryMb}MB</strong> / {selectedServer.maxMemoryMb}MB</span>
              <span>Node: <strong className="text-slate-200">{selectedServer.node}</strong></span>
            </div>
          </div>

          {/* WebSocket Real-time Status & Quick Actions */}
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono border font-semibold ${
              wsStatus === 'connected' ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30' :
              wsStatus === 'connecting' ? 'bg-cyan-950/60 text-cyan-300 border-cyan-500/30' :
              'bg-slate-800 text-slate-400 border-slate-700'
            }`}>
              {wsStatus === 'connected' ? <Wifi className="h-3 w-3 text-emerald-400" /> : <WifiOff className="h-3 w-3 text-slate-400" />}
              <span>{wsStatus === 'connected' ? 'WS STREAM ACTIVE' : 'LOG BUFFERED'}</span>
            </span>

            <button
              onClick={() => restartServer(selectedServer.id)}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors font-medium text-xs font-mono"
              title="Restart server container"
            >
              <RefreshCw className="h-3 w-3" />
              <span>Restart</span>
            </button>
            
            {selectedServer.status === 'online' ? (
              <button
                onClick={() => stopServer(selectedServer.id)}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-500/30 transition-colors font-medium text-xs font-mono"
              >
                <Pause className="h-3 w-3" />
                <span>Stop</span>
              </button>
            ) : (
              <button
                onClick={() => startServer(selectedServer.id)}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-500/30 transition-colors font-medium text-xs font-mono"
              >
                <Play className="h-3 w-3" />
                <span>Start</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Terminal Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
          {['ALL', 'INFO', 'WARN', 'ERROR', 'GRIM', 'CHAT', 'COMMAND'].map(filter => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`px-2.5 py-1 rounded text-[11px] font-mono font-medium transition-colors ${
                activeFilter === filter
                  ? 'bg-slate-700 text-white font-bold'
                  : 'bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              {filter}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Regex / Text filter..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="rounded border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs text-white placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none w-44 font-mono"
          />

          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-2.5 py-1 rounded border text-[11px] font-mono font-medium transition-colors ${
              autoScroll
                ? 'border-cyan-500/40 bg-cyan-950/40 text-cyan-300'
                : 'border-slate-800 bg-slate-900 text-slate-400'
            }`}
          >
            Auto-scroll: {autoScroll ? 'ON' : 'OFF'}
          </button>

          <button
            onClick={downloadLogFile}
            className="flex items-center gap-1 px-2.5 py-1 rounded border border-slate-800 bg-slate-900 text-slate-400 hover:text-white transition-colors font-mono"
            title="Download Log File"
          >
            <Download className="h-3 w-3" />
            <span className="hidden sm:inline">Export</span>
          </button>
        </div>
      </div>

      {/* Main Terminal Window */}
      <div className="relative rounded-xl border border-slate-800 bg-[#07090e] shadow-2xl overflow-hidden font-mono text-xs flex flex-col h-[520px]">
        {/* Terminal Title Bar */}
        <div className="flex items-center justify-between border-b border-slate-800/80 bg-[#0c1017] px-4 py-2 text-slate-400 select-none">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-rose-500/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
            <span className="ml-2 font-mono text-[11px] text-slate-400">
              umbrella-core:~/{selectedServer?.id || 'cluster'}/logs/latest.log
            </span>
          </div>

          <div className="flex items-center gap-2 text-[10px] text-slate-500">
            <span>{filteredLogs.length} events buffered</span>
          </div>
        </div>

        {/* Console Log Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-1 select-text scrollbar-thin scrollbar-thumb-slate-800">
          {filteredLogs.length === 0 ? (
            <div className="text-center py-16 text-slate-500 font-mono">
              No log messages matching filter criteria for {selectedServer?.name || 'this server'}.
            </div>
          ) : (
            filteredLogs.map(log => (
              <div
                key={log.id}
                className="flex items-start gap-2 hover:bg-slate-900/60 px-1 py-0.5 rounded transition-colors group"
              >
                <span className="text-slate-600 select-none shrink-0 font-mono text-[11px]">
                  [{log.timestamp}]
                </span>
                
                <span className={`shrink-0 font-mono text-[11px] px-1 py-0.2 rounded ${
                  log.level === 'ERROR' ? 'bg-rose-950/80 text-rose-300 font-bold' :
                  log.level === 'WARN' ? 'bg-amber-950/80 text-amber-300' :
                  log.level === 'GRIM' ? 'bg-purple-950/80 text-purple-300 font-bold' :
                  log.level === 'CHAT' ? 'bg-emerald-950/80 text-emerald-300' :
                  log.level === 'COMMAND' ? 'bg-cyan-950/80 text-cyan-300' :
                  'text-slate-400'
                }`}>
                  [{log.level}]
                </span>

                <span className={`flex-1 break-all leading-relaxed ${getLevelColor(log.level)}`}>
                  {log.message}
                </span>

                {/* Quick Action when playerName in log */}
                {log.level === 'GRIM' && (
                  <button
                    onClick={() => {
                      const match = log.message.match(/Flagged:?\s*([a-zA-Z0-9_]{3,16})/);
                      if (match && match[1]) onQuickBan(match[1]);
                      else onQuickBan('TargetPlayer');
                    }}
                    className="opacity-0 group-hover:opacity-100 px-1.5 py-0.5 rounded bg-rose-950 border border-rose-500/40 text-rose-300 text-[10px] shrink-0 hover:bg-rose-900 transition-opacity"
                  >
                    Quick Ban
                  </button>
                )}
              </div>
            ))
          )}
          <div ref={terminalEndRef} />
        </div>

        {/* Interactive Terminal Command Input Bar */}
        <form
          onSubmit={handleCommandSubmit}
          className="border-t border-slate-800/80 bg-[#0c1017] p-2.5 flex items-center gap-2"
        >
          <div className="flex items-center gap-1.5 text-cyan-400 font-mono text-xs pl-2 select-none">
            <span>&gt;</span>
          </div>
          
          <input
            type="text"
            value={inputCommand}
            onChange={(e) => setInputCommand(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Execute command on ${selectedServer?.name || 'server'} (e.g. /tps, /grim check <player>, /umbrella reload)...`}
            className="flex-1 bg-transparent text-slate-100 font-mono text-xs focus:outline-none placeholder:text-slate-600"
          />

          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px] text-slate-500 font-mono hidden md:inline">
              <kbd className="rounded border border-slate-700 bg-slate-800 px-1">↑</kbd> <kbd className="rounded border border-slate-700 bg-slate-800 px-1">↓</kbd> history
            </span>
            <button
              type="submit"
              disabled={!inputCommand.trim() || !selectedServer}
              className="flex items-center gap-1 rounded bg-cyan-600 px-3 py-1 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <span>Send</span>
              <Send className="h-3 w-3" />
            </button>
          </div>
        </form>
      </div>

      {/* Quick Command Action Chips */}
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
        <span className="font-semibold text-slate-300 font-mono">Quick Shortcuts:</span>
        {[
          { label: 'Check TPS (/tps)', cmd: 'tps' },
          { label: 'Garbage Collection (/gc)', cmd: 'gc' },
          { label: 'GrimAC Status (/grim check)', cmd: 'grim check' },
          { label: 'Reload Umbrella (/umbrella reload)', cmd: 'umbrella reload' },
          { label: 'Purge Dropped Items', cmd: 'kill @e[type=item]' },
          { label: 'Save World (/save-all)', cmd: 'save-all' }
        ].map(chip => (
          <button
            key={chip.cmd}
            onClick={() => selectedServer && executeConsoleCommand(selectedServer.id, chip.cmd)}
            className="rounded-md border border-slate-800 bg-slate-900/80 px-2.5 py-1 text-[11px] font-mono text-slate-300 hover:border-cyan-500/40 hover:text-cyan-300 transition-colors"
          >
            {chip.label}
          </button>
        ))}
      </div>
    </div>
  );
};
