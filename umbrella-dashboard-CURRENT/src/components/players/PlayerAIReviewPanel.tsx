import React, { useState, useEffect, useCallback } from 'react';
import api from '../../lib/api';
import { PlayerAIReview } from '../../types/dashboard';
import {
  X, Sparkles, AlertTriangle, CheckCircle2, RefreshCw,
  ShieldAlert, TrendingUp, TrendingDown, Loader2
} from 'lucide-react';

interface PlayerAIReviewPanelProps {
  uuid: string;
  username: string;
  onClose: () => void;
}

const RISK_STYLES: Record<string, { border: string; badge: string; icon: string }> = {
  LOW:      { border: 'border-emerald-500/30', badge: 'text-emerald-400 bg-emerald-950/60 border-emerald-500/30', icon: 'text-emerald-400' },
  MEDIUM:   { border: 'border-amber-500/30',   badge: 'text-amber-400 bg-amber-950/60 border-amber-500/30',     icon: 'text-amber-400'   },
  HIGH:     { border: 'border-orange-500/30',  badge: 'text-orange-400 bg-orange-950/60 border-orange-500/30',  icon: 'text-orange-400'  },
  CRITICAL: { border: 'border-red-500/30',     badge: 'text-red-400 bg-red-950/60 border-red-500/30',           icon: 'text-red-400'     },
};

const REC_STYLES: Record<string, string> = {
  MONITOR:       'text-blue-400 bg-blue-950/60 border-blue-500/30',
  WARN:          'text-amber-400 bg-amber-950/60 border-amber-500/30',
  TEMP_BAN:      'text-orange-400 bg-orange-950/60 border-orange-500/30',
  PERMANENT_BAN: 'text-red-400 bg-red-950/60 border-red-500/30',
  FALSE_POSITIVE:'text-emerald-400 bg-emerald-950/60 border-emerald-500/30',
};

export const PlayerAIReviewPanel: React.FC<PlayerAIReviewPanelProps> = ({ uuid, username, onClose }) => {
  const [state, setState] = useState<'loading' | 'error' | 'result'>('loading');
  const [result, setResult] = useState<PlayerAIReview | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');

  const runReview = useCallback(async () => {
    setState('loading');
    setResult(null);
    setErrorMsg('');
    try {
      const data = await api.reviewPlayerFullAI(uuid);
      // Normalise: backend may return varied shapes
      const review: PlayerAIReview = {
        risk_level: data.risk_level || data.riskLevel || 'LOW',
        confidence: data.confidence ?? 0,
        reasoning: data.reasoning || data.analysis?.reasoning || 'No reasoning provided.',
        recommendation: data.recommendation || 'MONITOR',
        key_findings: data.key_findings || data.analysis?.key_findings || [],
        mitigating_factors: data.mitigating_factors || data.analysis?.mitigating_factors || [],
      };
      setResult(review);
      setState('result');
    } catch (err: any) {
      setErrorMsg(err?.message || 'AI review request failed.');
      setState('error');
    }
  }, [uuid]);

  useEffect(() => { runReview(); }, [runReview]);

  const riskStyle = result ? (RISK_STYLES[result.risk_level] || RISK_STYLES.LOW) : RISK_STYLES.LOW;

  return (
    <div className="fixed inset-y-0 right-0 z-[60] w-full max-w-sm flex flex-col border-l border-slate-700 bg-[#0b0e14] shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-400" />
          <div>
            <p className="text-sm font-bold text-white">AI Player Review</p>
            <p className="text-xs text-slate-400">{username}</p>
          </div>
        </div>
        <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {/* Loading */}
        {state === 'loading' && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-400">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
            <p className="text-sm">Analyzing player data...</p>
          </div>
        )}

        {/* Error */}
        {state === 'error' && (
          <div className="rounded-xl border border-red-500/30 bg-red-950/20 p-5 space-y-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-400" />
              <p className="text-sm font-semibold text-red-300">AI review failed</p>
            </div>
            <p className="text-xs text-red-400">{errorMsg}</p>
          </div>
        )}

        {/* Result */}
        {state === 'result' && result && (
          <>
            {/* Risk Level — prominent */}
            <div className={`rounded-xl border ${riskStyle.border} bg-slate-900/60 p-5 text-center space-y-2`}>
              <ShieldAlert className={`h-8 w-8 mx-auto ${riskStyle.icon}`} />
              <div>
                <span className={`inline-flex px-3 py-1 rounded-full text-sm font-bold border font-mono ${riskStyle.badge}`}>
                  {result.risk_level} RISK
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">{(result.confidence * 100).toFixed(0)}% confidence</p>
            </div>

            {/* Recommendation */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Recommendation</p>
              <span className={`inline-flex px-2.5 py-1 rounded-lg text-xs font-bold border font-mono ${REC_STYLES[result.recommendation] || 'text-slate-400 border-slate-700 bg-slate-800'}`}>
                {result.recommendation.replace('_', ' ')}
              </span>
            </div>

            {/* Reasoning */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Reasoning</p>
              <p className="text-sm text-slate-300 leading-relaxed">{result.reasoning}</p>
            </div>

            {/* Key Findings */}
            {result.key_findings.length > 0 && (
              <div className="rounded-xl border border-red-500/20 bg-red-950/10 p-4 space-y-2">
                <p className="text-xs font-semibold text-red-400 uppercase tracking-wider">Key Findings</p>
                <ul className="space-y-1.5">
                  {result.key_findings.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                      <AlertTriangle className="h-3.5 w-3.5 text-red-400 mt-0.5 shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Mitigating Factors */}
            {result.mitigating_factors.length > 0 && (
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/10 p-4 space-y-2">
                <p className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Mitigating Factors</p>
                <ul className="space-y-1.5">
                  {result.mitigating_factors.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 mt-0.5 shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer — Re-review always available */}
      <div className="border-t border-slate-800 px-5 py-4">
        <button
          onClick={runReview}
          disabled={state === 'loading'}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 text-sm font-semibold hover:bg-indigo-600/40 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`h-4 w-4 ${state === 'loading' ? 'animate-spin' : ''}`} />
          Re-review
        </button>
      </div>
    </div>
  );
};

export default PlayerAIReviewPanel;
