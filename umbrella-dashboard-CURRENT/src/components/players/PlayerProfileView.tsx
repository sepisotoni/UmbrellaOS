import React, { useState, useEffect } from 'react';
import { api, FullProfileResponse } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import {
  ArrowLeft,
  Shield,
  ShieldAlert,
  AlertTriangle,
  Scale,
  UserX,
  Clock,
  Calendar,
  Activity,
  CheckCircle2,
  RefreshCw,
  Sparkles,
  ExternalLink,
  Ban,
  Radio,
  FileText,
} from 'lucide-react';

interface PlayerProfileViewProps {
  playerUuid: string;
  onBack: () => void;
  onOpenBanModal?: (playerUuid: string) => void;
}

type ProfileTab = 'overview' | 'punishments' | 'anticheat' | 'appeals' | 'alts';

export const PlayerProfileView: React.FC<PlayerProfileViewProps> = ({
  playerUuid,
  onBack,
  onOpenBanModal,
}) => {
  const { addToast, navigateToAppeal } = useDashboard();
  const [profile, setProfile] = useState<FullProfileResponse | null>(null);
  const [activeTab, setActiveTab] = useState<ProfileTab>('overview');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // AI Review state
  const [aiReviewLoading, setAiReviewLoading] = useState<boolean>(false);
  const [aiReviewResult, setAiReviewResult] = useState<any | null>(null);
  const [aiReviewError, setAiReviewError] = useState<string | null>(null);

  const fetchProfile = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getPlayerFullProfile(playerUuid);
      setProfile(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load player full profile');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, [playerUuid]);

  const handleTriggerAIReview = async () => {
    setAiReviewLoading(true);
    setAiReviewError(null);
    try {
      const result = await api.triggerPlayerAIReview(playerUuid);
      setAiReviewResult(result);
      addToast({
        type: 'success',
        title: 'AI Review Completed',
        message: 'On-demand GrimAC behavioral analysis finished.',
      });
      // Refresh profile to pick up any updated ai logs
      fetchProfile();
    } catch (err: any) {
      const msg = err.message || 'AI Review service unavailable.';
      setAiReviewError(msg);
      addToast({
        type: 'error',
        title: 'AI Review Failed',
        message: msg,
      });
    } finally {
      setAiReviewLoading(false);
    }
  };

  const handleMarkFalsePositive = async (altUuid: string) => {
    try {
      await api.markAltFalsePositive(undefined, altUuid);
      addToast({
        type: 'success',
        title: 'Marked False Positive',
        message: `Alt link for ${altUuid.slice(0, 8)} cleared.`,
      });
      fetchProfile();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Failed to clear alt link',
        message: err.message,
      });
    }
  };

  if (isLoading) {
    return (
      <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-12 text-center">
        <RefreshCw className="h-6 w-6 animate-spin text-purple-400 mx-auto mb-3" />
        <div className="text-sm font-mono text-slate-300">Loading full profile for {playerUuid}...</div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-6 space-y-4">
        <div className="flex items-center gap-3 text-rose-300">
          <AlertTriangle className="h-5 w-5 text-rose-400" />
          <span className="font-bold text-sm">Failed to retrieve profile: {error || 'Player not found'}</span>
        </div>
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3.5 py-1.5 text-xs text-slate-300 hover:text-white"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Players</span>
        </button>
      </div>
    );
  }

  const { player, verification, punishment_history, anticheat_history, appeal_history, alt_accounts } = profile;

  return (
    <div id="umbrella-player-profile-view" className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1e1b4b]">
        <div className="flex items-center gap-4">
          <button
            id="player-profile-back-btn"
            onClick={onBack}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#1e1b4b] bg-[#0d1127] text-slate-300 hover:border-purple-500/40 hover:text-white transition cursor-pointer"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>

          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-purple-900/60 border border-purple-500/40 flex items-center justify-center text-lg font-bold text-purple-300 font-mono">
              {player.username ? player.username.charAt(0).toUpperCase() : '?'}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-white font-mono">{player.username}</h1>
                {/* AUDIT-2026-08-29 fix: VerificationSchema.status is always
                    lowercase "verified"/"unverified" (api/routers/players.py) —
                    comparing to 'VERIFIED' never matched. */}
                {verification?.status === 'verified' ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-800/40">
                    <CheckCircle2 className="h-3 w-3" />
                    Verified
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-slate-900 text-slate-400 border border-slate-800">
                    Unverified
                  </span>
                )}
              </div>
              <div className="text-xs text-slate-400 font-mono">{player.uuid}</div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onOpenBanModal && (
            <button
              id="player-profile-punish-btn"
              onClick={() => onOpenBanModal(player.uuid)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/40 bg-rose-950/40 px-3 py-1.5 text-xs font-semibold text-rose-200 hover:bg-rose-900/50 transition cursor-pointer"
            >
              <Ban className="h-3.5 w-3.5 text-rose-400" />
              <span>Issue Punishment</span>
            </button>
          )}

          <button
            id="player-profile-refresh-btn"
            onClick={fetchProfile}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-purple-500/40 hover:text-white transition cursor-pointer"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Tabs bar */}
      <div className="flex border-b border-[#1e1b4b] gap-2 overflow-x-auto pb-px">
        {[
          { id: 'overview', label: 'Overview', icon: FileText },
          { id: 'punishments', label: `Punishments (${punishment_history?.length || 0})`, icon: ShieldAlert },
          { id: 'anticheat', label: `Anticheat (${anticheat_history?.total_flags || 0})`, icon: Shield },
          { id: 'appeals', label: `Appeals (${appeal_history?.length || 0})`, icon: Scale },
          { id: 'alts', label: `Alts (${alt_accounts?.length || 0})`, icon: UserX },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              id={`player-tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id as ProfileTab)}
              className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-t-lg transition border-t border-x cursor-pointer ${
                isActive
                  ? 'bg-[#0d1127] text-purple-300 border-[#1e1b4b] border-b-transparent -mb-px shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-[#0d1127]/40'
              }`}
            >
              <Icon className={`h-3.5 w-3.5 ${isActive ? 'text-purple-400' : 'text-slate-400'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-4">
              <div className="text-xs text-slate-400 font-mono uppercase">Current Server</div>
              <div className="mt-1 text-sm font-bold text-white font-mono">
                {player.current_server || 'Offline'}
              </div>
            </div>

            <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-4">
              <div className="text-xs text-slate-400 font-mono uppercase">Playtime</div>
              <div className="mt-1 text-sm font-bold text-white font-mono">
                {Math.round((player.playtime || 0) / 60)} hrs
              </div>
            </div>

            <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-4">
              <div className="text-xs text-slate-400 font-mono uppercase">Suspicion Score</div>
              <div className="mt-1 text-sm font-bold text-amber-400 font-mono">
                {player.suspicion_score || 0} / 100
              </div>
            </div>

            <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-4">
              <div className="text-xs text-slate-400 font-mono uppercase">Risk Score</div>
              <div className="mt-1 text-sm font-bold text-purple-300 font-mono">
                {player.risk_score || 0} / 100
              </div>
            </div>
          </div>

          {/* Details Table */}
          <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
            <h2 className="text-xs font-bold uppercase tracking-wider text-purple-400 font-mono mb-4">
              Profile Metadata
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="flex justify-between py-2 border-b border-[#1e1b4b]">
                <span className="text-slate-400">First Seen:</span>
                <span className="text-white font-mono">
                  {player.first_seen ? new Date(player.first_seen).toLocaleString() : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1e1b4b]">
                <span className="text-slate-400">Last Seen:</span>
                <span className="text-white font-mono">
                  {player.last_seen ? new Date(player.last_seen).toLocaleString() : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1e1b4b]">
                <span className="text-slate-400">Total Joins:</span>
                <span className="text-white font-mono">{player.joins || 0}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1e1b4b]">
                <span className="text-slate-400">Deaths:</span>
                <span className="text-white font-mono">{player.deaths || 0}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1e1b4b]">
                <span className="text-slate-400">Discord User ID:</span>
                <span className="text-purple-300 font-mono">
                  {verification?.discord_id || player.discord_id || 'Not Linked'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1e1b4b]">
                <span className="text-slate-400">Discord Username:</span>
                <span className="text-slate-200 font-mono">
                  {verification?.discord_username || 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Punishments */}
      {activeTab === 'punishments' && (
        <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-purple-400 font-mono">
              Punishment Records
            </h2>
          </div>

          {punishment_history.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500 font-mono">
              Clean record — no punishments on file for this player.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-[#1e1b4b] text-slate-400">
                    <th className="pb-3 font-semibold">Type</th>
                    <th className="pb-3 font-semibold">Reason</th>
                    <th className="pb-3 font-semibold">Staff</th>
                    <th className="pb-3 font-semibold">Issued At</th>
                    <th className="pb-3 font-semibold">Expires</th>
                    <th className="pb-3 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e1b4b]/60">
                  {punishment_history.map((p) => (
                    <tr key={p.id} className="hover:bg-[#121638]/50 transition">
                      <td className="py-3 font-bold uppercase text-purple-300">{p.type}</td>
                      <td className="py-3 text-slate-200">{p.reason}</td>
                      <td className="py-3 text-slate-400">{p.staff_id || 'AutoMod'}</td>
                      <td className="py-3 text-slate-400">
                        {p.created_at ? new Date(p.created_at).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="py-3 text-slate-400">
                        {p.expires_at ? new Date(p.expires_at).toLocaleDateString() : 'Permanent'}
                      </td>
                      <td className="py-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                            p.active
                              ? 'bg-rose-950/80 text-rose-300 border border-rose-800/40'
                              : 'bg-slate-900 text-slate-400 border border-slate-800'
                          }`}
                        >
                          {p.active ? 'ACTIVE' : 'EXPIRED'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Anticheat & AI Review */}
      {activeTab === 'anticheat' && (
        <div className="space-y-6">
          {/* AI Review Trigger Bar */}
          <div className="rounded-xl border border-purple-500/30 bg-purple-950/30 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 font-bold text-white text-sm">
                <Sparkles className="h-4 w-4 text-purple-400" />
                <span>On-Demand AI Anticheat Analysis</span>
              </div>
              <p className="text-xs text-purple-300/80 mt-0.5">
                Evaluates 30-day GrimAC flag trends, violation distribution, and false-positive risk.
              </p>
            </div>

            <button
              id="trigger-ai-player-review-btn"
              onClick={handleTriggerAIReview}
              disabled={aiReviewLoading}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-purple-500/50 bg-purple-600 hover:bg-purple-500 px-4 py-2 text-xs font-bold text-white transition shadow-[0_0_15px_rgba(168,85,247,0.3)] disabled:opacity-50 cursor-pointer"
            >
              <Sparkles className={`h-3.5 w-3.5 ${aiReviewLoading ? 'animate-spin' : ''}`} />
              <span>{aiReviewLoading ? 'Analyzing Cheat History...' : 'Trigger AI Review'}</span>
            </button>
          </div>

          {aiReviewError && (
            <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
              <div>
                <span className="font-bold">AI Review Error (503 Service Unavailable):</span>
                <p className="mt-0.5 text-rose-200/80">{aiReviewError}</p>
                <button
                  onClick={handleTriggerAIReview}
                  className="mt-2 text-xs text-purple-300 underline hover:text-white cursor-pointer"
                >
                  Re-review player
                </button>
              </div>
            </div>
          )}

          {aiReviewResult && (
            <div className="rounded-xl border border-purple-500/40 bg-[#0d1127] p-5 shadow-xl space-y-3">
              <div className="flex items-center justify-between border-b border-[#1e1b4b] pb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-purple-300 font-mono">
                  AI Review Recommendation
                </span>
                <span className="text-xs font-mono font-bold text-white">
                  Confidence: {Math.round((aiReviewResult.ai_confidence || 0.85) * 100)}%
                </span>
              </div>
              <div className="text-xs text-slate-200 whitespace-pre-wrap">
                {aiReviewResult.ai_summary || aiReviewResult.reasoning || JSON.stringify(aiReviewResult)}
              </div>
            </div>
          )}

          {/* Grim Check Breakdown */}
          <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
            <h2 className="text-xs font-bold uppercase tracking-wider text-purple-400 font-mono mb-4">
              GrimAC Flag Summary by Check
            </h2>

            {Object.keys(anticheat_history.by_check || {}).length === 0 ? (
              <div className="py-6 text-center text-xs text-slate-500 font-mono">
                No GrimAC flags registered for this player.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(anticheat_history.by_check).map(([check, stats]: [string, any]) => (
                  <div key={check} className="rounded-lg border border-[#1a1f42] bg-[#070914] p-3">
                    <div className="text-xs font-bold text-rose-400 font-mono">{check}</div>
                    <div className="mt-2 flex justify-between text-[11px] text-slate-400 font-mono">
                      <span>Flags: <strong className="text-white">{stats?.count || 1}</strong></span>
                      <span>Max VL: <strong className="text-amber-400">{stats?.max_vl || stats?.vl || 1}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Timeline */}
          <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
            <h2 className="text-xs font-bold uppercase tracking-wider text-purple-400 font-mono mb-4">
              Recent Violation Timeline
            </h2>
            {(!anticheat_history.timeline || anticheat_history.timeline.length === 0) ? (
              <div className="py-6 text-center text-xs text-slate-500 font-mono">
                No timeline records available.
              </div>
            ) : (
              <div className="space-y-2">
                {anticheat_history.timeline.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between rounded-lg border border-[#1a1f42] bg-[#070914] p-2.5 text-xs font-mono"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-rose-400 font-bold">{item.check_name}</span>
                      <span className="text-slate-400 text-[11px] truncate max-w-md">
                        {item.verbose || 'Flagged by heuristics'}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="px-1.5 py-0.5 rounded bg-rose-950/80 text-rose-300 font-bold text-[10px]">
                        VL {item.vl}
                      </span>
                      <span className="text-slate-500 text-[10px]">
                        {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : ''}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Appeals */}
      {activeTab === 'appeals' && (
        <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
          <h2 className="text-xs font-bold uppercase tracking-wider text-purple-400 font-mono mb-4">
            Appeal History
          </h2>
          {appeal_history.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500 font-mono">
              No appeals submitted by this player.
            </div>
          ) : (
            <div className="space-y-3">
              {appeal_history.map((app) => (
                <div
                  key={app.id}
                  onClick={() => navigateToAppeal(app.id)}
                  className="rounded-lg border border-[#1a1f42] bg-[#070914] p-4 hover:border-purple-500/40 transition cursor-pointer"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white font-mono">Appeal #{app.id.slice(0, 8)}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-950/80 text-purple-300 border border-purple-800/40 uppercase">
                      {app.status}
                    </span>
                  </div>
                  {app.action_taken && (
                    <div className="mt-2 text-xs text-emerald-400 font-mono">
                      Action Taken: {app.action_taken} ({app.handled_by || 'Staff'})
                    </div>
                  )}
                  {app.case_summary && (
                    <div className="mt-1 text-xs text-slate-300">{app.case_summary}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Alts */}
      {activeTab === 'alts' && (
        <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
          <h2 className="text-xs font-bold uppercase tracking-wider text-purple-400 font-mono mb-4">
            Linked Alt Accounts
          </h2>
          {alt_accounts.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500 font-mono">
              No associated alt accounts detected.
            </div>
          ) : (
            <div className="space-y-3">
              {alt_accounts.map((alt) => (
                <div
                  key={alt.uuid}
                  className="flex items-center justify-between rounded-lg border border-[#1a1f42] bg-[#070914] p-3 text-xs font-mono"
                >
                  <div>
                    <div className="font-bold text-white">{alt.username || alt.uuid.slice(0, 8)}</div>
                    <div className="text-[10px] text-slate-500">{alt.uuid}</div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 text-[10px] border border-amber-800/40">
                      {alt.cluster_type || 'IP Cluster'} ({alt.confidence || 'Medium'})
                    </span>

                    <button
                      onClick={() => handleMarkFalsePositive(alt.uuid)}
                      className="px-2.5 py-1 rounded border border-[#1e1b4b] bg-[#0d1127] text-slate-400 hover:text-white hover:border-purple-500/40 text-[11px] transition cursor-pointer"
                    >
                      False Positive
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
