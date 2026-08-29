import React, { useState } from 'react';
import { api, AppealSchema, AIReviewAppealResponse } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import {
  Scale,
  Sparkles,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowUpRight,
  PhoneCall,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  Shield,
  Calendar,
} from 'lucide-react';

interface AppealDetailPanelProps {
  appeal: AppealSchema;
  onClose: () => void;
  onRefresh: () => void;
}

export const AppealDetailPanel: React.FC<AppealDetailPanelProps> = ({
  appeal,
  onClose,
  onRefresh,
}) => {
  const { addToast, navigateToPlayer } = useDashboard();

  // AI Review State
  const [aiReviewLoading, setAiReviewLoading] = useState<boolean>(false);
  const [aiReviewResult, setAiReviewResult] = useState<AIReviewAppealResponse | null>(null);
  const [aiReviewError, setAiReviewError] = useState<string | null>(null);

  // Decision Modal / Action State
  const [staffNote, setStaffNote] = useState<string>('');
  const [newExpiry, setNewExpiry] = useState<string>('');
  const [showReduceDatePicker, setShowReduceDatePicker] = useState<boolean>(false);
  const [isSubmittingAction, setIsSubmittingAction] = useState<boolean>(false);

  // AUDIT-2026-08-29 fix: the backend creates appeals with status "open"
  // (api/routers/appeals.py create_appeal), never "pending" — this check
  // never matched, so isClosed was always true and every freshly-submitted
  // appeal hid its staff decision buttons. "open" is the only non-closed
  // value the backend ever produces (see ck_appeals_status).
  const isClosed = appeal.status !== 'open';

  const handleTriggerAI = async () => {
    setAiReviewLoading(true);
    setAiReviewError(null);
    try {
      const res = await api.triggerAppealAIReview(appeal.id);
      // AI result might be nested inside res or res.ai_result
      const aiData = res.ai_result || res;
      setAiReviewResult(aiData);
      addToast({
        type: 'success',
        title: 'AI Analysis Complete',
        message: 'AI decision recommendation synthesized.',
      });
      onRefresh();
    } catch (err: any) {
      const msg = err.message || 'AI service unavailable (503). You may proceed with manual review.';
      setAiReviewError(msg);
      addToast({
        type: 'error',
        title: 'AI Analysis Failed',
        message: msg,
      });
    } finally {
      setAiReviewLoading(false);
    }
  };

  const handleCloseAppeal = async (action: 'ACCEPT' | 'REDUCE_SENTENCE' | 'REJECT' | 'ESCALATE' | 'SCHEDULE_REVIEW') => {
    if (action === 'REDUCE_SENTENCE' && !newExpiry) {
      setShowReduceDatePicker(true);
      return;
    }

    setIsSubmittingAction(true);
    try {
      await api.closeAppeal(appeal.id, {
        action,
        staff_note: staffNote.trim() || undefined,
        new_expiry: newExpiry ? new Date(newExpiry).toISOString() : undefined,
      });

      addToast({
        type: 'success',
        title: 'Appeal Decided',
        message: `Appeal marked as ${action}.`,
      });
      onRefresh();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Decision Failed',
        message: err.message,
      });
    } finally {
      setIsSubmittingAction(false);
    }
  };

  return (
    <div className="rounded-2xl border border-[#1e1b4b] bg-[#0d1127] p-6 shadow-2xl space-y-6 font-mono text-xs">
      {/* Header with Closed Action Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1e1b4b] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Scale className="h-5 w-5 text-purple-400" />
            <h2 className="text-base font-bold text-white tracking-tight font-sans">
              {isClosed ? (
                <span className="text-purple-300">
                  {appeal.action_taken === 'ACCEPT' ? '✅ ACCEPTED' :
                   appeal.action_taken === 'REJECT' ? '❌ REJECTED' :
                   appeal.action_taken === 'REDUCE_SENTENCE' ? '⏳ SENTENCE REDUCED' :
                   appeal.action_taken === 'ESCALATE' ? '⬆️ ESCALATED' :
                   appeal.action_taken === 'SCHEDULE_REVIEW' ? '📞 REVIEW SCHEDULED' :
                   appeal.status} — Appeal #{appeal.id.slice(0, 8)}
                </span>
              ) : (
                `Appeal Case #${appeal.id.slice(0, 8)}`
              )}
            </h2>
          </div>
          <p className="text-slate-400 text-[11px] mt-0.5">
            Submitted {appeal.created_at ? new Date(appeal.created_at).toLocaleString() : 'recently'}
          </p>
        </div>

        <button
          onClick={onClose}
          className="self-start sm:self-auto px-3 py-1.5 rounded-lg border border-[#1e1b4b] bg-[#070914] text-slate-300 hover:text-white"
        >
          Close Detail
        </button>
      </div>

      {/* Case Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-xl border border-[#1a1f42] bg-[#070914] p-4 space-y-2">
          <div className="text-slate-400 font-bold uppercase text-[10px]">Appellant Profile</div>
          <div className="flex items-center justify-between">
            <span className="text-white font-bold">{appeal.player_uuid}</span>
            <button
              onClick={() => navigateToPlayer(appeal.player_uuid)}
              className="text-purple-400 hover:text-purple-300 inline-flex items-center gap-1 underline"
            >
              <span>Profile</span>
              <ExternalLink className="h-3 w-3" />
            </button>
          </div>
          <div className="text-slate-400 text-[11px]">
            Linked Punishment: <span className="text-slate-200">{appeal.punishment_id || 'N/A'}</span>
          </div>
        </div>

        <div className="rounded-xl border border-[#1a1f42] bg-[#070914] p-4 space-y-2">
          <div className="text-slate-400 font-bold uppercase text-[10px]">Appeal Status</div>
          <div className="flex items-center gap-2">
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                isClosed
                  ? 'bg-purple-950/80 text-purple-300 border border-purple-800/40'
                  : 'bg-amber-950/80 text-amber-300 border border-amber-800/40'
              }`}
            >
              {appeal.status.toUpperCase()}
            </span>
            {appeal.handled_by && (
              <span className="text-slate-400 text-[11px]">
                Handled by: <strong className="text-white">{appeal.handled_by}</strong>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Player's Written Appeal Statement */}
      <div className="rounded-xl border border-[#1a1f42] bg-[#070914] p-4 space-y-2">
        <div className="text-slate-400 font-bold uppercase text-[10px]">Player's Appeal Statement</div>
        <div className="text-slate-200 text-xs font-sans whitespace-pre-wrap leading-relaxed bg-[#0b0f24] p-3 rounded-lg border border-[#1e1b4b]">
          {appeal.message || 'No written message provided.'}
        </div>
      </div>

      {/* On-Demand AI Review Section */}
      <div className="rounded-xl border border-purple-500/30 bg-purple-950/20 p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-purple-500/20 pb-3">
          <div className="flex items-center gap-2 font-bold text-white">
            <Sparkles className="h-4 w-4 text-purple-400" />
            <span>AI Evidence & Remorse Analysis (On-Demand)</span>
          </div>

          {!isClosed && (
            <button
              id="trigger-appeal-ai-btn"
              onClick={handleTriggerAI}
              disabled={aiReviewLoading}
              className="inline-flex items-center gap-1.5 rounded-lg border border-purple-500/50 bg-purple-600 hover:bg-purple-500 px-3 py-1.5 text-xs font-bold text-white transition disabled:opacity-50 cursor-pointer shadow-[0_0_10px_rgba(168,85,247,0.3)]"
            >
              <Sparkles className={`h-3.5 w-3.5 ${aiReviewLoading ? 'animate-spin' : ''}`} />
              <span>{aiReviewLoading ? 'Analyzing Case...' : 'Trigger AI Review'}</span>
            </button>
          )}
        </div>

        {aiReviewError && (
          <div className="rounded-lg border border-rose-500/40 bg-rose-950/40 p-3 text-xs text-rose-300 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
            <div>
              <span className="font-bold">AI Review Error:</span>
              <p className="mt-0.5">{aiReviewError}</p>
              <button
                onClick={handleTriggerAI}
                className="mt-1.5 text-purple-300 underline hover:text-white"
              >
                Re-review appeal
              </button>
            </div>
          </div>
        )}

        {(aiReviewResult || appeal.case_summary) && (
          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-purple-300 font-bold">
                RECOMMENDATION: {aiReviewResult?.recommendation || 'REVIEWED'}
              </span>
              {aiReviewResult?.confidence && (
                <span className="text-slate-400">
                  Confidence: {Math.round(aiReviewResult.confidence * 100)}%
                </span>
              )}
            </div>

            <div className="text-slate-300 font-sans text-xs bg-[#070914] p-3 rounded-lg border border-[#1e1b4b]">
              {aiReviewResult?.reasoning || appeal.case_summary}
            </div>

            {aiReviewResult?.risk_factors && aiReviewResult.risk_factors.length > 0 && (
              <div className="text-rose-300 text-[11px]">
                <strong>Risk Factors:</strong> {aiReviewResult.risk_factors.join(', ')}
              </div>
            )}

            {aiReviewResult?.mitigating_factors && aiReviewResult.mitigating_factors.length > 0 && (
              <div className="text-emerald-300 text-[11px]">
                <strong>Mitigating Factors:</strong> {aiReviewResult.mitigating_factors.join(', ')}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Staff Actions (5 Action Buttons) */}
      {!isClosed ? (
        <div className="space-y-4 pt-2 border-t border-[#1e1b4b]">
          <div>
            <label className="block text-slate-400 mb-1 text-[11px]">Staff Note (Recorded in Audit Log)</label>
            <input
              type="text"
              value={staffNote}
              onChange={(e) => setStaffNote(e.target.value)}
              placeholder="e.g. Reviewed GrimAC reach flags — player demonstrated genuine remorse..."
              className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
            />
          </div>

          {showReduceDatePicker && (
            <div className="p-3 rounded-lg border border-amber-500/40 bg-amber-950/20 space-y-2">
              <label className="block text-amber-300 text-[11px] font-bold">New Sentence Expiration Date</label>
              <input
                type="datetime-local"
                value={newExpiry}
                onChange={(e) => setNewExpiry(e.target.value)}
                className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2 text-white focus:border-purple-500 focus:outline-none"
              />
            </div>
          )}

          <div className="text-slate-400 text-[11px] font-bold uppercase">Decision Actions</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            <button
              id="appeal-btn-accept"
              onClick={() => handleCloseAppeal('ACCEPT')}
              disabled={isSubmittingAction}
              className="flex flex-col items-center justify-center gap-1.5 p-3 rounded-xl border border-emerald-500/40 bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-200 transition font-bold cursor-pointer disabled:opacity-50 shadow-sm"
            >
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>Accept Appeal</span>
            </button>

            <button
              id="appeal-btn-reduce"
              onClick={() => handleCloseAppeal('REDUCE_SENTENCE')}
              disabled={isSubmittingAction}
              className="flex flex-col items-center justify-center gap-1.5 p-3 rounded-xl border border-amber-500/40 bg-amber-950/40 hover:bg-amber-900/60 text-amber-200 transition font-bold cursor-pointer disabled:opacity-50 shadow-sm"
            >
              <Clock className="h-4 w-4 text-amber-400" />
              <span>Reduce Sentence</span>
            </button>

            <button
              id="appeal-btn-schedule"
              onClick={() => handleCloseAppeal('SCHEDULE_REVIEW')}
              disabled={isSubmittingAction}
              className="flex flex-col items-center justify-center gap-1.5 p-3 rounded-xl border border-blue-500/40 bg-blue-950/40 hover:bg-blue-900/60 text-blue-200 transition font-bold cursor-pointer disabled:opacity-50 shadow-sm"
            >
              <PhoneCall className="h-4 w-4 text-blue-400" />
              <span>Schedule Review</span>
            </button>

            <button
              id="appeal-btn-escalate"
              onClick={() => handleCloseAppeal('ESCALATE')}
              disabled={isSubmittingAction}
              className="flex flex-col items-center justify-center gap-1.5 p-3 rounded-xl border border-purple-500/40 bg-purple-950/40 hover:bg-purple-900/60 text-purple-200 transition font-bold cursor-pointer disabled:opacity-50 shadow-sm"
            >
              <ArrowUpRight className="h-4 w-4 text-purple-400" />
              <span>Escalate</span>
            </button>

            <button
              id="appeal-btn-reject"
              onClick={() => handleCloseAppeal('REJECT')}
              disabled={isSubmittingAction}
              className="flex flex-col items-center justify-center gap-1.5 p-3 rounded-xl border border-rose-500/40 bg-rose-950/40 hover:bg-rose-900/60 text-rose-200 transition font-bold cursor-pointer disabled:opacity-50 shadow-sm"
            >
              <XCircle className="h-4 w-4 text-rose-400" />
              <span>Reject Appeal</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="p-4 rounded-xl border border-[#1e1b4b] bg-[#070914] text-center text-slate-400 text-xs">
          This appeal is closed and finalized. Case action: <strong className="text-white">{appeal.action_taken || appeal.status}</strong>
        </div>
      )}
    </div>
  );
};
