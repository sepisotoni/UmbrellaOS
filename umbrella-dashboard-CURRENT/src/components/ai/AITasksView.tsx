import React, { useState, useEffect, useRef } from 'react';
import { api, AITask, CopilotActionProposal, ServerRecord } from '../../lib/api';
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

type CopilotChatAction = Omit<CopilotActionProposal, 'status'> & {
  status: 'pending' | 'approved' | 'denied' | 'expired';
};

type CopilotChatMessage = {
  sender: 'user' | 'copilot';
  text: string;
  actions?: CopilotChatAction[];
};

function copilotActionFromTask(task: AITask): CopilotChatAction | null {
  const proposal = task.evidence?.copilot_action;
  if (
    !proposal ||
    !['ban', 'tempban', 'unban'].includes(proposal.action) ||
    typeof proposal.player_uuid !== 'string' ||
    typeof proposal.player_name !== 'string' ||
    typeof proposal.reason !== 'string'
  ) {
    return null;
  }
  const status: CopilotChatAction['status'] =
    task.status === 'approved' || task.status === 'denied' || task.status === 'expired'
      ? task.status
      : 'pending';
  return {
    task_id: task.id,
    action: proposal.action,
    player_uuid: proposal.player_uuid,
    player_name: proposal.player_name,
    reason: proposal.reason,
    duration_hours: proposal.duration_hours ?? null,
    expires_at: proposal.expires_at ?? null,
    confirmation_required: true,
    proposal_expires_at: task.expires_at,
    status,
  };
}

export const AITasksView: React.FC = () => {
  const { addToast, currentUser } = useDashboard();
  const canConfirmModeration = currentUser?.permissions?.includes('moderation.ban') ?? false;
  const [activeTab, setActiveTab] = useState<'tasks' | 'copilot' | 'crash-risk'>('tasks');

  // Tasks State
  const [tasks, setTasks] = useState<AITask[]>([]);
  const [tasksLoading, setTasksLoading] = useState<boolean>(true);
  const [tasksError, setTasksError] = useState<string | null>(null);

  // Copilot Chat State
  const [copilotMessages, setCopilotMessages] = useState<CopilotChatMessage[]>([
    {
      sender: 'copilot',
      text: 'Hello! I am your UmbrellaOS AI Copilot. Ask about player history, daily activity, server health, or request a ban/unban proposal. Moderation actions always require staff confirmation.',
    },
  ]);
  const [copilotInput, setCopilotInput] = useState<string>('');
  const [copilotLoading, setCopilotLoading] = useState<boolean>(false);
  const [copilotActionSubmitting, setCopilotActionSubmitting] = useState<number | null>(null);
  const copilotScrollRef = useRef<HTMLDivElement>(null);

  // Crash Risk State
  const [servers, setServers] = useState<ServerRecord[]>([]);
  const [selectedRiskServer, setSelectedRiskServer] = useState<string>('');
  const [riskServersError, setRiskServersError] = useState<string | null>(null);
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
    api.getServers()
      .then((res) => {
        const availableServers = Array.isArray(res) ? res : [];
        setServers(availableServers);
        setSelectedRiskServer(current =>
          availableServers.some(server => server.id === current)
            ? current
            : availableServers[0]?.id ?? '',
        );
        setRiskServersError(null);
      })
      .catch((error: unknown) => {
        setRiskServersError(
          error instanceof Error ? error.message : 'Could not load servers.',
        );
      });
  }, []);

  useEffect(() => {
    if (activeTab !== 'copilot' || !copilotScrollRef.current) return;
    const chat = copilotScrollRef.current;
    chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' });
  }, [activeTab, copilotMessages, copilotLoading]);

  const handleApproveTask = async (taskId: number) => {
    try {
      await api.approveAITask(taskId);
      addToast({
        type: 'success',
        title: 'Task Approved',
        message: `Task #${taskId} marked as approved.`,
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

  const handleDenyTask = async (taskId: number) => {
    try {
      await api.denyAITask(taskId);
      addToast({
        type: 'success',
        title: 'Task Denied',
        message: `Task #${taskId} rejected.`,
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

  const markCopilotAction = (
    taskId: number,
    status: CopilotChatAction['status'],
  ) => {
    setCopilotMessages((messages) =>
      messages.map((message) => ({
        ...message,
        actions: message.actions?.map((action) =>
          action.task_id === taskId ? { ...action, status } : action,
        ),
      })),
    );
  };

  const handleConfirmCopilotAction = async (action: CopilotChatAction) => {
    if (copilotActionSubmitting !== null || action.status !== 'pending') return;
    setCopilotActionSubmitting(action.task_id);
    try {
      await api.executeCopilotAction(action.task_id);
      markCopilotAction(action.task_id, 'approved');
      addToast({
        type: 'success',
        title: 'Moderation Action Executed',
        message: `${action.action.toUpperCase()} applied to ${action.player_name}.`,
      });
      await fetchTasks();
    } catch (err: any) {
      if (err.status === 410) markCopilotAction(action.task_id, 'expired');
      addToast({
        type: 'error',
        title: 'Action Not Executed',
        message: err.message || 'The moderation proposal could not be executed.',
      });
    } finally {
      setCopilotActionSubmitting(null);
    }
  };

  const handleDeclineCopilotAction = async (action: CopilotChatAction) => {
    if (copilotActionSubmitting !== null || action.status !== 'pending') return;
    setCopilotActionSubmitting(action.task_id);
    try {
      await api.declineCopilotAction(action.task_id);
      markCopilotAction(action.task_id, 'denied');
      addToast({
        type: 'success',
        title: 'Proposal Dismissed',
        message: `The ${action.action} proposal for ${action.player_name} was dismissed.`,
      });
      await fetchTasks();
    } catch (err: any) {
      if (err.status === 410) markCopilotAction(action.task_id, 'expired');
      addToast({
        type: 'error',
        title: 'Could Not Dismiss Proposal',
        message: err.message || 'The moderation proposal could not be dismissed.',
      });
    } finally {
      setCopilotActionSubmitting(null);
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
      const res = await api.askCopilot(
        query,
        selectedRiskServer ? { server_id: selectedRiskServer } : undefined,
      );
      setCopilotMessages((prev) => [
        ...prev,
        {
          sender: 'copilot',
          text: res.response || JSON.stringify(res),
          actions: (res.pending_actions || []).map((action) => ({
            ...action,
            status: action.status,
          })),
        },
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
                {tasks.map((task) => {
                  const actionProposal = copilotActionFromTask(task);
                  return (
                    <div
                      key={task.id}
                      className="rounded-xl border border-[#1a1f42] bg-[#070914] p-4 font-mono text-xs space-y-3"
                    >
                    <div className="flex items-center justify-between border-b border-[#1e1b4b] pb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white uppercase">{task.task_type || 'PROPOSED ACTION'}</span>
                        {task.player_uuid && (
                          <span className="px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 text-[10px]">
                            Target: {task.player_uuid.slice(0, 12)}…
                          </span>
                        )}
                        {task.ai_recommendation && (
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            task.ai_recommendation === 'REJECT'
                              ? 'bg-rose-950/80 text-rose-300'
                              : 'bg-emerald-950/80 text-emerald-300'
                          }`}>
                            AI: {task.ai_recommendation}
                            {task.ai_confidence ? ` (${Math.round(task.ai_confidence * 100)}%)` : ''}
                          </span>
                        )}
                      </div>
                      <span className="text-slate-500 text-[10px]">
                        {task.created_at ? new Date(task.created_at).toLocaleString() : 'Recent'}
                      </span>
                    </div>

                    <div className="text-slate-300 font-sans text-xs bg-[#0b0f24] p-3 rounded-lg border border-[#1e1b4b]">
                      {task.ai_summary || 'No summary available.'}
                    </div>

                      {actionProposal ? (
                        <div className="space-y-2 border-t border-[#1e1b42] pt-3">
                          <div className="text-slate-300">
                            {actionProposal.action.toUpperCase()} {actionProposal.player_name}
                            {actionProposal.duration_hours
                              ? ` for ${actionProposal.duration_hours} hours`
                              : ''}
                            {actionProposal.reason ? ` — ${actionProposal.reason}` : ''}
                          </div>
                          {actionProposal.status === 'pending' && canConfirmModeration ? (
                            <div className="flex justify-end gap-2">
                              <button
                                onClick={() => handleDeclineCopilotAction(actionProposal)}
                                disabled={copilotActionSubmitting !== null}
                                className="px-3 py-1.5 rounded-lg border border-slate-500/40 text-slate-300 text-xs font-bold disabled:opacity-50"
                              >
                                Dismiss
                              </button>
                              <button
                                onClick={() => handleConfirmCopilotAction(actionProposal)}
                                disabled={copilotActionSubmitting !== null}
                                className="px-3 py-1.5 rounded-lg border border-rose-500/40 bg-rose-950/40 text-rose-200 text-xs font-bold disabled:opacity-50"
                              >
                                Confirm and execute
                              </button>
                            </div>
                          ) : actionProposal.status === 'pending' ? (
                            <div className="text-right text-slate-400">
                              Your role cannot confirm this moderation action.
                            </div>
                          ) : (
                            <div className="text-right font-bold uppercase text-slate-400">
                              {actionProposal.status}
                            </div>
                          )}
                        </div>
                      ) : (
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
                            Approve Recommendation
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: AI Copilot Chat */}
      {activeTab === 'copilot' && (
        <div className="w-full min-w-0 max-w-full h-[min(70vh,560px)] min-h-[320px] overflow-hidden rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl flex flex-col">
          <div
            ref={copilotScrollRef}
            aria-live="polite"
            className="min-h-0 min-w-0 w-full flex-1 overflow-x-hidden overflow-y-auto overscroll-contain space-y-3 pr-2 scrollbar-thin scrollbar-thumb-purple-900"
          >
            {copilotMessages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex min-w-0 gap-3 text-xs font-sans ${
                  msg.sender === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {msg.sender === 'copilot' && (
                  <div className="h-7 w-7 rounded-lg bg-purple-900/60 border border-purple-500/40 flex items-center justify-center text-purple-300 shrink-0">
                    <Sparkles className="h-4 w-4" />
                  </div>
                )}
                <div className="min-w-0 max-w-[85%] space-y-2">
                  <div
                    className={`min-w-0 break-words [overflow-wrap:anywhere] rounded-xl p-3.5 leading-relaxed ${
                      msg.sender === 'user'
                        ? 'bg-purple-600 text-white font-medium shadow-md'
                        : 'bg-[#070914] text-slate-200 border border-[#1e1b4b]'
                    }`}
                  >
                    {msg.text}
                  </div>
                  {msg.actions?.map((action) => (
                    <div
                      key={action.task_id}
                      className="rounded-xl border border-amber-500/40 bg-amber-950/30 p-3 text-xs"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold uppercase text-amber-200">
                          Pending {action.action === 'tempban' ? 'temporary ban' : action.action}
                        </span>
                        <span className="text-[10px] text-amber-100/70">
                          Expires {new Date(action.proposal_expires_at).toLocaleString()}
                        </span>
                      </div>
                      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 text-[11px]">
                        <dt className="text-slate-400">Player</dt>
                        <dd className="break-all text-white">
                          {action.player_name} ({action.player_uuid})
                        </dd>
                        {action.action === 'tempban' && (
                          <>
                            <dt className="text-slate-400">Duration</dt>
                            <dd className="text-white">{action.duration_hours} hours</dd>
                          </>
                        )}
                        {action.expires_at && (
                          <>
                            <dt className="text-slate-400">Ban expires</dt>
                            <dd className="text-white">{new Date(action.expires_at).toLocaleString()}</dd>
                          </>
                        )}
                        {action.reason && (
                          <>
                            <dt className="text-slate-400">Reason</dt>
                            <dd className="break-words text-white">{action.reason}</dd>
                          </>
                        )}
                      </dl>
                      <p className="mt-2 text-[10px] text-amber-100/70">
                        No action has been taken. Bans apply across the network; review the target and reason before confirming.
                      </p>
                      {action.status === 'pending' && canConfirmModeration ? (
                        <div className="mt-3 flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => handleDeclineCopilotAction(action)}
                            disabled={copilotActionSubmitting !== null}
                            className="rounded-lg border border-slate-500/40 px-3 py-1.5 text-[11px] text-slate-300 hover:bg-slate-800 disabled:opacity-50"
                          >
                            Dismiss
                          </button>
                          <button
                            type="button"
                            onClick={() => handleConfirmCopilotAction(action)}
                            disabled={copilotActionSubmitting !== null}
                            className="rounded-lg border border-rose-500/40 bg-rose-900/50 px-3 py-1.5 text-[11px] font-bold text-rose-100 hover:bg-rose-800/70 disabled:opacity-50"
                          >
                            {copilotActionSubmitting === action.task_id
                              ? 'Submitting...'
                              : 'Confirm and execute'}
                          </button>
                        </div>
                      ) : action.status === 'pending' ? (
                        <p className="mt-3 text-right text-[11px] text-slate-400">
                          Your role cannot confirm this moderation action.
                        </p>
                      ) : (
                        <div className="mt-3 text-right text-[11px] font-semibold uppercase text-slate-300">
                          {action.status === 'approved'
                            ? 'Executed'
                            : action.status === 'denied'
                              ? 'Dismissed'
                              : 'Expired'}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <form onSubmit={handleSendCopilot} className="mt-4 flex shrink-0 gap-2 border-t border-[#1e1b4b] pt-3">
            <input
              id="copilot-query-input"
              type="text"
              value={copilotInput}
              onChange={(e) => setCopilotInput(e.target.value)}
              placeholder="Ask about players, activity, or request a ban/unban proposal..."
              className="min-w-0 flex-1 rounded-xl border border-[#1e1b4b] bg-[#070914] px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none font-sans"
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
                  disabled={servers.length === 0}
                  className="rounded-lg border border-[#1e1b4b] bg-[#070914] px-3 py-2 text-xs text-white focus:border-purple-500 focus:outline-none"
                >
                  {servers.length > 0 ? (
                    servers.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.id})
                      </option>
                    ))
                  ) : (
                    <option value="">
                      {riskServersError ? 'Server list unavailable' : 'No registered servers'}
                    </option>
                  )}
                </select>

                <button
                  id="evaluate-crash-risk-btn"
                  onClick={handleCheckCrashRisk}
                  disabled={riskLoading || !selectedRiskServer}
                  className="rounded-lg border border-purple-500/50 bg-purple-600 px-4 py-2 text-xs font-bold text-white hover:bg-purple-500 transition disabled:opacity-50 cursor-pointer"
                >
                  {riskLoading ? 'Evaluating...' : 'Analyze Risk'}
                </button>
              </div>
            </div>

            {riskServersError ? (
              <p role="alert" className="text-xs text-rose-300">
                Could not load the server list: {riskServersError}
              </p>
            ) : servers.length === 0 ? (
              <p className="text-xs text-slate-400">
                No registered servers are available to analyze.
              </p>
            ) : null}

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
                  {crashRiskResult.recommendation || crashRiskResult.summary || JSON.stringify(crashRiskResult)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
