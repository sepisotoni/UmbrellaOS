/**
 * Discord Server Hub
 * Real data: staff discord IDs, settings (guild ID, bot token set, channels),
 * verification stats, and broadcast. Guild stats require bot→core pipeline (not yet built).
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Bot, Hash, ShieldCheck, UserCheck, RefreshCw, Send,
  CheckCircle2, AlertCircle, Settings2, ExternalLink,
  Users, Copy, Check, Loader2, Radio, Info,
} from 'lucide-react';
import { api, SettingRecord, StaffMemberSchema } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';

// ─── Helpers ──────────────────────────────────────────────────────────────────
function useSettings() {
  const [map, setMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const records: SettingRecord[] = await api.getSettings();
      const m: Record<string, string> = {};
      for (const r of records) m[r.key] = r.value ?? '';
      setMap(m);
    } catch { /* silently */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);
  return { map, loading, reload: load };
}

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handle = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button onClick={handle} className="ml-1 text-slate-500 hover:text-slate-300 transition cursor-pointer">
      {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
    </button>
  );
}

function StatCard({ label, value, sub, icon }: { label: string; value: string | number; sub?: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-[#141d3d] bg-[#060b1c]/80 p-4 flex items-start gap-3">
      <div className="h-8 w-8 rounded-lg bg-indigo-950/60 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-[10px] uppercase font-mono text-slate-500 mb-0.5">{label}</div>
        <div className="text-lg font-bold text-white leading-none">{value}</div>
        {sub && <div className="text-[11px] text-slate-400 mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export const DiscordView: React.FC = () => {
  const { addToast } = useDashboard();
  const { map: settings, loading: settingsLoading, reload: reloadSettings } = useSettings();

  const [staff, setStaff] = useState<StaffMemberSchema[]>([]);
  const [staffLoading, setStaffLoading] = useState(true);
  const [verifiedCount, setVerifiedCount] = useState<number | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);

  // Broadcast state
  const [embedTitle, setEmbedTitle] = useState('');
  const [embedDescription, setEmbedDescription] = useState('');
  const [isBroadcasting, setIsBroadcasting] = useState(false);

  const loadStaff = useCallback(async () => {
    setStaffLoading(true);
    try {
      const data = await api.getStaffMembers();
      setStaff(data);
    } catch { setStaff([]); }
    finally { setStaffLoading(false); }
  }, []);

  const loadVerified = useCallback(async () => {
    try {
      // Count players with a discord_id linked
      const players = await api.getPlayers({ limit: 999 });
      setVerifiedCount(players.filter((p: any) => p.discord_id).length);
    } catch { setVerifiedCount(null); }
  }, []);

  useEffect(() => {
    loadStaff();
    loadVerified();
  }, [loadStaff, loadVerified]);

  const handleRefresh = async () => {
    setIsSyncing(true);
    await Promise.all([reloadSettings(), loadStaff(), loadVerified()]);
    setIsSyncing(false);
    addToast({ type: 'success', title: 'Refreshed', message: 'Discord hub data reloaded.' });
  };

  const handleBroadcast = async () => {
    if (!embedDescription.trim()) {
      addToast({ type: 'error', title: 'Empty message', message: 'Write a message before broadcasting.' });
      return;
    }
    setIsBroadcasting(true);
    try {
      await api.broadcastMessage(`**${embedTitle ? embedTitle + '**\n' : ''}${embedDescription}`, 'Staff');
      addToast({ type: 'success', title: 'Broadcast sent', message: 'Message dispatched to the network.' });
      setEmbedTitle('');
      setEmbedDescription('');
    } catch (err: any) {
      addToast({ type: 'error', title: 'Broadcast failed', message: err.message });
    } finally {
      setIsBroadcasting(false);
    }
  };

  const guildId = settings['discord.guild_id'] || '';
  const botTokenSet = Boolean(settings['discord.bot_token']);
  const staffChannel = settings['discord.staff_channel'] || settings['discord.staff_alerts_channel'] || '';
  const announcementsChannel = settings['discord.announcements_channel'] || '';
  const ipResponse = settings['discord.ip_response'] || '';

  return (
    <div className="space-y-5">
      <DisconnectedBanner />

      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Bot className="h-5 w-5 text-indigo-400" />
            Discord Server Hub
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Bot status, staff roster, verification, and broadcast.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={isSyncing}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#141d3d] bg-[#060b1c] px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white transition cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          {guildId && (
            <a
              href={`https://discord.com/channels/${guildId}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/40 bg-indigo-950/40 px-3 py-1.5 text-xs font-medium text-indigo-300 hover:text-white transition"
            >
              <ExternalLink className="h-3.5 w-3.5" /> Open Server
            </a>
          )}
        </div>
      </div>

      {/* Status cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label="Bot Status"
          value={botTokenSet ? 'Token Set' : 'Not Configured'}
          sub={botTokenSet ? 'Token stored in settings' : 'Add token in Settings → Discord'}
          icon={<Bot className="h-4 w-4" />}
        />
        <StatCard
          label="Guild ID"
          value={guildId ? guildId.slice(0, 10) + '…' : 'Not set'}
          sub={guildId ? undefined : 'Set in Settings → Discord'}
          icon={<Hash className="h-4 w-4" />}
        />
        <StatCard
          label="Staff Members"
          value={staffLoading ? '…' : staff.length}
          sub="Registered in dashboard"
          icon={<ShieldCheck className="h-4 w-4" />}
        />
        <StatCard
          label="Verified Players"
          value={verifiedCount === null ? '…' : verifiedCount}
          sub="Discord-linked accounts"
          icon={<UserCheck className="h-4 w-4" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Staff roster */}
        <div className="rounded-2xl border border-[#141d3d] bg-[#060b1c]/80 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Users className="h-4 w-4 text-indigo-400" /> Staff Roster
            </h2>
            <span className="text-[10px] font-mono text-slate-500">{staff.length} members</span>
          </div>

          {staffLoading ? (
            <div className="flex items-center justify-center py-8 gap-2 text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-xs">Loading staff…</span>
            </div>
          ) : staff.length === 0 ? (
            <p className="text-xs text-slate-500 py-6 text-center">No staff registered yet. Use the Staff tab to appoint members.</p>
          ) : (
            <div className="space-y-2">
              {staff.map((m) => (
                <div key={m.id} className="flex items-center gap-3 rounded-xl border border-[#141d3d] bg-[#070914]/60 px-3 py-2">
                  {m.avatar_url ? (
                    <img src={m.avatar_url} alt={m.username} className="h-7 w-7 rounded-full border border-indigo-500/30" />
                  ) : (
                    <div className="h-7 w-7 rounded-full bg-indigo-950 border border-indigo-500/30 flex items-center justify-center text-[11px] font-bold text-indigo-300">
                      {m.username.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-semibold text-white truncate">@{m.username}</div>
                    <div className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
                      {m.discord_id}
                      <CopyBtn text={m.discord_id} />
                    </div>
                  </div>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border font-bold ${
                    m.role === 'owner'     ? 'bg-amber-950/60 text-amber-300 border-amber-700/40' :
                    m.role === 'admin'     ? 'bg-rose-950/60 text-rose-300 border-rose-700/40' :
                    m.role === 'moderator' ? 'bg-indigo-950/60 text-indigo-300 border-indigo-700/40' :
                                            'bg-slate-900/60 text-slate-400 border-slate-700/40'
                  }`}>
                    {m.role?.toUpperCase() || 'STAFF'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Bot config summary + broadcast */}
        <div className="space-y-4">
          {/* Config summary */}
          <div className="rounded-2xl border border-[#141d3d] bg-[#060b1c]/80 p-5">
            <h2 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
              <Settings2 className="h-4 w-4 text-indigo-400" /> Bot Configuration
            </h2>

            {settingsLoading ? (
              <div className="flex items-center gap-2 text-slate-500 py-4 justify-center">
                <Loader2 className="h-4 w-4 animate-spin" /> <span className="text-xs">Loading…</span>
              </div>
            ) : (
              <div className="space-y-2 text-xs font-mono">
                {[
                  { label: 'Bot Token', value: botTokenSet ? '●●●●●●●●●●●●  (set)' : 'Not set', ok: botTokenSet },
                  { label: 'Guild ID', value: guildId || 'Not set', ok: Boolean(guildId) },
                  { label: 'Staff Channel', value: staffChannel || 'Not set', ok: Boolean(staffChannel) },
                  { label: 'Announcements', value: announcementsChannel || 'Not set', ok: Boolean(announcementsChannel) },
                  { label: '!ip Response', value: ipResponse ? ipResponse.slice(0, 32) + (ipResponse.length > 32 ? '…' : '') : 'Not set', ok: Boolean(ipResponse) },
                ].map(({ label, value, ok }) => (
                  <div key={label} className="flex items-center justify-between gap-3 rounded-lg border border-[#141d3d] bg-[#070914]/40 px-3 py-2">
                    <span className="text-slate-400">{label}</span>
                    <div className="flex items-center gap-1.5 min-w-0 overflow-hidden">
                      {ok
                        ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                        : <AlertCircle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
                      }
                      <span className={`truncate ${ok ? 'text-slate-300' : 'text-slate-500'}`}>{value}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <p className="text-[11px] text-slate-500 flex items-center gap-1 mt-3">
              <Info className="h-3 w-3 shrink-0" />
              Edit these values in <button className="text-indigo-400 hover:underline cursor-pointer" onClick={() => {}}>Settings → Discord</button>
            </p>
          </div>

          {/* Broadcast */}
          <div className="rounded-2xl border border-[#141d3d] bg-[#060b1c]/80 p-5">
            <h2 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
              <Radio className="h-4 w-4 text-indigo-400" /> Network Broadcast
            </h2>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Title (optional)"
                value={embedTitle}
                onChange={(e) => setEmbedTitle(e.target.value)}
                className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none placeholder:text-slate-600"
              />
              <textarea
                placeholder="Broadcast message…"
                value={embedDescription}
                onChange={(e) => setEmbedDescription(e.target.value)}
                rows={3}
                className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none placeholder:text-slate-600 resize-none"
              />
              <button
                onClick={handleBroadcast}
                disabled={isBroadcasting || !embedDescription.trim()}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-indigo-500/50 bg-indigo-600 hover:bg-indigo-500 px-4 py-2.5 text-xs font-bold text-white transition disabled:opacity-50 cursor-pointer"
              >
                {isBroadcasting
                  ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Broadcasting…</>
                  : <><Send className="h-3.5 w-3.5" /> Send Broadcast</>
                }
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Guild stats notice */}
      <div className="rounded-xl border border-amber-500/20 bg-amber-950/10 px-4 py-3 flex items-start gap-2.5 text-xs text-amber-300/80">
        <Info className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
        <span>
          <strong>Guild analytics</strong> (member count, channels, role stats, slash command metrics) require the bot to push data to Core via the Discord→Core bridge. This pipeline is planned for a future phase.
        </span>
      </div>
    </div>
  );
};

export default DiscordView;
