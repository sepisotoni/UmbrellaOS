import React, { useState, useEffect } from 'react';
import { api, PlayerSummary } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { PlayerProfileView } from './PlayerProfileView';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  Users,
  Search,
  RefreshCw,
  AlertCircle,
  ExternalLink,
  ShieldAlert,
  Clock,
  Ban,
} from 'lucide-react';

interface PlayersViewProps {
  onOpenBanModal?: (playerUuid: string) => void;
}

export const PlayersView: React.FC<PlayersViewProps> = ({ onOpenBanModal }) => {
  const { selectedPlayerUuid, setSelectedPlayerUuid } = useDashboard();
  const [players, setPlayers] = useState<PlayerSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPlayers = async (search?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getPlayers({ username: search || undefined, limit: 100 });
      setPlayers(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch player directory');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPlayers(searchQuery);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchPlayers(searchQuery);
  };

  if (selectedPlayerUuid) {
    return (
      <PlayerProfileView
        playerUuid={selectedPlayerUuid}
        onBack={() => setSelectedPlayerUuid(null)}
        onOpenBanModal={onOpenBanModal}
      />
    );
  }

  return (
    <div id="umbrella-players-view" className="space-y-6">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Player Directory</span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-purple-950/80 border border-purple-800/40 text-purple-300">
              {players.length} Players Loaded
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Search, inspect behavior histories, GrimAC violations, and manage punishments.
          </p>
        </div>

        <button
          id="players-refresh-btn"
          onClick={() => fetchPlayers(searchQuery)}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-purple-500/40 hover:text-white transition cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Search Input */}
      <form onSubmit={handleSearchSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <input
            id="players-search-input"
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by Minecraft username or UUID..."
            className="w-full rounded-xl border border-[#1e1b4b] bg-[#0d1127] px-4 py-2.5 pl-10 text-xs text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none font-mono"
          />
          <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-500 pointer-events-none" />
        </div>
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-xl border border-purple-500/40 bg-purple-600 px-4 py-2 text-xs font-bold text-white hover:bg-purple-500 transition cursor-pointer"
        >
          Search
        </button>
      </form>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
          <div>
            <span className="font-bold">Error loading player directory:</span>
            <p className="mt-0.5 text-rose-200/80">{error}</p>
          </div>
        </div>
      )}

      {/* Players List Table */}
      <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
        {isLoading ? (
          <div className="py-12 text-center text-xs text-slate-500 font-mono">
            Loading player records from core...
          </div>
        ) : players.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500 font-mono">
            No players found matching your query.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-[#1e1b4b] text-slate-400">
                  <th className="pb-3 font-semibold">Player</th>
                  <th className="pb-3 font-semibold">UUID</th>
                  <th className="pb-3 font-semibold">Playtime</th>
                  <th className="pb-3 font-semibold">Risk Score</th>
                  <th className="pb-3 font-semibold">Suspicion</th>
                  <th className="pb-3 font-semibold">Last Seen</th>
                  <th className="pb-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e1b4b]/60">
                {players.map((p) => (
                  <tr
                    key={p.uuid}
                    onClick={() => setSelectedPlayerUuid(p.uuid)}
                    className="hover:bg-[#121638]/60 transition cursor-pointer group"
                  >
                    <td className="py-3 font-bold text-white group-hover:text-purple-300 transition">
                      {p.username}
                    </td>
                    <td className="py-3 text-slate-400 text-[11px]">{p.uuid.slice(0, 12)}...</td>
                    <td className="py-3 text-slate-300">
                      {Math.round((p.playtime || 0) / 60)} hrs
                    </td>
                    <td className="py-3">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          (p.risk_score || 0) >= 70
                            ? 'bg-rose-950/80 text-rose-300 border border-rose-800/40'
                            : (p.risk_score || 0) >= 40
                            ? 'bg-amber-950/80 text-amber-300 border border-amber-800/40'
                            : 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/40'
                        }`}
                      >
                        {p.risk_score || 0}
                      </span>
                    </td>
                    <td className="py-3 text-amber-400 font-bold">{p.suspicion_score || 0}</td>
                    <td className="py-3 text-slate-400 text-[11px]">
                      {p.last_seen ? new Date(p.last_seen).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedPlayerUuid(p.uuid);
                        }}
                        className="inline-flex items-center gap-1 text-[11px] text-purple-400 hover:text-purple-300 underline cursor-pointer"
                      >
                        <span>Profile</span>
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
  );
};
