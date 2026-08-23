import React, { useState, useEffect } from 'react';
import { PlayerProfileView } from '../players/PlayerProfileView';
import { AppealDetailPanel } from './AppealDetailPanel';
import { useDashboard } from '../../context/DashboardContext';
import { PunishmentRecord, GrimACViolation, AppealTicket } from '../../types/dashboard';
import api from '../../lib/api';
import {
  ShieldAlert,
  Search,
  Filter,
  Lock,
  Radio,
  Users,
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
  ExternalLink,
  ChevronRight,
  UserX,
  VolumeX,
  Ban,
  Activity,
  Fingerprint
} from 'lucide-react';

interface ModerationViewProps {
  onOpenBanModal: () => void;
}

export const ModerationView: React.FC<ModerationViewProps> = ({ onOpenBanModal }) => {
  const {
    punishments,
    pardonPunishment,
    altClusters,
    banAltRing,
    appeals,
    resolveAppeal,
    players,
    addToast
  } = useDashboard();

  // Real anticheat violations — fetched from backend
  const [grimViolations, setGrimViolations] = useState<any[]>([]);
  const [violationsLoading, setViolationsLoading] = useState(false);
  const [violationsError, setViolationsError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchViolations = async () => {
      setViolationsLoading(true);
      setViolationsError(null);
      try {
        const data = await api.getAnticheatViolations({ limit: 50 });
        if (!cancelled) setGrimViolations(data);
      } catch (err: any) {
        if (!cancelled) setViolationsError(err?.message || 'Failed to load anticheat violations.');
      } finally {
        if (!cancelled) setViolationsLoading(false);
      }
    };
    fetchViolations();
    return () => { cancelled = true; };
  }, []);


  // P15: Player profile + appeal detail state
  const [profileTarget, setProfileTarget] = useState<{ uuid: string; username: string; defaultTab?: any; filterFrom?: Date; filterTo?: Date } | null>(null);
  const [selectedAppeal, setSelectedAppeal] = useState<any | null>(null);

  type SubTab = 'punishments' | 'grimac' | 'alt-detection' | 'appeals';
  const [subTab, setSubTab] = useState<SubTab>('punishments');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');

  // Filter Punishments
  const filteredPunishments = punishments.filter(p => {
    const matchesSearch = !searchTerm || 
      p.playerName.toLowerCase().includes(searchTerm.toLowerCase()) || 
      p.reason.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.staffName.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || p.status === statusFilter;
    const matchesType = typeFilter === 'ALL' || p.type.includes(typeFilter);
    return matchesSearch && matchesStatus && matchesType;
  });

  const pendingAppeals = appeals.filter(a => a.status === 'PENDING' || a.status === 'AI_REVIEWED');

  return (
    <div className="space-y-6 pb-12">
      {/* View Header & Sub-Tabs */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-rose-500/30 bg-rose-950/40 text-rose-400">
              <ShieldAlert className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight font-display">
                Moderation & GrimAC Security Center
              </h1>
              <p className="text-xs text-slate-400">
                Network-wide bans ledger, predictive packet anticheat flags, multi-account graph, and AI appeals triage
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onOpenBanModal}
            className="flex items-center gap-1.5 rounded-lg bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-500 transition-colors shadow-sm font-mono"
          >
            <Ban className="h-3.5 w-3.5" />
            <span>Issue New Punishment</span>
          </button>
        </div>
      </div>

      {/* Sub-Navigation Buttons */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto">
        <button
          onClick={() => setSubTab('punishments')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
            subTab === 'punishments'
              ? 'bg-slate-800 text-cyan-400 border border-slate-700 shadow-sm'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <Lock className="h-3.5 w-3.5" />
          <span>Punishments Ledger</span>
          <span className="font-mono text-[10px] bg-slate-900 px-1.5 py-0.2 rounded border border-slate-800">
            {punishments.length}
          </span>
        </button>

        <button
          onClick={() => setSubTab('grimac')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
            subTab === 'grimac'
              ? 'bg-slate-800 text-rose-400 border border-slate-700 shadow-sm'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <Activity className="h-3.5 w-3.5" />
          <span>GrimAC Live Stream</span>
          <span className="font-mono text-[10px] bg-rose-950/80 text-rose-300 px-1.5 py-0.2 rounded border border-rose-500/30">
            {grimViolations.length} Live
          </span>
        </button>

        <button
          onClick={() => setSubTab('alt-detection')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
            subTab === 'alt-detection'
              ? 'bg-slate-800 text-amber-400 border border-slate-700 shadow-sm'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <Fingerprint className="h-3.5 w-3.5" />
          <span>Alt Account Rings & Clusters</span>
          <span className="font-mono text-[10px] bg-amber-950/80 text-amber-300 px-1.5 py-0.2 rounded border border-amber-500/30">
            {altClusters.length} Rings
          </span>
        </button>

        <button
          onClick={() => setSubTab('appeals')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
            subTab === 'appeals'
              ? 'bg-slate-800 text-indigo-400 border border-slate-700 shadow-sm'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <FileText className="h-3.5 w-3.5" />
          <span>Appeals Desk (AI Triage)</span>
          {pendingAppeals.length > 0 && (
            <span className="font-mono text-[10px] bg-indigo-950/80 text-indigo-300 px-1.5 py-0.2 rounded border border-indigo-500/30">
              {pendingAppeals.length} Pending
            </span>
          )}
        </button>
      </div>

      {/* Tab 1: Punishments Ledger */}
      {subTab === 'punishments' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-[#0c1017] p-3 rounded-xl border border-slate-800">
            <div className="flex items-center gap-2 flex-1 max-w-md">
              <Search className="h-4 w-4 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by player name, reason, or staff..."
                className="w-full bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none font-mono"
              />
            </div>

            <div className="flex items-center gap-2 text-xs font-mono">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-lg border border-slate-800 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none font-mono"
              >
                <option value="ALL">All Statuses</option>
                <option value="ACTIVE">Active Only</option>
                <option value="EXPIRED">Expired</option>
                <option value="PARDONED">Pardoned</option>
              </select>

              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="rounded-lg border border-slate-800 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none font-mono"
              >
                <option value="ALL">All Types</option>
                <option value="BAN">Bans (Perm/Temp/HWID)</option>
                <option value="MUTE">Mutes</option>
                <option value="WARN">Warnings</option>
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="rounded-xl border border-slate-800 bg-[#0c1017] overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="border-b border-slate-800 bg-slate-900/60 font-mono text-[11px] text-slate-400">
                  <tr>
                    <th className="py-3 px-4">Player & ID</th>
                    <th className="py-3 px-3">Type</th>
                    <th className="py-3 px-4">Reason & Evidence</th>
                    <th className="py-3 px-3">Issuer</th>
                    <th className="py-3 px-3">Dates & Scope</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {filteredPunishments.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-xs text-slate-500 font-mono">
                        No punishment records found matching criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredPunishments.map(p => (
                      <tr key={p.id} className="hover:bg-slate-900/40 transition-colors">
                        <td className="py-3 px-4">
                          <button
                            onClick={() => setProfileTarget({ uuid: p.playerUuid, username: p.playerName })}
                            className="font-bold text-cyan-400 hover:text-cyan-300 flex items-center gap-1.5 font-mono transition-colors"
                          >
                            {p.playerName}
                          </button>
                          <div className="text-[10px] font-mono text-slate-500 mt-0.5">#{p.id}</div>
                        </td>
                        <td className="py-3 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                            p.type.includes('BAN') ? 'bg-rose-950/40 text-rose-300 border-rose-500/30' :
                            p.type.includes('MUTE') ? 'bg-amber-950/40 text-amber-300 border-amber-500/30' :
                            'bg-slate-800 text-slate-300 border-slate-700'
                          }`}>
                            {p.type}
                          </span>
                        </td>
                        <td className="py-3 px-4 max-w-xs">
                          <div className="text-slate-200 truncate font-mono text-[11px]">{p.reason}</div>
                          {p.evidenceUrl && (
                            <a 
                              href={p.evidenceUrl} 
                              target="_blank" 
                              rel="noreferrer"
                              className="text-[10px] text-cyan-400 hover:underline flex items-center gap-1 mt-0.5 font-mono"
                            >
                              <span>View Evidence</span>
                              <ExternalLink className="h-2.5 w-2.5" />
                            </a>
                          )}
                        </td>
                        <td className="py-3 px-3 font-mono text-slate-400">
                          <div>{p.staffName}</div>
                          {(p.staffName === 'GrimAC AutoMod' || p.staffName === 'GrimAC') && (
                            <button
                              onClick={() => {
                                const banTime = new Date(p.createdAt);
                                setProfileTarget({
                                  uuid: p.playerUuid,
                                  username: p.playerName,
                                  defaultTab: 'anticheat',
                                  filterFrom: new Date(banTime.getTime() - 10 * 60 * 1000),
                                  filterTo: new Date(banTime.getTime() + 10 * 60 * 1000),
                                });
                              }}
                              className="text-[10px] text-amber-400 hover:text-amber-300 flex items-center gap-1 mt-0.5 font-mono transition-colors"
                            >
                              <ExternalLink className="h-2.5 w-2.5" />
                              View Evidence
                            </button>
                          )}
                        </td>
                        <td className="py-3 px-3 font-mono text-[11px] text-slate-400">
                          <div>{p.createdAt}</div>
                          <div className="text-[10px] text-slate-500">
                            {p.expiresAt ? `Exp: ${p.expiresAt}` : 'Permanent'} • {p.serverScope}
                          </div>
                        </td>
                        <td className="py-3 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                            p.status === 'ACTIVE' ? 'bg-rose-950/60 text-rose-300 border border-rose-600' :
                            p.status === 'PARDONED' ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-600' :
                            'bg-slate-800 text-slate-400'
                          }`}>
                            {p.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          {p.status === 'ACTIVE' && (
                            <button
                              onClick={() => pardonPunishment(p.id)}
                              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-emerald-900/60 text-slate-300 hover:text-emerald-200 border border-slate-700 text-xs font-mono transition-colors"
                            >
                              Pardon
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: GrimAC Live Violation Stream */}
      {subTab === 'grimac' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-fuchsia-500/30 bg-[#0c1017] p-4 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-lg bg-fuchsia-950/40 border border-fuchsia-500/30 flex items-center justify-center text-fuchsia-400">
                <Activity className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">GrimAC Quantum Packet Prediction Engine</h3>
                <p className="text-xs text-slate-400">
                  Sub-tick packet simulation for reach, angle delta, autoclicker kurtosis, and fly pathing.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
              <span className="text-xs font-mono text-emerald-400 font-bold">14 Prediction Checks Active</span>
            </div>
          </div>

          <div className="space-y-3">
            {violationsLoading ? (
              <div className="p-8 rounded-xl border border-slate-800 bg-[#0c1017] text-center text-xs text-slate-400 font-mono animate-pulse">
                Loading anticheat violations...
              </div>
            ) : violationsError ? (
              <div className="p-6 rounded-xl border border-rose-500/30 bg-rose-950/10 text-xs text-rose-400 font-mono">
                {violationsError}
              </div>
            ) : grimViolations.length === 0 ? (
              <div className="p-8 rounded-xl border border-slate-800 bg-[#0c1017] text-center text-xs text-slate-500 font-mono">
                No active violation packets streamed. Anticheat reporting clear status.
              </div>
            ) : (
              grimViolations.map(v => (
                <div
                  key={v.id}
                  className="rounded-xl border border-slate-800 bg-[#0c1017] p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className="h-8 w-8 rounded-lg bg-rose-950/40 border border-rose-500/30 flex items-center justify-center text-rose-400 font-bold font-mono text-xs shrink-0">
                      VL{v.violationLevel}
                    </div>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-bold text-white font-mono">{v.playerName}</span>
                        <span className="text-[11px] font-mono text-rose-400 font-semibold bg-rose-950/40 border border-rose-500/20 px-1.5 py-0.2 rounded">
                          Failed: {v.checkName}
                        </span>
                        <span className="text-[11px] font-mono text-slate-400">@{v.server}</span>
                        <span className="text-[10px] font-mono text-slate-500">• Ping {v.playerPing}ms • TPS {v.tpsAtTime}</span>
                      </div>
                      <p className="text-xs text-slate-300 mt-1 font-mono">{v.details}</p>
                      {v.autoMitigationTaken && (
                        <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-cyan-300 font-mono">
                          <CheckCircle2 className="h-3 w-3 text-cyan-400" />
                          <span>Autonomous Action: {v.autoMitigationTaken}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 font-mono">
                    <button
                      onClick={() => {
                        addToast('info', 'Spectator Teleport', `Teleported staff view to ${v.playerName} on ${v.server}.`);
                      }}
                      className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 text-xs font-semibold text-slate-300 hover:text-white transition-colors"
                    >
                      Spectate
                    </button>
                    <button
                      onClick={onOpenBanModal}
                      className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white transition-colors"
                    >
                      Ban Player
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Alt Account Detection & Clustering Graph */}
      {subTab === 'alt-detection' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-amber-500/30 bg-[#0c1017] p-4 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-lg bg-amber-950/40 border border-amber-500/30 flex items-center justify-center text-amber-400">
                <Fingerprint className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Heuristic Alt Ring Clustering & VPN Detector</h3>
                <p className="text-xs text-slate-400">
                  Groups multi-account evasion rings based on HWID hash collision, subnet IP bursts, and telemetry tokens.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {altClusters.length === 0 ? (
              <div className="col-span-2 p-8 rounded-xl border border-slate-800 bg-[#0c1017] text-center text-xs text-slate-500 font-mono">
                No flagged alt account clusters in database.
              </div>
            ) : (
              altClusters.map(cluster => (
                <div
                  key={cluster.id}
                  className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-3 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white font-mono">{cluster.id}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                        cluster.status === 'CONFIRMED_ALT_RING' ? 'bg-rose-950/40 text-rose-300 border-rose-500/30' :
                        cluster.status === 'WHITELISTED_HOUSEHOLD' ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30' :
                        'bg-amber-950/40 text-amber-300 border-amber-500/30'
                      }`}>
                        {cluster.status}
                      </span>
                    </div>

                    <div className="mt-2 text-xs text-slate-300 font-mono">
                      <strong className="text-cyan-400">{cluster.rootIdentifier}</strong>
                    </div>

                    <div className="mt-3">
                      <span className="text-[11px] text-slate-400 font-semibold font-mono">Associated Accounts ({cluster.associatedAccounts.length}):</span>
                      <div className="flex flex-wrap gap-1.5 mt-1.5">
                        {cluster.associatedAccounts.map(acc => (
                          <span 
                            key={acc}
                            className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 font-mono text-[11px] text-slate-200"
                          >
                            {acc}
                          </span>
                        ))}
                      </div>
                    </div>

                    <p className="text-xs text-slate-400 mt-3 italic font-mono">
                      "{cluster.notes}"
                    </p>
                  </div>

                  <div className="pt-3 border-t border-slate-800 flex items-center justify-between font-mono">
                    <span className="text-xs text-slate-400">
                      Confidence: <strong className="text-amber-400">{cluster.confidence}%</strong>
                    </span>

                    {cluster.status !== 'CONFIRMED_ALT_RING' ? (
                      <button
                        onClick={() => banAltRing(cluster.id)}
                        className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white transition-colors"
                      >
                        Bulk-Ban Cluster
                      </button>
                    ) : (
                      <span className="text-xs text-rose-400 font-semibold">
                        All Alts Blacklisted ({cluster.bannedCount})
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Appeals Desk & AI Triage */}
      {subTab === 'appeals' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-indigo-500/30 bg-[#0c1017] p-4 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-lg bg-indigo-950/40 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">AI Sentiment & Remorse Appeal Analysis</h3>
                <p className="text-xs text-slate-400">
                  Cross-references player history, anticheat violation replays, and sentiment markers.
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            {appeals.length === 0 ? (
              <div className="p-8 rounded-xl border border-slate-800 bg-[#0c1017] text-center text-xs text-slate-500 font-mono">
                Zero pending appeals currently in queue.
              </div>
            ) : (
              appeals.map(ticket => {
                const ticketAny = ticket as any;
                const isClosed = ['ACCEPTED','REJECTED','ESCALATED','REVIEW_SCHEDULED'].includes(ticket.status);
                return (
                <div
                  key={ticket.id}
                  className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4 cursor-pointer hover:border-slate-700 transition-colors"
                  onClick={() => setSelectedAppeal(ticketAny)}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        {isClosed && ticketAny.action_taken && (
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                            ticketAny.action_taken === 'ACCEPT' ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30' :
                            ticketAny.action_taken === 'REJECT' ? 'bg-rose-950/40 text-rose-300 border-rose-500/30' :
                            ticketAny.action_taken === 'ESCALATE' ? 'bg-orange-950/40 text-orange-300 border-orange-500/30' :
                            'bg-purple-950/40 text-purple-300 border-purple-500/30'
                          }`}>
                            {ticketAny.action_taken === 'ACCEPT' ? '✅ ACCEPTED' :
                             ticketAny.action_taken === 'REJECT' ? '❌ REJECTED' :
                             ticketAny.action_taken === 'ESCALATE' ? '⬆️ ESCALATED' :
                             ticketAny.action_taken === 'SCHEDULE_REVIEW' ? '📞 REVIEW SCHEDULED' :
                             ticketAny.action_taken === 'REDUCE_SENTENCE' ? '⏳ SENTENCE REDUCED' :
                             ticket.status}
                          </span>
                        )}
                        <span className="font-bold text-white text-sm font-mono">{ticket.playerUsername}</span>
                        <span className="text-[10px] font-mono text-slate-500">#{ticket.id}</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                          ticket.status === 'ACCEPTED' ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30' :
                          ticket.status === 'REJECTED' ? 'bg-rose-950/40 text-rose-300 border-rose-500/30' :
                          ticket.status === 'ESCALATED' ? 'bg-orange-950/40 text-orange-300 border-orange-500/30' :
                          ticket.status === 'REVIEW_SCHEDULED' ? 'bg-purple-950/40 text-purple-300 border-purple-500/30' :
                          'bg-amber-950/40 text-amber-300 border-amber-500/30'
                        }`}>
                          {ticket.status}
                        </span>
                        {/* AI review status badge */}
                        {ticketAny.ai_review_status && (
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                            ticketAny.ai_review_status === 'COMPLETED' ? 'bg-indigo-950/40 text-indigo-300 border-indigo-500/30' :
                            ticketAny.ai_review_status === 'FAILED' ? 'bg-red-950/40 text-red-300 border-red-500/30' :
                            'bg-slate-800 text-slate-400 border-slate-700'
                          }`}>
                            {ticketAny.ai_review_status === 'COMPLETED' ? '🤖 AI Reviewed' :
                             ticketAny.ai_review_status === 'FAILED' ? '⚠️ AI Failed' : '⏳ Pending AI'}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5 font-mono">
                        Original Punishment: <strong className="text-rose-400">{ticket.originalReason}</strong>
                      </div>
                    </div>
                    <div className="text-xs font-mono text-slate-500">
                      Submitted: {ticket.createdAt}
                    </div>
                  </div>

                  {/* Player's Statement */}
                  <div>
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1 font-mono">
                      Player Statement:
                    </label>
                    <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/70 text-xs text-slate-200 italic font-mono">
                      "{ticket.appealReason}"
                    </div>
                  </div>

                  {/* AI Triage Card */}
                  <div className="rounded-lg border border-indigo-500/30 bg-indigo-950/20 p-3.5 space-y-2">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <div className="flex items-center gap-1.5 font-bold text-indigo-300">
                        <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
                        <span>Umbrella AI Recommendation: {ticket.aiRecommendedAction}</span>
                      </div>
                      <span className="text-[11px] text-indigo-300">
                        Authenticity Score: <strong>{ticket.aiSentimentScore}/100</strong>
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed font-mono text-[11px]">
                      {ticket.aiAnalysisSummary}
                    </p>
                  </div>

                  {/* Staff Verdict Buttons */}
                  {ticket.status !== 'ACCEPTED' && ticket.status !== 'REJECTED' && (
                    <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800 font-mono">
                      <button
                        onClick={() => resolveAppeal(ticket.id, 'REJECTED')}
                        className="px-4 py-2 rounded-lg border border-rose-500/30 bg-rose-950/30 hover:bg-rose-900/50 text-rose-200 text-xs font-semibold transition-colors flex items-center gap-1.5"
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        <span>Reject Appeal</span>
                      </button>
                      <button
                        onClick={() => resolveAppeal(ticket.id, 'ACCEPTED')}
                        className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors flex items-center gap-1.5"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>Approve & Unban</span>
                      </button>
                    </div>
                  )}
                </div>
              );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};
