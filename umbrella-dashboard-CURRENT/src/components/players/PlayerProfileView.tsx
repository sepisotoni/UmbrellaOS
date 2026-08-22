import React, { useState, useEffect, useCallback } from 'react';
import api from '../../lib/api';
import { PlayerFullProfile, AnticheatFlag } from '../../types/dashboard';
import { PlayerAIReviewPanel } from './PlayerAIReviewPanel';
import {
  X, Copy, CheckCircle2, Clock, Shield, User, Activity, FileText,
  AlertTriangle, Users, Sparkles, Ban, VolumeX, ChevronRight,
  ExternalLink, Search, RefreshCw, Eye
} from 'lucide-react';

interface PlayerProfileViewProps {
  uuid: string;
  username: string;
  onClose: () => void;
  onOpenBanModal?: (playerName: string) => void;
  defaultTab?: 'overview' | 'punishments' | 'anticheat' | 'appeals' | 'alts';
  filterFrom?: Date;
  filterTo?: Date;
}

type TabId = 'overview' | 'punishments' | 'anticheat' | 'appeals' | 'alts';

const RISK_COLOURS: Record<string, string> = {
  LOW: 'text-emerald-400 bg-emerald-950/60 border-emerald-500/30',
  MEDIUM: 'text-amber-400 bg-amber-950/60 border-amber-500/30',
  HIGH: 'text-orange-400 bg-orange-950/60 border-orange-500/30',
  CRITICAL: 'text-red-400 bg-red-950/60 border-red-500/30',
};

const STATUS_COLOURS: Record<string, string> = {
  OPEN: 'text-blue-400 bg-blue-950/60 border-blue-500/30',
  ACCEPTED: 'text-emerald-400 bg-emerald-950/60 border-emerald-500/30',
  REJECTED: 'text-red-400 bg-red-950/60 border-red-500/30',
  ESCALATED: 'text-orange-400 bg-orange-950/60 border-orange-500/30',
  REVIEW_SCHEDULED: 'text-purple-400 bg-purple-950/60 border-purple-500/30',
  PENDING: 'text-blue-400 bg-blue-950/60 border-blue-500/30',
  AI_REVIEWED: 'text-indigo-400 bg-indigo-950/60 border-indigo-500/30',
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); });
  };
  return (
    <button onClick={handleCopy} className="ml-1 text-slate-500 hover:text-cyan-400 transition-colors">
      {copied ? <CheckCircle2 className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
    </button>
  );
}

function SkeletonCard() {
  return (
    <div className="animate-pulse space-y-3 p-4 rounded-xl border border-slate-800 bg-slate-900/40">
      <div className="h-4 bg-slate-800 rounded w-1/3" />
      <div className="h-3 bg-slate-800 rounded w-2/3" />
      <div className="h-3 bg-slate-800 rounded w-1/2" />
    </div>
  );
}

function ErrorCard({ message, uuid, onRetry }: { message: string; uuid: string; onRetry: () => void }) {
  return (
    <div className="rounded-xl border border-red-500/40 bg-red-950/20 p-6 text-center space-y-3">
      <AlertTriangle className="h-8 w-8 text-red-400 mx-auto" />
      <p className="text-sm font-semibold text-red-300">Profile unavailable</p>
      <p className="text-xs text-slate-400 font-mono">{uuid}</p>
      <p className="text-xs text-red-400">{message}</p>
      <button onClick={onRetry} className="flex items-center gap-1.5 mx-auto px-3 py-1.5 rounded-lg bg-red-900/40 border border-red-500/30 text-red-300 text-xs hover:bg-red-900/60 transition-colors">
        <RefreshCw className="h-3 w-3" /> Retry
      </button>
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (!seconds) return '0h';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 24) return `${Math.floor(h / 24)}d ${h % 24}h`;
  return `${h}h ${m}m`;
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

export const PlayerProfileView: React.FC<PlayerProfileViewProps> = ({
  uuid, username, onClose, onOpenBanModal, defaultTab = 'overview', filterFrom, filterTo
}) => {
  const [profile, setProfile] = useState<PlayerFullProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>(defaultTab);
  const [checkFilter, setCheckFilter] = useState('');
  const [showAIPanel, setShowAIPanel] = useState(false);

  const fetchProfile = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.getPlayerFullProfile(uuid);
      setProfile(data as PlayerFullProfile);
    } catch (err: any) {
      setError(err?.message || 'Failed to load player profile.');
    } finally { setLoading(false); }
  }, [uuid]);

  useEffect(() => { fetchProfile(); }, [fetchProfile]);

  const riskLevel = profile?.player?.risk_score || 'LOW';
  const isOnline = profile?.player?.last_seen
    ? (Date.now() - new Date(profile.player.last_seen).getTime()) < 5 * 60 * 1000
    : false;

  const anticheatTimeline: AnticheatFlag[] = profile?.anticheat_history?.timeline || [];
  const filteredTimeline = anticheatTimeline.filter(f => {
    const matchesCheck = !checkFilter || f.check_name.toLowerCase().includes(checkFilter.toLowerCase());
    if (!filterFrom && !filterTo) return matchesCheck;
    const t = new Date(f.timestamp).getTime();
    const from = filterFrom ? filterFrom.getTime() : 0;
    const to = filterTo ? filterTo.getTime() : Infinity;
    return matchesCheck && t >= from && t <= to;
  }).slice(0, 50);

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <User className="h-3.5 w-3.5" /> },
    { id: 'punishments', label: 'Punishments', icon: <Shield className="h-3.5 w-3.5" /> },
    { id: 'anticheat', label: 'Anticheat', icon: <Activity className="h-3.5 w-3.5" /> },
    { id: 'appeals', label: 'Appeals', icon: <FileText className="h-3.5 w-3.5" /> },
    { id: 'alts', label: 'Alts', icon: <Users className="h-3.5 w-3.5" /> },
  ];

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4" onClick={onClose}>
        <div
          className="relative w-full max-w-5xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-700 bg-[#0c1017] shadow-2xl"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-slate-800 bg-[#0c1017]/95 backdrop-blur-sm px-6 py-4">
            <div className="flex items-center gap-4">
              <img
                src={`https://mc-heads.net/avatar/${username}/48`}
                alt={username}
                className="h-12 w-12 rounded-lg border border-slate-700"
              />
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-white font-display">{username}</h2>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border font-mono ${isOnline ? 'text-emerald-400 bg-emerald-950/60 border-emerald-500/30' : 'text-slate-400 bg-slate-800/60 border-slate-700'}`}>
                    {isOnline ? 'Online' : 'Offline'}
                  </span>
                  {riskLevel && (
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border font-mono ${RISK_COLOURS[riskLevel] || RISK_COLOURS.LOW}`}>
                      {riskLevel} Risk
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1 mt-0.5">
                  <span className="text-xs text-slate-500 font-mono">{uuid}</span>
                  <CopyButton text={uuid} />
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowAIPanel(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 text-xs font-semibold hover:bg-indigo-600/40 transition-colors"
              >
                <Sparkles className="h-3.5 w-3.5" /> AI Review
              </button>
              <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors">
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 border-b border-slate-800 px-6 pt-3">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-t-lg text-xs font-semibold transition-all ${
                  activeTab === tab.id
                    ? 'text-cyan-400 bg-slate-800 border-b-2 border-cyan-500'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {loading && (
              <div className="space-y-4">
                <SkeletonCard /><SkeletonCard /><SkeletonCard />
              </div>
            )}
            {!loading && error && <ErrorCard message={error} uuid={uuid} onRetry={fetchProfile} />}
            {!loading && !error && profile && (
              <>
                {/* TAB: Overview */}
                {activeTab === 'overview' && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {[
                        { label: 'First Seen', value: formatDate(profile.player.first_seen) },
                        { label: 'Last Seen', value: formatDate(profile.player.last_seen) },
                        { label: 'Playtime', value: formatDuration(profile.player.playtime) },
                        { label: 'Active Punishments', value: String(profile.punishment_history.filter(p => p.status === 'ACTIVE').length) },
                      ].map(stat => (
                        <div key={stat.label} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                          <p className="text-xs text-slate-500 mb-1">{stat.label}</p>
                          <p className="text-sm font-bold text-white font-mono">{stat.value}</p>
                        </div>
                      ))}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2">
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Verification</p>
                        {profile.verification ? (
                          <div className="flex items-center gap-2">
                            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                            <span className="text-sm text-white font-mono">{profile.verification.discord_username}</span>
                            <span className="text-xs text-slate-500">linked {formatDate(profile.verification.linked_at)}</span>
                          </div>
                        ) : (
                          <p className="text-sm text-slate-500">Not verified</p>
                        )}
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2">
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Alt Accounts</p>
                        <button
                          onClick={() => setActiveTab('alts')}
                          className="flex items-center gap-2 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                        >
                          <Users className="h-4 w-4" />
                          {profile.alt_accounts.length} linked accounts
                          <ChevronRight className="h-3 w-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB: Punishments */}
                {activeTab === 'punishments' && (
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <p className="text-xs text-slate-400">{profile.punishment_history.length} total punishments</p>
                      {onOpenBanModal && (
                        <button
                          onClick={() => onOpenBanModal(username)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-600/20 border border-rose-500/30 text-rose-300 text-xs font-semibold hover:bg-rose-600/40 transition-colors"
                        >
                          <Ban className="h-3 w-3" /> Issue Punishment
                        </button>
                      )}
                    </div>
                    {profile.punishment_history.length === 0 && (
                      <p className="text-sm text-slate-500 text-center py-8">No punishment history</p>
                    )}
                    <div className="space-y-2">
                      {profile.punishment_history.map(p => (
                        <div key={p.id} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 flex items-center gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border font-mono ${
                                p.type.includes('BAN') ? 'text-red-400 bg-red-950/60 border-red-500/30' :
                                p.type.includes('MUTE') ? 'text-amber-400 bg-amber-950/60 border-amber-500/30' :
                                'text-slate-400 bg-slate-800 border-slate-700'
                              }`}>{p.type}</span>
                              <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border font-mono ${
                                p.status === 'ACTIVE' ? 'text-red-400 bg-red-950/60 border-red-500/30' :
                                p.status === 'PARDONED' ? 'text-emerald-400 bg-emerald-950/60 border-emerald-500/30' :
                                'text-slate-400 bg-slate-800 border-slate-700'
                              }`}>{p.status}</span>
                            </div>
                            <p className="text-sm text-white truncate">{p.reason}</p>
                            <p className="text-xs text-slate-500 mt-0.5">
                              by {p.staff_name} · {formatDate(p.created_at)}
                              {p.expires_at && ` · expires ${formatDate(p.expires_at)}`}
                            </p>
                          </div>
                          {p.status === 'ACTIVE' && (
                            <button
                              onClick={async () => {
                                try { await api.revokePunishment(p.id); await fetchProfile(); }
                                catch { alert('Failed to revoke punishment'); }
                              }}
                              className="shrink-0 px-2 py-1 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-300 hover:bg-rose-950/40 hover:border-rose-500/30 hover:text-rose-300 transition-colors"
                            >
                              Revoke
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* TAB: Anticheat */}
                {activeTab === 'anticheat' && (
                  <div className="space-y-4">
                    {/* Summary cards */}
                    <div className="grid grid-cols-3 gap-3">
                      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                        <p className="text-xs text-slate-500 mb-1">Total Flags</p>
                        <p className="text-2xl font-bold text-white font-mono">{profile.anticheat_history.total_flags}</p>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                        <p className="text-xs text-slate-500 mb-1">Unique Checks</p>
                        <p className="text-2xl font-bold text-white font-mono">{Object.keys(profile.anticheat_history.by_check).length}</p>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                        <p className="text-xs text-slate-500 mb-1">Most Flagged</p>
                        <p className="text-sm font-bold text-amber-400 font-mono">
                          {Object.entries(profile.anticheat_history.by_check).sort((a, b) => b[1].count - a[1].count)[0]?.[0] || '—'}
                        </p>
                      </div>
                    </div>
                    {/* By Check breakdown */}
                    {Object.keys(profile.anticheat_history.by_check).length > 0 && (
                      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">By Check</p>
                        {Object.entries(profile.anticheat_history.by_check)
                          .sort((a, b) => b[1].count - a[1].count)
                          .map(([check, stats]) => {
                            const maxCount = Math.max(...Object.values(profile.anticheat_history.by_check).map(s => s.count));
                            const pct = maxCount > 0 ? (stats.count / maxCount) * 100 : 0;
                            return (
                              <div key={check} className="space-y-1">
                                <div className="flex items-center justify-between text-xs">
                                  <span className="text-white font-mono">{check}</span>
                                  <div className="flex gap-4 text-slate-400 font-mono">
                                    <span>{stats.count}x</span>
                                    <span>avg VL {stats.avg_vl.toFixed(1)}</span>
                                    <span>max VL {stats.max_vl}</span>
                                  </div>
                                </div>
                                <div className="h-1.5 rounded-full bg-slate-800">
                                  <div className="h-full rounded-full bg-amber-500/70" style={{ width: `${pct}%` }} />
                                </div>
                              </div>
                            );
                          })}
                      </div>
                    )}
                    {/* Timeline */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex-1">Timeline (last 50)</p>
                        <div className="flex items-center gap-2 bg-slate-900 rounded-lg border border-slate-800 px-2 py-1">
                          <Search className="h-3 w-3 text-slate-500" />
                          <input
                            value={checkFilter}
                            onChange={e => setCheckFilter(e.target.value)}
                            placeholder="Filter by check..."
                            className="bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none w-32 font-mono"
                          />
                        </div>
                      </div>
                      {filteredTimeline.length === 0
                        ? <p className="text-sm text-slate-500 text-center py-4">No anticheat flags</p>
                        : (
                          <div className="rounded-xl border border-slate-800 overflow-hidden">
                            <table className="w-full text-xs">
                              <thead>
                                <tr className="border-b border-slate-800 bg-slate-900/60">
                                  <th className="text-left px-3 py-2 text-slate-400 font-semibold">Check</th>
                                  <th className="text-left px-3 py-2 text-slate-400 font-semibold">VL</th>
                                  <th className="text-left px-3 py-2 text-slate-400 font-semibold">Verbose</th>
                                  <th className="text-left px-3 py-2 text-slate-400 font-semibold">Time</th>
                                  <th className="px-3 py-2" />
                                </tr>
                              </thead>
                              <tbody>
                                {filteredTimeline.map((flag, i) => (
                                  <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-900/40 transition-colors">
                                    <td className="px-3 py-2 font-mono text-amber-300">{flag.check_name}</td>
                                    <td className="px-3 py-2 font-mono text-white">{flag.vl}</td>
                                    <td className="px-3 py-2 text-slate-400 max-w-xs truncate">{flag.verbose}</td>
                                    <td className="px-3 py-2 text-slate-500 font-mono whitespace-nowrap">{formatDate(flag.timestamp)}</td>
                                    <td className="px-3 py-2">
                                      <button
                                        onClick={() => {
                                          const t = new Date(flag.timestamp);
                                          const from = new Date(t.getTime() - 10 * 60 * 1000);
                                          const to = new Date(t.getTime() + 10 * 60 * 1000);
                                          setCheckFilter('');
                                          setActiveTab('anticheat');
                                        }}
                                        className="flex items-center gap-1 text-slate-500 hover:text-cyan-400 transition-colors"
                                        title="View ±10min window"
                                      >
                                        <Eye className="h-3 w-3" />
                                      </button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                    </div>
                  </div>
                )}

                {/* TAB: Appeals */}
                {activeTab === 'appeals' && (
                  <div className="space-y-3">
                    <p className="text-xs text-slate-400">{profile.appeal_history.length} appeals</p>
                    {profile.appeal_history.length === 0 && (
                      <p className="text-sm text-slate-500 text-center py-8">No appeal history</p>
                    )}
                    {profile.appeal_history.map(appeal => (
                      <div key={appeal.id} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border font-mono ${STATUS_COLOURS[appeal.status] || 'text-slate-400 border-slate-700 bg-slate-800'}`}>
                            {appeal.status}
                          </span>
                          {appeal.action_taken && (
                            <span className="text-xs text-slate-400">{appeal.action_taken}</span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400">Submitted {formatDate(appeal.created_at)}</p>
                        {appeal.appeal_text && (
                          <p className="text-sm text-slate-300 line-clamp-2">{appeal.appeal_text}</p>
                        )}
                        {appeal.handled_by && (
                          <p className="text-xs text-slate-500">Handled by {appeal.handled_by}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* TAB: Alts */}
                {activeTab === 'alts' && (
                  <div className="space-y-3">
                    <p className="text-xs text-slate-400">{profile.alt_accounts.length} linked accounts</p>
                    {profile.alt_accounts.length === 0 && (
                      <p className="text-sm text-slate-500 text-center py-8">No alt accounts detected</p>
                    )}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {profile.alt_accounts.map(alt => (
                        <div key={alt.uuid} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2">
                          <div className="flex items-center gap-3">
                            <img src={`https://mc-heads.net/avatar/${alt.username}/32`} alt={alt.username} className="h-8 w-8 rounded border border-slate-700" />
                            <div>
                              <p className="text-sm font-semibold text-white">{alt.username}</p>
                              <p className="text-xs text-slate-500 font-mono truncate">{alt.uuid}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 text-xs">
                            <span className="text-amber-400 font-mono">{(alt.confidence * 100).toFixed(0)}% confidence</span>
                            <span className="text-slate-500">·</span>
                            <span className="text-slate-400">{alt.cluster_type}</span>
                          </div>
                          <button
                            onClick={async () => {
                              try { await api.reportFalsePositiveAlt(alt.uuid, 'Marked false positive by staff'); await fetchProfile(); }
                              catch { alert('Failed to mark as false positive'); }
                            }}
                            className="text-xs text-slate-400 hover:text-emerald-400 transition-colors"
                          >
                            Mark False Positive
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* AI Review Side Panel */}
      {showAIPanel && (
        <PlayerAIReviewPanel
          uuid={uuid}
          username={username}
          onClose={() => setShowAIPanel(false)}
        />
      )}
    </>
  );
};

export default PlayerProfileView;
