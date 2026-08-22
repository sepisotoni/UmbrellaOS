import React, { useState, useCallback } from 'react';
import api from '../../lib/api';
import { Appeal, AIReviewResult } from '../../types/dashboard';
import {
  X, Sparkles, AlertTriangle, CheckCircle2, RefreshCw, Loader2,
  Calendar, ChevronRight, User, Shield, Clock, ExternalLink
} from 'lucide-react';

interface AppealDetailPanelProps {
  appeal: Appeal;
  staffUsername?: string;
  onClose: () => void;
  onActionTaken?: (appealId: string, action: string) => void;
}

const ACTION_BUTTONS = [
  { action: 'ACCEPT',          label: '✅ Accept Appeal',          className: 'bg-emerald-600/20 border-emerald-500/30 text-emerald-300 hover:bg-emerald-600/40' },
  { action: 'REDUCE_SENTENCE', label: '⏳ Reduce Sentence',         className: 'bg-blue-600/20 border-blue-500/30 text-blue-300 hover:bg-blue-600/40' },
  { action: 'SCHEDULE_REVIEW', label: '📞 Schedule Review Call',    className: 'bg-purple-600/20 border-purple-500/30 text-purple-300 hover:bg-purple-600/40' },
  { action: 'ESCALATE',        label: '⬆️ Escalate to Senior Staff', className: 'bg-orange-600/20 border-orange-500/30 text-orange-300 hover:bg-orange-600/40' },
  { action: 'REJECT',          label: '❌ Reject Appeal',            className: 'bg-red-600/20 border-red-500/30 text-red-300 hover:bg-red-600/40' },
];

const STATUS_COLOURS: Record<string, string> = {
  OPEN:             'text-blue-400 bg-blue-950/60 border-blue-500/30',
  ACCEPTED:         'text-emerald-400 bg-emerald-950/60 border-emerald-500/30',
  REJECTED:         'text-red-400 bg-red-950/60 border-red-500/30',
  ESCALATED:        'text-orange-400 bg-orange-950/60 border-orange-500/30',
  REVIEW_SCHEDULED: 'text-purple-400 bg-purple-950/60 border-purple-500/30',
  PENDING:          'text-blue-400 bg-blue-950/60 border-blue-500/30',
  AI_REVIEWED:      'text-indigo-400 bg-indigo-950/60 border-indigo-500/30',
};

const REC_STYLES: Record<string, { icon: string; badge: string }> = {
  ACCEPT:          { icon: '✅', badge: 'text-emerald-400 bg-emerald-950/60 border-emerald-500/30' },
  REDUCE_SENTENCE: { icon: '⏳', badge: 'text-blue-400 bg-blue-950/60 border-blue-500/30' },
  REJECT:          { icon: '❌', badge: 'text-red-400 bg-red-950/60 border-red-500/30' },
  ESCALATE:        { icon: '⬆️', badge: 'text-orange-400 bg-orange-950/60 border-orange-500/30' },
  SCHEDULE_REVIEW: { icon: '📞', badge: 'text-purple-400 bg-purple-950/60 border-purple-500/30' },
};

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

const isClosed = (appeal: Appeal): boolean =>
  ['ACCEPTED', 'REJECTED', 'ESCALATED', 'REVIEW_SCHEDULED'].includes(appeal.status);

export const AppealDetailPanel: React.FC<AppealDetailPanelProps> = ({
  appeal, staffUsername, onClose, onActionTaken
}) => {
  const [aiState, setAiState] = useState<'idle' | 'loading' | 'error' | 'result'>(
    appeal.ai_review_status === 'COMPLETED' && appeal.ai_result ? 'result' :
    appeal.ai_review_status === 'FAILED' ? 'error' : 'idle'
  );
  const [aiResult, setAiResult] = useState<AIReviewResult | null>(appeal.ai_result || null);
  const [aiError, setAiError] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [newExpiry, setNewExpiry] = useState('');
  const [staffNote, setStaffNote] = useState('');
  const [actionDone, setActionDone] = useState<string | null>(
    isClosed(appeal) ? appeal.action_taken : null
  );
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const runAIReview = useCallback(async () => {
    setAiState('loading');
    setAiResult(null);
    setAiError('');
    try {
      const data = await api.reviewAppealAI(appeal.id);
      const result: AIReviewResult = {
        recommendation: data.recommendation || 'REJECT',
        confidence: data.confidence ?? 0,
        reasoning: data.reasoning || 'No reasoning provided.',
        punishment_context: data.punishment_context || '',
        flag_summary: data.flag_summary || null,
        risk_factors: data.risk_factors || [],
        mitigating_factors: data.mitigating_factors || [],
      };
      setAiResult(result);
      setAiState('result');
    } catch (err: any) {
      setAiError(err?.message || 'AI review request failed.');
      setAiState('error');
    }
  }, [appeal.id]);

  const handleAction = async (action: string) => {
    if (action === 'REDUCE_SENTENCE' && !showDatePicker) {
      setShowDatePicker(true);
      return;
    }
    setActionLoading(action);
    try {
      await api.closeAppeal(
        appeal.id,
        action,
        staffNote || undefined,
        action === 'REDUCE_SENTENCE' ? newExpiry : undefined
      );
      setActionDone(action);
      showToast(`Appeal #${appeal.id} — ${action} by ${staffUsername || 'staff'}`);
      if (onActionTaken) onActionTaken(appeal.id, action);
    } catch (err: any) {
      showToast(`Error: ${err?.message || 'Failed to close appeal'}`);
    } finally {
      setActionLoading(null);
    }
  };

  const closed = isClosed(appeal) || !!actionDone;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4" onClick={onClose}>
      <div
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-700 bg-[#0c1017] shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Toast */}
        {toast && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white shadow-lg font-mono">
            {toast}
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div>
            <p className="text-sm font-bold text-white">Appeal #{appeal.id}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border font-mono ${STATUS_COLOURS[appeal.status] || 'text-slate-400 border-slate-700 bg-slate-800'}`}>
                {appeal.status}
              </span>
              <span className="text-xs text-slate-500">Submitted {formatDate(appeal.created_at)}</span>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Closed appeal case summary — prominent */}
          {closed && (appeal.case_summary || actionDone) && (
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 space-y-2">
              <p className="text-sm font-bold text-emerald-300">
                {actionDone === 'ACCEPT' || appeal.status === 'ACCEPTED' ? '✅ ACCEPTED' :
                 actionDone === 'REJECT' || appeal.status === 'REJECTED' ? '❌ REJECTED' :
                 actionDone === 'ESCALATE' || appeal.status === 'ESCALATED' ? '⬆️ ESCALATED' :
                 actionDone === 'SCHEDULE_REVIEW' || appeal.status === 'REVIEW_SCHEDULED' ? '📞 REVIEW SCHEDULED' :
                 actionDone === 'REDUCE_SENTENCE' ? '⏳ SENTENCE REDUCED' : '✓ CLOSED'} — Appeal #{appeal.id}
              </p>
              {appeal.case_summary && <p className="text-xs text-slate-300">{appeal.case_summary}</p>}
              {appeal.handled_by && (
                <p className="text-xs text-slate-500">Handled by: {appeal.handled_by} · {formatDate(appeal.closed_at || null)}</p>
              )}
            </div>
          )}

          {/* Appeal Info */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Player</p>
            <div className="flex items-center gap-3">
              <img
                src={`https://mc-heads.net/avatar/${appeal.player_username || 'Steve'}/32`}
                alt={appeal.player_username || '?'}
                className="h-8 w-8 rounded border border-slate-700"
              />
              <div>
                <p className="text-sm font-semibold text-white">{appeal.player_username || '—'}</p>
                <p className="text-xs text-slate-500 font-mono">{appeal.player_uuid || '—'}</p>
              </div>
            </div>
            {appeal.punishment && (
              <div className="mt-2 border-t border-slate-800 pt-3 space-y-1">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Original Punishment</p>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-rose-400 font-mono border border-rose-500/30 bg-rose-950/60 px-2 py-0.5 rounded">{appeal.punishment.type}</span>
                  <span className="text-xs text-slate-300">{appeal.punishment.reason}</span>
                </div>
                <p className="text-xs text-slate-500">by {appeal.punishment.staff_name} · {formatDate(appeal.punishment.created_at)}</p>
              </div>
            )}
            {appeal.appeal_text && (
              <div className="mt-2 border-t border-slate-800 pt-3 space-y-1">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Appeal Text</p>
                <p className="text-sm text-slate-300 leading-relaxed">{appeal.appeal_text}</p>
              </div>
            )}
          </div>

          {/* AI Review Section */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
                AI Analysis
              </p>
              {aiState !== 'loading' && (
                <button
                  onClick={runAIReview}
                  className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  <RefreshCw className="h-3 w-3" />
                  {aiState === 'idle' ? 'Run AI Review' : 'Re-review'}
                </button>
              )}
            </div>

            {/* Idle — no review yet */}
            {aiState === 'idle' && (
              <button
                onClick={runAIReview}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 text-sm font-semibold hover:bg-indigo-600/40 transition-colors"
              >
                <Sparkles className="h-4 w-4" /> AI Review
              </button>
            )}

            {/* Loading */}
            {aiState === 'loading' && (
              <div className="flex items-center gap-3 text-slate-400">
                <Loader2 className="h-4 w-4 animate-spin text-indigo-400" />
                <span className="text-sm">Analyzing appeal...</span>
              </div>
            )}

            {/* Error */}
            {aiState === 'error' && (
              <div className="rounded-lg border border-red-500/30 bg-red-950/20 p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-400" />
                  <p className="text-sm text-red-300">AI review failed — {aiError}</p>
                </div>
              </div>
            )}

            {/* Result */}
            {aiState === 'result' && aiResult && (
              <div className="space-y-3">
                {/* Prominent recommendation */}
                <div className="rounded-lg border border-indigo-500/20 bg-indigo-950/20 p-4 text-center space-y-1">
                  <p className="text-xs text-indigo-400 uppercase tracking-wider font-semibold">AI Recommendation</p>
                  <p className="text-lg font-bold text-white">
                    {REC_STYLES[aiResult.recommendation]?.icon} RECOMMEND: {aiResult.recommendation.replace('_', ' ')}
                  </p>
                  <p className="text-xs text-slate-400 font-mono">{(aiResult.confidence * 100).toFixed(0)}% confidence</p>
                </div>

                {/* Reasoning */}
                <div>
                  <p className="text-xs font-semibold text-slate-500 mb-1">Reasoning</p>
                  <p className="text-sm text-slate-300 leading-relaxed">{aiResult.reasoning}</p>
                </div>

                {/* Punishment context */}
                {aiResult.punishment_context && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 mb-1">Context</p>
                    <p className="text-sm text-slate-400">{aiResult.punishment_context}</p>
                  </div>
                )}

                {/* GrimAC context */}
                {aiResult.flag_summary && (
                  <div>
                    <p className="text-xs font-semibold text-amber-500/80 mb-1">GrimAC Context</p>
                    <p className="text-sm text-slate-400">{aiResult.flag_summary}</p>
                  </div>
                )}

                {/* Risk factors */}
                {aiResult.risk_factors.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-red-400/80 mb-1">Risk Factors</p>
                    <ul className="space-y-1">
                      {aiResult.risk_factors.map((f, i) => (
                        <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                          <AlertTriangle className="h-3 w-3 text-red-400 mt-0.5 shrink-0" />{f}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Mitigating factors */}
                {aiResult.mitigating_factors.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-emerald-400/80 mb-1">Mitigating Factors</p>
                    <ul className="space-y-1">
                      {aiResult.mitigating_factors.map((f, i) => (
                        <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                          <CheckCircle2 className="h-3 w-3 text-emerald-400 mt-0.5 shrink-0" />{f}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Staff note input */}
          {!closed && (
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">Staff Note (optional)</label>
              <textarea
                value={staffNote}
                onChange={e => setStaffNote(e.target.value)}
                placeholder="Add a note for the record..."
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-slate-600 resize-none"
                rows={2}
              />
            </div>
          )}

          {/* Reduce sentence date picker */}
          {showDatePicker && !closed && (
            <div className="rounded-xl border border-blue-500/30 bg-blue-950/20 p-4 space-y-3">
              <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">New Expiry Date</p>
              <input
                type="datetime-local"
                value={newExpiry}
                onChange={e => setNewExpiry(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-slate-600 font-mono"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => handleAction('REDUCE_SENTENCE')}
                  disabled={!newExpiry || actionLoading === 'REDUCE_SENTENCE'}
                  className="flex-1 px-3 py-2 rounded-lg bg-blue-600/30 border border-blue-500/30 text-blue-300 text-xs font-semibold hover:bg-blue-600/50 disabled:opacity-50 transition-colors"
                >
                  {actionLoading === 'REDUCE_SENTENCE' ? <Loader2 className="h-3.5 w-3.5 animate-spin mx-auto" /> : 'Confirm Reduction'}
                </button>
                <button onClick={() => setShowDatePicker(false)} className="px-3 py-2 rounded-lg border border-slate-700 text-slate-400 text-xs hover:bg-slate-800 transition-colors">Cancel</button>
              </div>
            </div>
          )}

          {/* Action Buttons — always visible unless appeal is closed */}
          {!closed && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Decision</p>
              <div className="grid grid-cols-1 gap-2">
                {ACTION_BUTTONS.map(btn => (
                  <button
                    key={btn.action}
                    onClick={() => handleAction(btn.action)}
                    disabled={actionLoading !== null}
                    className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-semibold transition-colors disabled:opacity-60 disabled:cursor-not-allowed ${btn.className}`}
                  >
                    {actionLoading === btn.action
                      ? <Loader2 className="h-4 w-4 animate-spin" />
                      : btn.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AppealDetailPanel;
