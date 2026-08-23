import React, { useState, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { api } from '../../lib/api';
import {
  CheckCircle2,
  Search,
  UserCheck,
  Link as LinkIcon,
  Unlink,
  ExternalLink,
  Clock,
  Shield,
  Bot,
  AlertCircle,
  Plus
} from 'lucide-react';

interface VerificationLink {
  id: string;
  discordId: string;
  discordTag: string;
  minecraftUsername: string;
  minecraftUuid: string;
  linkedAt: string;
  verifiedBy: 'BOT_CODE' | 'MANUAL_STAFF' | 'OAUTH';
  status: 'VERIFIED' | 'PENDING_CODE' | 'EXPIRED';
}

export const VerificationView: React.FC = () => {
  const { addToast } = useDashboard();

  const [links, setLinks] = useState<VerificationLink[]>([]);
  const [linksLoading, setLinksLoading] = useState(false);
  const [linksError, setLinksError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [manualLinkOpen, setManualLinkOpen] = useState(false);
  const [manualDiscordId, setManualDiscordId] = useState('');
  const [manualMcUsername, setManualMcUsername] = useState('');

  useEffect(() => {
    let cancelled = false;
    const fetchLinks = async () => {
      setLinksLoading(true);
      setLinksError(null);
      try {
        const data = await api.getVerificationLinks();
        if (!cancelled && Array.isArray(data)) {
          setLinks(data.map((raw: any) => ({
            id: raw.id || `lnk-${raw.minecraft_uuid || raw.discord_id}`,
            discordId: raw.discord_id || raw.discordId || '',
            discordTag: raw.discord_tag || raw.discordTag || raw.discord_id || 'Unknown',
            minecraftUsername: raw.minecraft_username || raw.minecraftUsername || 'Unknown',
            minecraftUuid: raw.minecraft_uuid || raw.minecraftUuid || '00000000-0000-0000-0000-000000000000',
            linkedAt: (raw.linked_at || raw.linkedAt || raw.created_at || new Date().toISOString()).replace('T', ' ').substring(0, 19),
            verifiedBy: raw.verified_by || raw.verifiedBy || 'BOT_CODE',
            status: raw.status || 'VERIFIED',
          })));
        }
      } catch (err: any) {
        if (!cancelled) setLinksError(err?.message || 'Failed to load verification links.');
      } finally {
        if (!cancelled) setLinksLoading(false);
      }
    };
    fetchLinks();
    return () => { cancelled = true; };
  }, []);

  const filteredLinks = links.filter(l => {
    return (
      !searchTerm ||
      l.discordTag.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.minecraftUsername.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.discordId.includes(searchTerm)
    );
  });

  const handleUnlink = async (id: string, discordTag: string, mcUsername: string) => {
    setLinks(prev => prev.filter(l => l.id !== id));
    addToast('warning', 'Account Unlinked', `Unlinked ${discordTag} from Minecraft player ${mcUsername}.`);
  };

  const handleCreateManualLink = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualDiscordId.trim() || !manualMcUsername.trim()) return;

    setManualLinkOpen(false);
    const discordId = manualDiscordId.trim();
    const mcUsername = manualMcUsername.trim();
    setManualDiscordId('');
    setManualMcUsername('');

    try {
      await api.manualLinkDiscord(mcUsername, discordId);
      addToast('success', 'Manual Link Created', `Linked Discord ID ${discordId} with Minecraft user ${mcUsername}.`);
      // Refresh list from backend
      const data = await api.getVerificationLinks();
      if (Array.isArray(data)) {
        setLinks(data.map((raw: any) => ({
          id: raw.id || `lnk-${raw.minecraft_uuid || raw.discord_id}`,
          discordId: raw.discord_id || raw.discordId || '',
          discordTag: raw.discord_tag || raw.discordTag || raw.discord_id || 'Unknown',
          minecraftUsername: raw.minecraft_username || raw.minecraftUsername || 'Unknown',
          minecraftUuid: raw.minecraft_uuid || raw.minecraftUuid || '00000000-0000-0000-0000-000000000000',
          linkedAt: (raw.linked_at || raw.linkedAt || raw.created_at || new Date().toISOString()).replace('T', ' ').substring(0, 19),
          verifiedBy: raw.verified_by || raw.verifiedBy || 'MANUAL_STAFF',
          status: raw.status || 'VERIFIED',
        })));
      }
    } catch (err: any) {
      addToast('error', 'Link Failed', err?.message || `Could not link Discord ID ${discordId}.`);
    }
  };

  return (
    <div className="space-y-6 pb-12 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <UserCheck className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white font-display">
                Account Verification & DiscordSRV
              </h1>
              <p className="text-xs text-slate-400">
                DiscordSRV Cloud verification pairs, /link codes, and staff manual account linkages.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setManualLinkOpen(true)}
            className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-cyan-500 transition-colors shadow-sm cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Manual Link</span>
          </button>
        </div>
      </div>

      {/* Filter and Search */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-[#0c1017] p-3 rounded-xl border border-slate-800">
        <span className="text-xs font-mono text-slate-400">
          {links.filter(l => l.status === 'VERIFIED').length} Verified Pairs Active
        </span>

        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search Discord tag, username, or ID..."
            className="w-full rounded-lg border border-slate-800 bg-slate-900/90 pl-9 pr-3 py-1.5 text-xs text-white placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
          />
        </div>
      </div>

      {/* Verification Links Table */}
      <div className="rounded-xl border border-slate-800 bg-[#0d1117] overflow-hidden shadow-sm font-mono text-xs">
        <table className="w-full text-left">
          <thead className="border-b border-slate-800 bg-slate-900/60 text-[11px] text-slate-400 uppercase font-mono">
            <tr>
              <th className="p-3.5">Discord Profile</th>
              <th className="p-3.5">Minecraft Profile</th>
              <th className="p-3.5">Verification Method</th>
              <th className="p-3.5">Status</th>
              <th className="p-3.5">Linked Timestamp</th>
              <th className="p-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {linksLoading ? (
              <tr><td colSpan={5} className="p-8 text-center text-slate-400 font-mono animate-pulse text-xs">Loading verification links...</td></tr>
            ) : linksError ? (
              <tr><td colSpan={5} className="p-6 text-center text-rose-400 font-mono text-xs">{linksError}</td></tr>
            ) : filteredLinks.length === 0 ? (
              <tr><td colSpan={5} className="p-8 text-center text-slate-500 font-mono text-xs">No verified account pairs found.</td></tr>
            ) : null}
            {filteredLinks.map(l => (
              <tr key={l.id} className="hover:bg-slate-900/40 transition-colors">
                <td className="p-3.5">
                  <div className="flex items-center gap-2.5">
                    <div className="h-7 w-7 rounded bg-indigo-950/80 border border-indigo-500/30 text-indigo-400 flex items-center justify-center font-bold text-[11px]">
                      D
                    </div>
                    <div>
                      <div className="font-semibold text-white">{l.discordTag}</div>
                      <div className="text-[10px] text-slate-500">ID: {l.discordId}</div>
                    </div>
                  </div>
                </td>

                <td className="p-3.5">
                  <div className="flex items-center gap-2.5">
                    <img
                      src={`https://mc-heads.net/avatar/${l.minecraftUsername}/24`}
                      alt={l.minecraftUsername}
                      className="h-6 w-6 rounded bg-slate-800 border border-slate-700"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                    <span className="text-cyan-300 font-bold">{l.minecraftUsername}</span>
                  </div>
                </td>

                <td className="p-3.5 text-slate-400">
                  <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px]">
                    {l.verifiedBy}
                  </span>
                </td>

                <td className="p-3.5">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    l.status === 'VERIFIED'
                      ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/30'
                      : 'bg-amber-950/80 text-amber-300 border border-amber-500/30'
                  }`}>
                    {l.status}
                  </span>
                </td>

                <td className="p-3.5 text-slate-500 text-[11px]">{l.linkedAt}</td>

                <td className="p-3.5 text-right">
                  <button
                    onClick={() => handleUnlink(l.id, l.discordTag, l.minecraftUsername)}
                    className="p-1 rounded text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                    title="Unlink Account"
                  >
                    <Unlink className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Manual Link Modal */}
      {manualLinkOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 font-sans animate-in fade-in duration-150">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#090b10] p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white font-display">Manual Account Link</h3>
              <button onClick={() => setManualLinkOpen(false)} className="text-slate-400 hover:text-white cursor-pointer">
                <AlertCircle className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateManualLink} className="space-y-4 font-mono text-xs">
              <div className="space-y-1">
                <label className="text-slate-400 font-semibold font-sans">Discord User ID (Snowflake)</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 8921049281928391"
                  value={manualDiscordId}
                  onChange={(e) => setManualDiscordId(e.target.value)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-400 font-semibold font-sans">Minecraft Username</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. UmbrellaLead_MC"
                  value={manualMcUsername}
                  onChange={(e) => setManualMcUsername(e.target.value)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 font-sans">
                <button
                  type="button"
                  onClick={() => setManualLinkOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:text-white cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold cursor-pointer shadow-sm"
                >
                  Confirm Link
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
