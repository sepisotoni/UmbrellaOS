import React, { useState, useEffect } from 'react';
import { api, FlaggedAltAccount, AltClusterGroup } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  UserX,
  Users,
  RefreshCw,
  AlertCircle,
  ShieldAlert,
  CheckCircle2,
  ExternalLink,
  Search,
} from 'lucide-react';

export const AltDetectionView: React.FC = () => {
  const { addToast, navigateToPlayer } = useDashboard();
  const [flaggedAlts, setFlaggedAlts] = useState<FlaggedAltAccount[]>([]);
  const [altGroups, setAltGroups] = useState<AltClusterGroup[]>([]);
  const [activeTab, setActiveTab] = useState<'flagged' | 'groups'>('flagged');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAltData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [flaggedRes, groupsRes] = await Promise.allSettled([
        api.getFlaggedAlts(),
        api.getAltGroups(),
      ]);

      if (flaggedRes.status === 'fulfilled') {
        // Core returns FlaggedPlayerSchema {uuid, username, suspicion_score, first_seen}
        // Normalize to FlaggedAltAccount shape the table expects
        const normalized = (flaggedRes.value || []).map((p: any) => ({
          id: p.uuid,
          primary_uuid: p.uuid,
          primary_username: p.username,
          alt_uuid: p.uuid,
          alt_username: p.username,
          method: 'Suspicion Score',
          confidence: Math.min((p.suspicion_score || 0) / 100, 1),
          created_at: p.first_seen,
        }));
        setFlaggedAlts(normalized);
      }
      if (groupsRes.status === 'fulfilled') {
        // Core returns AltGroupSchema {id, created_at, notes, confirmed}
        // Normalize to AltClusterGroup shape
        const normalized = (groupsRes.value || []).map((g: any) => ({
          group_id: String(g.id),
          reason: g.notes || (g.confirmed ? 'Confirmed Cluster' : 'Suspected Cluster'),
          members: (g.members || []).map((m: any) => ({
            uuid: m.player_uuid || m.uuid || '',
            username: m.player_uuid?.slice(0, 8) || 'Unknown',
            is_banned: false,
          })),
        }));
        setAltGroups(normalized);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch alt intelligence data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAltData();
  }, []);

  const handleMarkFalsePositive = async (primaryUuid: string, altUuid?: string) => {
    try {
      await api.markAltFalsePositive(primaryUuid, altUuid);
      addToast({
        type: 'success',
        title: 'Marked False Positive',
        message: 'Alt cluster link unflagged.',
      });
      fetchAltData();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Operation Failed',
        message: err.message,
      });
    }
  };

  const filteredAlts = flaggedAlts.filter(
    (a) =>
      a.primary_username?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.alt_username?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.primary_uuid.includes(searchQuery) ||
      a.alt_uuid.includes(searchQuery)
  );

  return (
    <div id="umbrella-alt-detection-view" className="space-y-6">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Alt Account Intelligence</span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-purple-950/80 border border-purple-800/40 text-purple-300">
              {flaggedAlts.length} Clusters
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Detect ban-evaders, IP correlation clusters, and device fingerprint matches.
          </p>
        </div>

        <button
          id="alts-refresh-btn"
          onClick={fetchAltData}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-purple-500/40 hover:text-white transition cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-[#1e1b4b] gap-2 pb-px">
        <button
          onClick={() => setActiveTab('flagged')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-t-lg transition border-t border-x cursor-pointer ${
            activeTab === 'flagged'
              ? 'bg-[#0d1127] text-purple-300 border-[#1e1b4b] border-b-transparent -mb-px shadow-sm'
              : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-[#0d1127]/40'
          }`}
        >
          <UserX className="h-3.5 w-3.5 text-rose-400" />
          <span>Flagged Alt Pairs ({flaggedAlts.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('groups')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-t-lg transition border-t border-x cursor-pointer ${
            activeTab === 'groups'
              ? 'bg-[#0d1127] text-purple-300 border-[#1e1b4b] border-b-transparent -mb-px shadow-sm'
              : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-[#0d1127]/40'
          }`}
        >
          <Users className="h-3.5 w-3.5 text-purple-400" />
          <span>Cluster Groups ({altGroups.length})</span>
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
          <div>
            <span className="font-bold">Error loading alt intelligence:</span>
            <p className="mt-0.5 text-rose-200/80">{error}</p>
          </div>
        </div>
      )}

      {/* TAB 1: Flagged Pairs */}
      {activeTab === 'flagged' && (
        <div className="space-y-4">
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by player username or UUID..."
              className="w-full rounded-xl border border-[#1e1b4b] bg-[#0d1127] px-4 py-2.5 pl-10 text-xs text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none font-mono"
            />
            <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-500 pointer-events-none" />
          </div>

          <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
            {isLoading ? (
              <div className="py-12 text-center text-xs text-slate-500 font-mono">
                Loading flagged alt correlation records...
              </div>
            ) : filteredAlts.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500 font-mono">
                No active alt flags recorded.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-[#1e1b4b] text-slate-400">
                      <th className="pb-3 font-semibold">Primary Account</th>
                      <th className="pb-3 font-semibold">Suspected Alt</th>
                      <th className="pb-3 font-semibold">Correlation Method</th>
                      <th className="pb-3 font-semibold">Confidence</th>
                      <th className="pb-3 font-semibold">Flagged Date</th>
                      <th className="pb-3 font-semibold text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1e1b4b]/60">
                    {filteredAlts.map((alt) => (
                      <tr key={alt.id} className="hover:bg-[#121638]/50 transition">
                        <td
                          onClick={() => navigateToPlayer(alt.primary_uuid)}
                          className="py-3 font-bold text-white hover:text-purple-300 hover:underline cursor-pointer"
                        >
                          {alt.primary_username || alt.primary_uuid.slice(0, 10)}
                        </td>
                        <td
                          onClick={() => navigateToPlayer(alt.alt_uuid)}
                          className="py-3 font-bold text-rose-300 hover:underline cursor-pointer"
                        >
                          {alt.alt_username || alt.alt_uuid.slice(0, 10)}
                        </td>
                        <td className="py-3 text-slate-300">
                          {alt.method || 'IP Address Match'}
                        </td>
                        <td className="py-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              (alt.confidence || 0) >= 0.8
                                ? 'bg-rose-950/80 text-rose-300 border border-rose-800/40'
                                : 'bg-amber-950/80 text-amber-300 border border-amber-800/40'
                            }`}
                          >
                            {Math.round((alt.confidence || 0.85) * 100)}%
                          </span>
                        </td>
                        <td className="py-3 text-slate-400 text-[11px]">
                          {alt.created_at ? new Date(alt.created_at).toLocaleDateString() : 'Recent'}
                        </td>
                        <td className="py-3 text-right">
                          <button
                            onClick={() => handleMarkFalsePositive(alt.primary_uuid, alt.alt_uuid)}
                            className="px-2.5 py-1 rounded border border-[#1e1b4b] bg-[#070914] text-slate-300 hover:text-white hover:border-purple-500/40 text-[11px] transition cursor-pointer"
                          >
                            False Positive
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

      {/* TAB 2: Cluster Groups */}
      {activeTab === 'groups' && (
        <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
          {isLoading ? (
            <div className="py-12 text-center text-xs text-slate-500 font-mono">
              Loading alt correlation clusters...
            </div>
          ) : altGroups.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500 font-mono">
              No multi-account clusters identified.
            </div>
          ) : (
            <div className="space-y-4">
              {altGroups.map((grp) => (
                <div
                  key={grp.group_id}
                  className="rounded-xl border border-[#1a1f42] bg-[#070914] p-4 space-y-3 font-mono text-xs"
                >
                  <div className="flex items-center justify-between border-b border-[#1e1b4b] pb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-purple-300">Cluster #{grp.group_id.slice(0, 8)}</span>
                      <span className="px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 text-[10px] border border-purple-800/40">
                        {grp.members.length} Associated Accounts
                      </span>
                    </div>
                    <span className="text-slate-500 text-[10px]">
                      Method: {grp.reason || 'IP Subnet Cluster'}
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-2 pt-1">
                    {grp.members.map((m) => (
                      <div
                        key={m.uuid}
                        onClick={() => navigateToPlayer(m.uuid)}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] text-white hover:border-purple-500/40 transition cursor-pointer"
                      >
                        <span className="font-bold">{m.username || m.uuid.slice(0, 8)}</span>
                        {m.is_banned && (
                          <span className="px-1.5 py-0.2 rounded bg-rose-950 text-rose-400 text-[9px] font-bold">
                            BANNED
                          </span>
                        )}
                      </div>
                    ))}
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
