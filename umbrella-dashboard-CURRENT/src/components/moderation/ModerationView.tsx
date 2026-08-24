import React, { useState, useEffect } from 'react';
import { api, PunishmentSchema, AnticheatViolationRecord } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  ShieldAlert,
  Shield,
  Ban,
  AlertTriangle,
  RefreshCw,
  Search,
  Filter,
  Plus,
  ExternalLink,
  CheckCircle2,
  X,
  Clock,
} from 'lucide-react';

interface ModerationViewProps {
  onOpenBanModal?: () => void;
}

export const ModerationView: React.FC<ModerationViewProps> = ({ onOpenBanModal }) => {
  const { addToast, navigateToPlayer } = useDashboard();
  const [activeTab, setActiveTab] = useState<'punishments' | 'grimac'>('punishments');

  // Punishments State
  const [punishments, setPunishments] = useState<PunishmentSchema[]>([]);
  const [activeOnly, setActiveOnly] = useState<boolean>(false);
  const [punishmentsLoading, setPunishmentsLoading] = useState<boolean>(true);
  const [punishmentsError, setPunishmentsError] = useState<string | null>(null);

  // GrimAC State
  const [violations, setViolations] = useState<AnticheatViolationRecord[]>([]);
  const [grimCheckFilter, setGrimCheckFilter] = useState<string>('');
  const [violationsLoading, setViolationsLoading] = useState<boolean>(true);
  const [violationsError, setViolationsError] = useState<string | null>(null);

  // Issue Punishment Modal
  const [isIssueModalOpen, setIsIssueModalOpen] = useState<boolean>(false);
  const [newPlayerUuid, setNewPlayerUuid] = useState<string>('');
  const [newType, setNewType] = useState<string>('ban');
  const [newReason, setNewReason] = useState<string>('');
  const [newExpiresAt, setNewExpiresAt] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Violation detail modal for "View Evidence"
  const [selectedViolation, setSelectedViolation] = useState<AnticheatViolationRecord | null>(null);

  const fetchPunishments = async () => {
    setPunishmentsLoading(true);
    setPunishmentsError(null);
    try {
      const data = await api.getPunishments({ active_only: activeOnly, limit: 100 });
      setPunishments(data || []);
    } catch (err: any) {
      setPunishmentsError(err.message || 'Failed to load punishments');
    } finally {
      setPunishmentsLoading(false);
    }
  };

  const fetchViolations = async () => {
    setViolationsLoading(true);
    setViolationsError(null);
    try {
      const data = await api.getAnticheatViolations({
        check_name: grimCheckFilter || undefined,
        limit: 100,
      });
      setViolations(data || []);
    } catch (err: any) {
      setViolationsError(err.message || 'Failed to load GrimAC violations');
    } finally {
      setViolationsLoading(false);
    }
  };

  useEffect(() => {
    fetchPunishments();
  }, [activeOnly]);

  useEffect(() => {
    fetchViolations();
  }, [grimCheckFilter]);

  const handleRevoke = async (id: string) => {
    if (!confirm('Are you sure you want to revoke/pardon this punishment?')) return;
    try {
      await api.revokePunishment(id);
      addToast({
        type: 'success',
        title: 'Punishment Revoked',
        message: `Punishment ${id.slice(0, 8)} has been pardoned.`,
      });
      fetchPunishments();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Revoke Failed',
        message: err.message,
      });
    }
  };

  const handleCreatePunishment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlayerUuid.trim() || !newReason.trim()) return;

    setIsSubmitting(true);
    try {
      await api.createPunishment({
        player_uuid: newPlayerUuid.trim(),
        type: newType,
        reason: newReason.trim(),
        expires_at: newExpiresAt ? new Date(newExpiresAt).toISOString() : null,
      });
      addToast({
        type: 'success',
        title: 'Punishment Issued',
        message: `Successfully applied ${newType.toUpperCase()} to ${newPlayerUuid.slice(0, 8)}.`,
      });
      setIsIssueModalOpen(false);
      setNewPlayerUuid('');
      setNewReason('');
      setNewExpiresAt('');
      fetchPunishments();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Failed to issue punishment',
        message: err.message,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div id="umbrella-moderation-view" className="space-y-6">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Moderation & Anticheat</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage active bans, kicks, mutes, and inspect GrimAC heuristic triggers.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            id="moderation-issue-btn"
            onClick={() => setIsIssueModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/40 bg-rose-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-rose-500 transition cursor-pointer shadow-[0_0_12px_rgba(244,63,94,0.3)]"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Issue Punishment</span>
          </button>

          <button
            id="moderation-refresh-btn"
            onClick={() => {
              if (activeTab === 'punishments') fetchPunishments();
              else fetchViolations();
            }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-purple-500/40 hover:text-white transition cursor-pointer"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-[#1e1b4b] gap-2 pb-px">
        <button
          id="mod-tab-punishments"
          onClick={() => setActiveTab('punishments')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-t-lg transition border-t border-x cursor-pointer ${
            activeTab === 'punishments'
              ? 'bg-[#0d1127] text-purple-300 border-[#1e1b4b] border-b-transparent -mb-px shadow-sm'
              : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-[#0d1127]/40'
          }`}
        >
          <ShieldAlert className="h-3.5 w-3.5 text-rose-400" />
          <span>Punishments Record ({punishments.length})</span>
        </button>

        <button
          id="mod-tab-grimac"
          onClick={() => setActiveTab('grimac')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-t-lg transition border-t border-x cursor-pointer ${
            activeTab === 'grimac'
              ? 'bg-[#0d1127] text-purple-300 border-[#1e1b4b] border-b-transparent -mb-px shadow-sm'
              : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-[#0d1127]/40'
          }`}
        >
          <Shield className="h-3.5 w-3.5 text-purple-400" />
          <span>GrimAC Flags Feed ({violations.length})</span>
        </button>
      </div>

      {/* TAB 1: Punishments */}
      {activeTab === 'punishments' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none">
              <input
                id="filter-active-punishments"
                type="checkbox"
                checked={activeOnly}
                onChange={(e) => setActiveOnly(e.target.checked)}
                className="rounded border-[#1e1b4b] bg-[#070914] text-purple-600 focus:ring-purple-500"
              />
              <span>Show Active Only</span>
            </label>
          </div>

          {punishmentsError && (
            <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
              <div>
                <span className="font-bold">Error loading punishments:</span>
                <p className="mt-0.5 text-rose-200/80">{punishmentsError}</p>
              </div>
            </div>
          )}

          <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
            {punishmentsLoading ? (
              <div className="py-12 text-center text-xs text-slate-500 font-mono">
                Loading punishments from database...
              </div>
            ) : punishments.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500 font-mono">
                No punishments found.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-[#1e1b4b] text-slate-400">
                      <th className="pb-3 font-semibold">Type</th>
                      <th className="pb-3 font-semibold">Player</th>
                      <th className="pb-3 font-semibold">Reason</th>
                      <th className="pb-3 font-semibold">Staff</th>
                      <th className="pb-3 font-semibold">Issued At</th>
                      <th className="pb-3 font-semibold">Expires</th>
                      <th className="pb-3 font-semibold">Status</th>
                      <th className="pb-3 font-semibold text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1e1b4b]/60">
                    {punishments.map((p) => (
                      <tr key={p.id} className="hover:bg-[#121638]/50 transition">
                        <td className="py-3 font-bold uppercase text-purple-300">{p.type}</td>
                        <td
                          onClick={() => navigateToPlayer(p.player_uuid)}
                          className="py-3 text-slate-300 hover:text-purple-300 hover:underline cursor-pointer"
                        >
                          {p.player_name || p.player_uuid.slice(0, 12) + '...'}
                        </td>
                        <td className="py-3 text-slate-200 max-w-xs truncate">{p.reason}</td>
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
                        <td className="py-3 text-right">
                          {p.active && (
                            <button
                              id={`revoke-punishment-${p.id}`}
                              onClick={() => handleRevoke(p.id)}
                              className="px-2.5 py-1 rounded border border-rose-500/40 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 text-[11px] transition cursor-pointer"
                            >
                              Revoke
                            </button>
                          )}
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

      {/* TAB 2: GrimAC Violations */}
      {activeTab === 'grimac' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                id="grim-check-filter"
                type="text"
                value={grimCheckFilter}
                onChange={(e) => setGrimCheckFilter(e.target.value)}
                placeholder="Filter by check name (e.g. Reach, Speed, KillAura, Flight)..."
                className="w-full rounded-xl border border-[#1e1b4b] bg-[#0d1127] px-4 py-2.5 pl-10 text-xs text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none font-mono"
              />
              <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-500 pointer-events-none" />
            </div>
          </div>

          {violationsError && (
            <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
              <div>
                <span className="font-bold">Error loading violations:</span>
                <p className="mt-0.5 text-rose-200/80">{violationsError}</p>
              </div>
            </div>
          )}

          <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
            {violationsLoading ? (
              <div className="py-12 text-center text-xs text-slate-500 font-mono">
                Loading GrimAC flags from core...
              </div>
            ) : violations.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500 font-mono">
                No violations found matching filter.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-[#1e1b4b] text-slate-400">
                      <th className="pb-3 font-semibold">Check</th>
                      <th className="pb-3 font-semibold">Player</th>
                      <th className="pb-3 font-semibold">Server</th>
                      <th className="pb-3 font-semibold">VL</th>
                      <th className="pb-3 font-semibold">Details</th>
                      <th className="pb-3 font-semibold">Timestamp</th>
                      <th className="pb-3 font-semibold text-right">Evidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1e1b4b]/60">
                    {violations.map((v) => (
                      <tr key={v.id} className="hover:bg-[#121638]/50 transition">
                        <td className="py-3 font-bold text-rose-400">{v.check_name}</td>
                        <td
                          onClick={() => navigateToPlayer(v.player_uuid)}
                          className="py-3 text-slate-200 font-bold hover:text-purple-300 hover:underline cursor-pointer"
                        >
                          {v.player_name || v.player_uuid.slice(0, 10)}
                        </td>
                        <td className="py-3 text-slate-400">{v.server_id || 'survival-01'}</td>
                        <td className="py-3">
                          <span className="px-1.5 py-0.5 rounded bg-rose-950/80 text-rose-300 font-bold text-[10px] border border-rose-800/40">
                            VL {v.vl}
                          </span>
                        </td>
                        <td className="py-3 text-slate-400 max-w-xs truncate">{v.verbose}</td>
                        <td className="py-3 text-slate-500 text-[11px]">
                          {v.created_at ? new Date(v.created_at).toLocaleTimeString() : ''}
                        </td>
                        <td className="py-3 text-right">
                          <button
                            id={`view-evidence-${v.id}`}
                            onClick={() => setSelectedViolation(v)}
                            className="inline-flex items-center gap-1 text-[11px] text-purple-400 hover:text-purple-300 underline cursor-pointer"
                          >
                            <span>View Evidence</span>
                            <ExternalLink className="h-3 w-3" />
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

      {/* Modal: Issue Punishment */}
      {isIssueModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-[#1e1b4b] bg-[#0d1127] p-6 shadow-2xl space-y-5 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-[#1e1b4b] pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Ban className="h-4 w-4 text-rose-400" />
                <span>Issue Network Punishment</span>
              </h3>
              <button
                onClick={() => setIsIssueModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreatePunishment} className="space-y-4">
              <div>
                <label className="block text-slate-300 mb-1">Player UUID or Username</label>
                <input
                  type="text"
                  value={newPlayerUuid}
                  onChange={(e) => setNewPlayerUuid(e.target.value)}
                  placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
                  required
                  className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1">Punishment Type</label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
                >
                  <option value="ban">Ban (Network-wide)</option>
                  <option value="mute">Mute (Chat mute)</option>
                  <option value="warn">Warn (Formal Warning)</option>
                  <option value="kick">Kick (Immediate disconnect)</option>
                  <option value="ipban">IP Ban</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 mb-1">Reason</label>
                <textarea
                  value={newReason}
                  onChange={(e) => setNewReason(e.target.value)}
                  placeholder="State rule violation (e.g. GrimAC KillAura Heuristics, Toxicity)..."
                  required
                  rows={3}
                  className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none font-sans"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1">Expiration (Leave blank for Permanent)</label>
                <input
                  type="datetime-local"
                  value={newExpiresAt}
                  onChange={(e) => setNewExpiresAt(e.target.value)}
                  className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsIssueModalOpen(false)}
                  className="flex-1 py-2 rounded-lg border border-[#1e1b4b] bg-[#070914] text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 py-2 rounded-lg border border-rose-500/50 bg-rose-600 hover:bg-rose-500 text-white font-bold disabled:opacity-50"
                >
                  {isSubmitting ? 'Enforcing...' : 'Enforce Punishment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: View Evidence Details */}
      {selectedViolation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-[#1e1b4b] bg-[#0d1127] p-6 shadow-2xl space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-[#1e1b4b] pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-rose-400" />
                <span>GrimAC Heuristic Evidence</span>
              </h3>
              <button
                onClick={() => setSelectedViolation(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-2.5">
              <div className="flex justify-between py-1.5 border-b border-[#1e1b4b]">
                <span className="text-slate-400">Violation ID:</span>
                <span className="text-white">{selectedViolation.id}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-[#1e1b4b]">
                <span className="text-slate-400">Player:</span>
                <span
                  onClick={() => {
                    navigateToPlayer(selectedViolation.player_uuid);
                    setSelectedViolation(null);
                  }}
                  className="text-purple-300 underline cursor-pointer"
                >
                  {selectedViolation.player_name || selectedViolation.player_uuid}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-[#1e1b4b]">
                <span className="text-slate-400">Check:</span>
                <span className="text-rose-400 font-bold">{selectedViolation.check_name}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-[#1e1b4b]">
                <span className="text-slate-400">Violation Level (VL):</span>
                <span className="text-amber-400 font-bold">VL {selectedViolation.vl}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-[#1e1b4b]">
                <span className="text-slate-400">Server:</span>
                <span className="text-white">{selectedViolation.server_id || 'global'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-[#1e1b4b]">
                <span className="text-slate-400">Timestamp:</span>
                <span className="text-slate-300">
                  {selectedViolation.created_at
                    ? new Date(selectedViolation.created_at).toLocaleString()
                    : 'N/A'}
                </span>
              </div>
              <div className="pt-2">
                <div className="text-slate-400 mb-1">Packet Details & Verbose Output:</div>
                <div className="rounded-lg border border-[#1a1f42] bg-[#070914] p-3 text-slate-200 whitespace-pre-wrap">
                  {selectedViolation.verbose || 'No additional verbose payload.'}
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => {
                  navigateToPlayer(selectedViolation.player_uuid);
                  setSelectedViolation(null);
                }}
                className="px-4 py-2 rounded-lg border border-purple-500/40 bg-purple-600 hover:bg-purple-500 text-white font-bold"
              >
                Inspect Player Profile
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
