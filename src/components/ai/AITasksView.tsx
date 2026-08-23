import React, { useState, useEffect } from 'react';
import { api, AITask, ServerRecord } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  Brain,
  Sparkles,
  CheckCircle2,
  XCircle,
  MessageSquare,
  AlertTriangle,
  RefreshCw,
  Send,
  ShieldAlert,
  Server,
  Activity,
} from 'lucide-react';

export const AITasksView: React.FC = () => {
  const { addToast } = useDashboard();
  const [activeTab, setActiveTab] = useState<'tasks' | 'copilot' | 'crash-risk'>('tasks');

  // Tasks State
  const [tasks, setTasks] = useState<AITask[]>([]);
  const [tasksLoading, setTasksLoading] = useState<boolean>(true);
  const [tasksError, setTasksError] = useState<string | null>(null);

  // Copilot Chat State
  const [copilotMessages, setCopilotMessages] = useState<{ sender: 'user' | 'copilot'; text: string }[]>([
    {
      sender: 'copilot',
      text: 'Hello! I am your UmbrellaOS AI Copilot. Ask me about server health, GrimAC false positives, or audit anomalies.',
    },
  ]);
  const [copilotInput, setCopilotInput] = useState<string>('');
  const [copilotLoading, setCopilotLoading] = useState<boolean>(false);

  // Crash Risk State
  const [servers, setServers] = useState<ServerRecord[]>([]);
  const [selectedRiskServer, setSelectedRiskServer] = useState<string>('survival-01');
  const [crashRiskResult, setCrashRiskResult] = useState<any | null>(null);
  const [riskLoading, setRiskLoading] = useState<boolean>(false);
  const [riskError, setRiskError] = useState<string | null>(null);

  const fetchTasks = async () => {
    setTasksLoading(true);
    setTasksError(null);
    try {
      const data = await api.getAITasks();
      setTasks(data || []);
    } catch (err: any) {
      setTasksError(err.message || 'Failed to load AI task queue');
    } finally {
      setTasksLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
    api.getServers().then((res) => {
      if (res && res.length > 0) {
        setServers(res);
        setSelectedRiskServer(res[0].id);
      }
    }).catch(() => {});
  }, []);

  const handleApproveTask = async (taskId: string) => {
    try {
      await api.approveAITask(taskId);
      addToast({
        type: 'success',
        title: 'Task Approved',
        message: `Task ${taskId.slice(0, 8)} marked as approved.`,
      });
      fetchTasks();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Approval Failed',
        message: err.message,
      });
    }
  };

  const handleDenyTask = async (taskId: string) => {
    try {
      await api.denyAITask(taskId);
      addToast({
        type: 'success',
        title: 'Task Denied',
        message: `Task ${taskId.slice(0, 8)} rejected.`,
      });
      fetchTasks();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Action Failed',
        message: err.message,
      });
    }
  };

  const handleSendCopilot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!copilotInput.trim() || copilotLoading) return;

    const query = copilotInput.trim();
    setCopilotInput('');
    setCopilotMessages((prev) => [...prev, { sender: 'user', text: query }]);
    setCopilotLoading(true);

    try {
      const res = await api.askCopilot(query, { server_id: selectedRiskServer });
      setCopilotMessages((prev) => [
        ...prev,
        { sender: 'copilot', text: res.response || res.answer || JSON.stringify(res) },
      ]);
    } catch (err: any) {
      setCopilotMessages((prev) => [
        ...prev,
        { sender: 'copilot', text: `Error: ${err.message || 'AI service unavailable.'}` },
      ]);
    } finally {
      setCopilotLoading(false);
    }
  };

  const handleCheckCrashRisk = async () => {
    if (!selectedRiskServer) return;
    setRiskLoading(true);
    setRiskError(null);
    try {
      const res = await api.getCrashRisk(selectedRiskServer);
      setCrashRiskResult(res);
      addToast({
        type: 'success',
        title: 'Risk Assessed',
        message: `Evaluated crash indicators for ${selectedRiskServer}.`,
      });
    } catch (err: any) {
      setRiskError(err.message || 'Crash risk analysis failed.');
    } finally {
      setRiskLoading(false);
    }
  };

  return (
    <div id="umbrella-ai-tasks-view" className="space-y-6">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>AI Operations & Intelligence</span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-purple-950/80 border border-purple-800/40 text-purple-300">
              On-Demand
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Human-in-the-loop task approvals, administrative copilot, and crash risk scoring.
          </p>
        </div>

        <button
          id="ai-refresh-btn"
          onClick={fetchTasks}
          disabled={tasksLoading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-purple-500/40 hover:text-white transition cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${tasksLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#1e1b4b] gap-2 pb-px">
        <button
          onClick={() => setActiveTab('tasks')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-t-lg transition border-t border-x cursor-pointer ${
            activeTab === 'tasks'
              ? 'bg-[#0d1127] text-purple-300 border-[#1e1b4b] border-b-transparent -mb-px shadow-sm'
              : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-[#0d1127]/40'
          }`}
        >
          <Brain className="h-3.5 w-3.5 text-purple-400" />
          <span>Pending Approvals ({tasks.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('copilot')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-t-lg transition border-t border-x cursor-pointer ${
            activeTab === 'copilot'
              ? 'bg-[#0d1127] text-purple-300 border-[#1e1b4b] border-b-transparent -mb-px shadow-sm'
              : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-[#0d1127]/40'
          }`}
        >
          <Sparkles className="h-3.5 w-3.5 text-purple-400" />
          <span>AI Copilot</span>
        </button>

        <button
          onClick={() => setActiveTab('crash-risk')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-t-lg transition border-t border-x cursor-pointer ${
            activeTab === 'crash-risk'
              ? 'bg-[#0d1127] text-purple-300 border-[#1e1b4b] border-b-transparent -mb-px shadow-sm'
              : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-[#0d1127]/40'
          }`}
        >
          <ShieldAlert className="h-3.5 w-3.5 text-amber-400" />
          <span>Crash Risk Analyzer</span>
        </button>
      </div>

      {/* TAB 1: AI Tasks Approval */}
      {activeTab === 'tasks' && (
        <div className="space-y-4">
          {tasksError && (
            <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
              <div>
                <span className="font-bold">Error loading AI tasks:</span>
                <p className="mt-0.5 text-rose-200/80">{tasksError}</p>
              </div>
            </div>
          )}

          <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
            {tasksLoading ? (
              <div className="py-12 text-center text-xs text-slate-500 font-mono">
                Loading task queue from core...
              </div>
            ) : tasks.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500 font-mono">
                No pending AI tasks waiting for human-in-the-loop review.
              </div>
            ) : (
              <div className="space-y-4">
                {tasks.map((task) => (
                  <div
                    key={task.id}
                    className="rounded-xl border border-[#1a1f42] bg-[#070914] p-4 font-mono text-xs space-y-3"
                  >
                    <div className="flex items-center justify-between border-b border-[#1e1b4b] pb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white uppercase">{task.action_type || 'PROPOSED ACTION'}</span>
                        <span className="px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 text-[10px]">
                          Target: {task.target_id}
                        </span>
                      </div>
                      <span className="text-slate-500 text-[10px]">
                        {task.created_at ? new Date(task.created_at).toLocaleString() : 'Recent'}
                      </span>
                    </div>

                    <div className="text-slate-300 font-sans text-xs bg-[#0b0f24] p-3 rounded-lg border border-[#1e1b4b]">
                      {task.reasoning || task.description}
                    </div>

                    <div className="flex justify-end gap-2 pt-1">
                      <button
                        onClick={() => handleDenyTask(task.id)}
                        className="px-3 py-1.5 rounded-lg border border-rose-500/40 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 text-xs font-bold transition cursor-pointer"
                      >
                        Deny
                      </button>
                      <button
                        onClick={() => handleApproveTask(task.id)}
                        className="px-3 py-1.5 rounded-lg border border-emerald-500/40 bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 text-xs font-bold transition cursor-pointer"
                      >
                        Approve & Enforce
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: AI Copilot Chat */}
      {activeTab === 'copilot' && (
        <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl flex flex-col h-[560px]">
          <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-thin scrollbar-thumb-purple-900">
            {copilotMessages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-3 text-xs font-sans ${
                  msg.sender === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {msg.sender === 'copilot' && (
                  <div className="h-7 w-7 rounded-lg bg-purple-900/60 border border-purple-500/40 flex items-center justify-center text-purple-300 shrink-0">
                    <Sparkles className="h-4 w-4" />
                  </div>
                )}
                <div
                  className={`rounded-xl p-3.5 max-w-lg leading-relaxed ${
                    msg.sender === 'user'
                      ? 'bg-purple-600 text-white font-medium shadow-md'
                      : 'bg-[#070914] text-slate-200 border border-[#1e1b4b]'
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
          </div>

          <form onSubmit={handleSendCopilot} className="mt-4 pt-3 border-t border-[#1e1b4b] flex gap-2">
            <input
              id="copilot-query-input"
              type="text"
              value={copilotInput}
              onChange={(e) => setCopilotInput(e.target.value)}
              placeholder="Ask Copilot about GrimAC logs, player trends, or server triage..."
              className="flex-1 rounded-xl border border-[#1e1b4b] bg-[#070914] px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none font-sans"
            />
            <button
              id="submit-copilot-query"
              type="submit"
              disabled={copilotLoading || !copilotInput.trim()}
              className="rounded-xl border border-purple-500/50 bg-purple-600 px-4 py-2.5 text-xs font-bold text-white hover:bg-purple-500 transition disabled:opacity-50 cursor-pointer"
            >
              {copilotLoading ? 'Thinking...' : 'Ask Copilot'}
            </button>
          </form>
        </div>
      )}

      {/* TAB 3: Crash Risk Analyzer */}
      {activeTab === 'crash-risk' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl space-y-4 font-mono text-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="font-bold text-white text-sm">Evaluate Instance Stability</h3>
                <p className="text-slate-400 text-xs mt-0.5">
                  Analyze garbage collection spikes, chunk load surges, and thread stalls.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={selectedRiskServer}
                  onChange={(e) => setSelectedRiskServer(e.target.value)}
                  className="rounded-lg border border-[#1e1b4b] bg-[#070914] px-3 py-2 text-xs text-white focus:border-purple-500 focus:outline-none"
                >
                  {servers.length > 0 ? (
                    servers.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.id})
                      </option>
                    ))
                  ) : (
                    <option value="survival-01">survival-01</option>
                  )}
                </select>

                <button
                  id="evaluate-crash-risk-btn"
                  onClick={handleCheckCrashRisk}
                  disabled={riskLoading}
                  className="rounded-lg border border-purple-500/50 bg-purple-600 px-4 py-2 text-xs font-bold text-white hover:bg-purple-500 transition disabled:opacity-50 cursor-pointer"
                >
                  {riskLoading ? 'Evaluating...' : 'Analyze Risk'}
                </button>
              </div>
            </div>

            {riskError && (
              <div className="rounded-lg border border-rose-500/40 bg-rose-950/40 p-3 text-xs text-rose-300">
                {riskError}
              </div>
            )}

            {crashRiskResult && (
              <div className="rounded-xl border border-purple-500/40 bg-[#070914] p-4 space-y-3">
                <div className="flex items-center justify-between border-b border-[#1e1b4b] pb-2">
                  <span className="font-bold text-purple-300">Risk Assessment for {selectedRiskServer}</span>
                  <span className="text-amber-400 font-bold">
                    Risk Level: {crashRiskResult.risk_level || 'LOW'}
                  </span>
                </div>
                <div className="text-slate-300 font-sans text-xs">
                  {crashRiskResult.summary || JSON.stringify(crashRiskResult)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
