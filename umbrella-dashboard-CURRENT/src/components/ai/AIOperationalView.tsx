import React, { useState, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import api from '../../lib/api';
import {
  Sparkles,
  Send,
  Flame,
  FileText,
  Bot,
  User,
  Activity,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
} from 'lucide-react';

const RISK_BADGE: Record<string, string> = {
  LOW: 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30',
  MEDIUM: 'bg-amber-950/60 text-amber-300 border-amber-500/30',
  HIGH: 'bg-orange-950/60 text-orange-300 border-orange-500/30',
  CRITICAL: 'bg-rose-950/60 text-rose-300 border-rose-500/30',
};

export const AIOperationalView: React.FC = () => {
  const {
    copilotMessages,
    sendCopilotPrompt,
    servers,
    selectedServerId,
    addToast,
  } = useDashboard();

  type AISection = 'copilot' | 'tasks' | 'crash-risk';
  const [activeSection, setActiveSection] = useState<AISection>('copilot');
  const [inputPrompt, setInputPrompt] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  // AI task queue — fetched locally
  const [aiTasks, setAiTasks] = useState<any[]>([]);
  const [tasksLoading, setTasksLoading] = useState(false);

  useEffect(() => {
    if (activeSection !== 'tasks') return;
    let cancelled = false;
    const fetchTasks = async () => {
      setTasksLoading(true);
      try {
        const data = await api.getAITasks();
        if (!cancelled) setAiTasks(data);
      } catch {
        // silently fail — backend may not have tasks
      } finally {
        if (!cancelled) setTasksLoading(false);
      }
    };
    fetchTasks();
    return () => { cancelled = true; };
  }, [activeSection]);

  // Crash risk state
  const [crashRisk, setCrashRisk] = useState<any>(null);
  const [crashRiskLoading, setCrashRiskLoading] = useState(false);
  const [crashRiskError, setCrashRiskError] = useState<string | null>(null);

  useEffect(() => {
    if (activeSection !== 'crash-risk') return;
    const serverId = selectedServerId || (servers[0]?.id ?? '');
    if (!serverId) return;

    let cancelled = false;
    const fetchRisk = async () => {
      setCrashRiskLoading(true);
      setCrashRiskError(null);
      try {
        const data = await api.getCrashRisk(serverId);
        if (!cancelled) setCrashRisk(data);
      } catch (err: any) {
        if (!cancelled) setCrashRiskError(err?.message || 'Crash risk endpoint unavailable.');
      } finally {
        if (!cancelled) setCrashRiskLoading(false);
      }
    };
    fetchRisk();
    return () => { cancelled = true; };
  }, [activeSection, selectedServerId, servers]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputPrompt.trim() || isTyping) return;
    const query = inputPrompt.trim();
    setInputPrompt('');
    setIsTyping(true);
    await sendCopilotPrompt(query);
    setIsTyping(false);
  };

  const samplePrompts = [
    "Why is any instance dropping TPS below 18?",
    "Check alt accounts and client brand for connected players",
    "Analyze recent combat violation patterns across proxy routes",
    "How many players are online on proxies?",
    "Recommend JVM memory flags for high player-count lobby nodes"
  ];

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight font-display">
              Operational Intelligence & AI Governance
            </h1>
            <p className="text-xs text-slate-400">
              Copilot chat, AI task queue, and crash risk assessment
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 font-mono">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs text-emerald-400 font-semibold">AI Backend Active</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto">
        <button
          onClick={() => setActiveSection('copilot')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
            activeSection === 'copilot'
              ? 'bg-slate-800 text-cyan-400 border border-slate-700'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <Bot className="h-3.5 w-3.5" />
          <span>Incident Copilot</span>
        </button>

        <button
          onClick={() => setActiveSection('tasks')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
            activeSection === 'tasks'
              ? 'bg-slate-800 text-indigo-400 border border-slate-700'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <FileText className="h-3.5 w-3.5" />
          <span>AI Task Queue</span>
          {aiTasks.length > 0 && (
            <span className="font-mono text-[10px] bg-indigo-950/80 text-indigo-300 px-1.5 rounded border border-indigo-500/30">
              {aiTasks.filter((t: any) => t.status === 'PENDING' || t.status === 'RUNNING').length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveSection('crash-risk')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
            activeSection === 'crash-risk'
              ? 'bg-slate-800 text-amber-400 border border-slate-700'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <Flame className="h-3.5 w-3.5" />
          <span>Crash Risk</span>
        </button>
      </div>

      {/* Copilot Chat */}
      {activeSection === 'copilot' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3 flex flex-col h-[580px] rounded-xl border border-slate-800 bg-[#0c1017] shadow-lg overflow-hidden">
            <div className="flex-1 overflow-y-auto p-4 space-y-4 font-sans text-xs">
              {copilotMessages.map((msg: any) => {
                const isAssistant = msg.role === 'assistant';
                return (
                  <div key={msg.id} className={`flex items-start gap-3 ${isAssistant ? '' : 'flex-row-reverse'}`}>
                    <div className={`h-8 w-8 rounded-lg flex items-center justify-center shrink-0 ${
                      isAssistant
                        ? 'bg-cyan-950/60 border border-cyan-500/40 text-cyan-300'
                        : 'bg-indigo-950/60 border border-indigo-500/40 text-indigo-300'
                    }`}>
                      {isAssistant ? <Sparkles className="h-4 w-4" /> : <User className="h-4 w-4" />}
                    </div>
                    <div className={`max-w-2xl rounded-xl p-4 leading-relaxed ${
                      isAssistant
                        ? 'bg-slate-900/90 border border-slate-800 text-slate-200'
                        : 'bg-cyan-950/40 border border-cyan-500/30 text-white'
                    }`}>
                      <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5 mb-2 font-mono text-[10px]">
                        <span className="font-bold text-slate-400">{isAssistant ? 'Umbrella AI Copilot' : 'Administrator'}</span>
                        <span className="text-slate-500">{msg.timestamp}</span>
                      </div>
                      <div className="whitespace-pre-wrap font-mono text-[12px]">{msg.content}</div>
                    </div>
                  </div>
                );
              })}
              {isTyping && (
                <div className="flex items-center gap-2 text-xs text-cyan-400 font-mono italic">
                  <Sparkles className="h-3.5 w-3.5 animate-spin" />
                  <span>Umbrella AI is processing your query...</span>
                </div>
              )}
            </div>
            <form onSubmit={handleSend} className="p-3 border-t border-slate-800 bg-slate-950/80 flex items-center gap-2">
              <input
                type="text"
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                placeholder="Ask about TPS lag, player suspicion, or server configs..."
                className="flex-1 rounded-xl border border-slate-700 bg-[#0c1017] px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
              />
              <button
                type="submit"
                disabled={!inputPrompt.trim() || isTyping}
                className="rounded-xl bg-cyan-600 px-5 py-2.5 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors flex items-center gap-1.5 font-mono"
              >
                <Send className="h-3.5 w-3.5" />
                <span>Ask</span>
              </button>
            </form>
          </div>

          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-4 space-y-2.5">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">Suggested Inquiries</h3>
              <div className="space-y-1.5">
                {samplePrompts.map(p => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setInputPrompt(p)}
                    className="w-full text-left p-2 rounded-lg border border-slate-800 bg-slate-900/60 hover:border-cyan-500/40 text-[11px] text-slate-300 hover:text-cyan-200 transition-colors font-mono"
                  >
                    "{p}"
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-4 space-y-2 text-xs font-mono">
              <div className="font-bold text-white flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5 text-emerald-400" />
                <span>Context Grounding</span>
              </div>
              <div className="text-[11px] text-slate-400 space-y-1">
                <p>• {servers.length} instances streamed</p>
                <p>• Real-time GrimAC packet logs</p>
                <p>• PostgreSQL replica state store</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Task Queue */}
      {activeSection === 'tasks' && (
        <div className="space-y-4">
          {tasksLoading ? (
            <div className="p-8 rounded-xl border border-slate-800 bg-[#0c1017] text-center text-xs text-slate-400 font-mono animate-pulse">
              Loading AI tasks...
            </div>
          ) : (!aiTasks || aiTasks.length === 0) ? (
            <div className="p-8 rounded-xl border border-slate-800 bg-[#0c1017] text-center text-xs text-slate-500 font-mono">
              No AI tasks in queue.
            </div>
          ) : (
            aiTasks.map((task: any) => (
              <div key={task.id} className="rounded-xl border border-slate-800 bg-[#0c1017] p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-bold text-white font-mono">{task.taskType}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                      task.status === 'PENDING' ? 'bg-amber-950/60 text-amber-300 border-amber-500/30' :
                      task.status === 'RUNNING' ? 'bg-cyan-950/60 text-cyan-300 border-cyan-500/30' :
                      task.status === 'COMPLETED' || task.status === 'APPROVED' ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30' :
                      'bg-rose-950/60 text-rose-300 border-rose-500/30'
                    }`}>
                      {task.status}
                    </span>
                    {task.confidence !== undefined && (
                      <span className="text-[10px] text-slate-400 font-mono">Confidence: {Math.round(task.confidence * 100)}%</span>
                    )}
                  </div>
                  {task.recommendation && (
                    <p className="text-xs text-slate-300 font-mono">{task.recommendation}</p>
                  )}
                  <p className="text-[10px] text-slate-500 font-mono flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {task.createdAt}
                  </p>
                </div>
                {(task.status === 'PENDING' || task.status === 'COMPLETED') && (
                  <div className="flex items-center gap-2 shrink-0 font-mono">
                    <button
                      onClick={async () => {
                        try {
                          await api.approveAITask(task.id);
                          addToast('success', 'Task Approved', `AI task ${task.id} approved.`);
                        } catch (err: any) {
                          addToast('error', 'Approval Failed', err?.message || 'Could not approve task.');
                        }
                      }}
                      className="px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-xs font-semibold text-white transition-colors flex items-center gap-1"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Approve
                    </button>
                    <button
                      onClick={async () => {
                        try {
                          await api.denyAITask(task.id);
                          addToast('warning', 'Task Denied', `AI task ${task.id} denied.`);
                        } catch (err: any) {
                          addToast('error', 'Deny Failed', err?.message || 'Could not deny task.');
                        }
                      }}
                      className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 text-xs font-semibold text-slate-300 hover:text-rose-400 transition-colors flex items-center gap-1"
                    >
                      <XCircle className="h-3.5 w-3.5" />
                      Deny
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Crash Risk */}
      {activeSection === 'crash-risk' && (
        <div className="space-y-4">
          <div className="text-xs text-slate-400 font-mono">
            Showing crash risk assessment for server: <span className="text-white">{selectedServerId || servers[0]?.id || 'none'}</span>
          </div>

          {crashRiskLoading && (
            <div className="p-8 rounded-xl border border-slate-800 bg-[#0c1017] text-center text-xs text-slate-400 font-mono animate-pulse">
              Assessing crash risk...
            </div>
          )}

          {crashRiskError && (
            <div className="p-6 rounded-xl border border-amber-500/30 bg-amber-950/10 text-xs text-amber-400 font-mono flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{crashRiskError}</span>
            </div>
          )}

          {crashRisk && !crashRiskLoading && (
            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-bold text-white font-mono">{crashRisk.server_name || crashRisk.server_id}</div>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">Predictive crash risk assessment</div>
                </div>
                <span className={`px-3 py-1 rounded-lg text-xs font-bold font-mono border ${RISK_BADGE[crashRisk.risk_level] || RISK_BADGE['LOW']}`}>
                  {crashRisk.risk_level}
                </span>
              </div>

              {crashRisk.tps_trend && crashRisk.tps_trend.length > 0 && (
                <div>
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 font-mono">TPS Trend</div>
                  <div className="flex items-end gap-1 h-12">
                    {crashRisk.tps_trend.map((tps: number, i: number) => (
                      <div
                        key={i}
                        className={`flex-1 rounded-t ${tps >= 19 ? 'bg-emerald-500' : tps >= 15 ? 'bg-amber-500' : 'bg-rose-500'}`}
                        style={{ height: `${Math.max(4, (tps / 20) * 100)}%` }}
                        title={`TPS: ${tps}`}
                      />
                    ))}
                  </div>
                </div>
              )}

              {crashRisk.recommendation && (
                <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/60 text-xs text-slate-200 font-mono">
                  <span className="text-cyan-400 font-bold">Recommendation: </span>
                  {crashRisk.recommendation}
                </div>
              )}
            </div>
          )}

          {!crashRiskLoading && !crashRiskError && !crashRisk && (
            <div className="p-8 rounded-xl border border-slate-800 bg-[#0c1017] text-center text-xs text-slate-500 font-mono">
              No server selected or no data available.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
