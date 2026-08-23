import React, { useState, useEffect } from 'react';
import { api, VerificationLink, PendingVerification } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  UserCheck,
  Link,
  Unlink,
  RefreshCw,
  AlertCircle,
  Clock,
  Plus,
  X,
  Search,
  ExternalLink,
} from 'lucide-react';

export const VerificationView: React.FC = () => {
  const { addToast, navigateToPlayer } = useDashboard();
  const [links, setLinks] = useState<VerificationLink[]>([]);
  const [pending, setPending] = useState<PendingVerification[]>([]);
  const [activeTab, setActiveTab] = useState<'links' | 'pending'>('links');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Manual link modal
  const [isManualModalOpen, setIsManualModalOpen] = useState<boolean>(false);
  const [discordId, setDiscordId] = useState<string>('');
  const [playerUuid, setPlayerUuid] = useState<string>('');
  const [discordUsername, setDiscordUsername] = useState<string>('');
  const [minecraftUsername, setMinecraftUsername] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const fetchVerificationData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [linksRes, pendingRes] = await Promise.allSettled([
        api.getVerificationLinks(),
        api.getPendingVerifications(),
      ]);

      if (linksRes.status === 'fulfilled') {
        setLinks(linksRes.value || []);
      }
      if (pendingRes.status === 'fulfilled') {
        setPending(pendingRes.value || []);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load verification database');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchVerificationData();
  }, []);

  const handleUnlink = async (dId: string, mcName?: string) => {
    if (!confirm(`Are you sure you want to unlink Discord ID ${dId} from Minecraft?`)) return;

    try {
      await api.unlinkVerification(dId);
      addToast({
        type: 'success',
        title: 'Account Unlinked',
        message: `Unlinked ${mcName || dId}.`,
      });
      fetchVerificationData();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Unlink Failed',
        message: err.message,
      });
    }
  };

  const handleManualLink = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!discordId.trim() || !playerUuid.trim()) return;

    setIsSubmitting(true);
    try {
      await api.manualLinkVerification({
        discord_id: discordId.trim(),
        player_uuid: playerUuid.trim(),
        discord_username: discordUsername.trim() || undefined,
        minecraft_username: minecraftUsername.trim() || undefined,
      });
      addToast({
        type: 'success',
        title: 'Account Linked',
        message: `Successfully bound Discord ${discordId} to Minecraft ${playerUuid.slice(0, 8)}.`,
      });
      setIsManualModalOpen(false);
      setDiscordId('');
      setPlayerUuid('');
      setDiscordUsername('');
      setMinecraftUsername('');
      fetchVerificationData();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Linking Failed',
        message: err.message,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredLinks = links.filter(
    (l) =>
      l.minecraft_username?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.discord_username?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.discord_id.includes(searchQuery) ||
      l.player_uuid.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div id="umbrella-verification-view" className="space-y-6">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Discord & Minecraft Verification</span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-purple-950/80 border border-purple-800/40 text-purple-300">
              {links.length} Verified
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage linked player identities, active link codes, and manual overrides.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            id="manual-link-btn"
            onClick={() => setIsManualModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-purple-500/40 bg-purple-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-purple-500 transition cursor-pointer shadow-[0_0_12px_rgba(168,85,247,0.3)]"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Manual Link</span>
          </button>

          <button
            id="verification-refresh-btn"
            onClick={fetchVerificationData}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-purple-500/40 hover:text-white transition cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#1e1b4b] gap-2 pb-px">
        <button
          onClick={() => setActiveTab('links')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-t-lg transition border-t border-x cursor-pointer ${
            activeTab === 'links'
              ? 'bg-[#0d1127] text-purple-300 border-[#1e1b4b] border-b-transparent -mb-px shadow-sm'
              : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-[#0d1127]/40'
          }`}
        >
          <UserCheck className="h-3.5 w-3.5 text-purple-400" />
          <span>Active Links ({links.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('pending')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-t-lg transition border-t border-x cursor-pointer ${
            activeTab === 'pending'
              ? 'bg-[#0d1127] text-purple-300 border-[#1e1b4b] border-b-transparent -mb-px shadow-sm'
              : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-[#0d1127]/40'
          }`}
        >
          <Clock className="h-3.5 w-3.5 text-amber-400" />
          <span>Pending Verification Codes ({pending.length})</span>
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
          <div>
            <span className="font-bold">Error loading verification data:</span>
            <p className="mt-0.5 text-rose-200/80">{error}</p>
          </div>
        </div>
      )}

      {/* TAB 1: Active Links */}
      {activeTab === 'links' && (
        <div className="space-y-4">
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by Minecraft name, Discord username, or ID..."
              className="w-full rounded-xl border border-[#1e1b4b] bg-[#0d1127] px-4 py-2.5 pl-10 text-xs text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none font-mono"
            />
            <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-500 pointer-events-none" />
          </div>

          <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
            {isLoading ? (
              <div className="py-12 text-center text-xs text-slate-500 font-mono">
                Loading linked records...
              </div>
            ) : filteredLinks.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500 font-mono">
                No linked accounts found.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-[#1e1b4b] text-slate-400">
                      <th className="pb-3 font-semibold">Minecraft Player</th>
                      <th className="pb-3 font-semibold">Minecraft UUID</th>
                      <th className="pb-3 font-semibold">Discord User</th>
                      <th className="pb-3 font-semibold">Discord ID</th>
                      <th className="pb-3 font-semibold">Linked At</th>
                      <th className="pb-3 font-semibold text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1e1b4b]/60">
                    {filteredLinks.map((l) => (
                      <tr key={l.id} className="hover:bg-[#121638]/50 transition">
                        <td
                          onClick={() => navigateToPlayer(l.player_uuid)}
                          className="py-3 font-bold text-white hover:text-purple-300 hover:underline cursor-pointer"
                        >
                          {l.minecraft_username || 'Unknown'}
                        </td>
                        <td className="py-3 text-slate-400 text-[11px]">{l.player_uuid.slice(0, 12)}...</td>
                        <td className="py-3 text-purple-300 font-semibold">{l.discord_username || 'Discord User'}</td>
                        <td className="py-3 text-slate-400">{l.discord_id}</td>
                        <td className="py-3 text-slate-400 text-[11px]">
                          {l.linked_at ? new Date(l.linked_at).toLocaleDateString() : 'N/A'}
                        </td>
                        <td className="py-3 text-right">
                          <button
                            onClick={() => handleUnlink(l.discord_id, l.minecraft_username)}
                            className="px-2.5 py-1 rounded border border-rose-500/40 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 text-[11px] transition cursor-pointer"
                          >
                            Unlink
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

      {/* TAB 2: Pending Links */}
      {activeTab === 'pending' && (
        <div className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl">
          {isLoading ? (
            <div className="py-12 text-center text-xs text-slate-500 font-mono">
              Loading pending verification codes...
            </div>
          ) : pending.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500 font-mono">
              No pending verification codes currently waiting for confirmation.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-[#1e1b4b] text-slate-400">
                    <th className="pb-3 font-semibold">Verification Code</th>
                    <th className="pb-3 font-semibold">Minecraft UUID</th>
                    <th className="pb-3 font-semibold">Discord ID</th>
                    <th className="pb-3 font-semibold">Created</th>
                    <th className="pb-3 font-semibold">Expires At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e1b4b]/60">
                  {pending.map((p) => (
                    <tr key={p.code} className="hover:bg-[#121638]/50 transition">
                      <td className="py-3 font-bold text-amber-400 text-sm">{p.code}</td>
                      <td className="py-3 text-slate-300">{p.player_uuid}</td>
                      <td className="py-3 text-purple-300">{p.discord_id || 'Awaiting Discord Command'}</td>
                      <td className="py-3 text-slate-400 text-[11px]">
                        {p.created_at ? new Date(p.created_at).toLocaleTimeString() : 'N/A'}
                      </td>
                      <td className="py-3 text-slate-400 text-[11px]">
                        {p.expires_at ? new Date(p.expires_at).toLocaleTimeString() : '15m'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Modal: Manual Link */}
      {isManualModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-[#1e1b4b] bg-[#0d1127] p-6 shadow-2xl space-y-5 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-[#1e1b4b] pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Link className="h-4 w-4 text-purple-400" />
                <span>Manual Account Link Override</span>
              </h3>
              <button
                onClick={() => setIsManualModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleManualLink} className="space-y-4">
              <div>
                <label className="block text-slate-300 mb-1">Discord User ID</label>
                <input
                  type="text"
                  value={discordId}
                  onChange={(e) => setDiscordId(e.target.value)}
                  placeholder="e.g. 289123891238912"
                  required
                  className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1">Minecraft Player UUID</label>
                <input
                  type="text"
                  value={playerUuid}
                  onChange={(e) => setPlayerUuid(e.target.value)}
                  placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
                  required
                  className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1">Discord Username (Optional)</label>
                <input
                  type="text"
                  value={discordUsername}
                  onChange={(e) => setDiscordUsername(e.target.value)}
                  placeholder="e.g. notch_fan"
                  className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1">Minecraft Username (Optional)</label>
                <input
                  type="text"
                  value={minecraftUsername}
                  onChange={(e) => setMinecraftUsername(e.target.value)}
                  placeholder="e.g. Steve"
                  className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsManualModalOpen(false)}
                  className="flex-1 py-2 rounded-lg border border-[#1e1b4b] bg-[#070914] text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 py-2 rounded-lg border border-purple-500/50 bg-purple-600 hover:bg-purple-500 text-white font-bold disabled:opacity-50"
                >
                  {isSubmitting ? 'Linking...' : 'Confirm Link'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
