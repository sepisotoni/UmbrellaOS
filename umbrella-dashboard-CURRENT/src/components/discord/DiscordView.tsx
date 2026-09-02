import React, { useState, useEffect, useCallback } from 'react';
import {
  Bot, Hash, RefreshCw, Send, Radio, Copy, Check, Info,
  Users, Server, Activity, Terminal, Shield, Layers, Box, Settings
} from 'lucide-react';
import { api, SettingRecord, GuildChannel, GuildRole } from '../../lib/api';
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
    <button onClick={handle} className="ml-2 p-1.5 rounded bg-indigo-950/40 text-slate-400 hover:text-white transition cursor-pointer">
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-[#141d3d] rounded ${className}`} />;
}

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ─── Static command list (authoritative — mirrors actual cogs) ─────────────────

const STATIC_COMMANDS = [
  { name: '/server_list',           args: '',                       owner_only: false, description: 'List all registered Minecraft servers' },
  { name: '/server_status',         args: '<server_id>',            owner_only: false, description: 'Get status of a specific server' },
  { name: '/server_stats',          args: '<server_id>',            owner_only: false, description: 'Show TPS, player count, RAM for a server' },
  { name: '/server_start',          args: '<server_id>',            owner_only: true,  description: 'Start a server' },
  { name: '/server_stop',           args: '<server_id>',            owner_only: true,  description: 'Stop a server' },
  { name: '/server_restart',        args: '<server_id>',            owner_only: true,  description: 'Restart a server' },
  { name: '/server_kill',           args: '<server_id>',            owner_only: true,  description: 'Force-kill a server process' },
  { name: '/server_delete',         args: '<server_id>',            owner_only: true,  description: 'Permanently delete a server record' },
  { name: '/player_risk',           args: '<player>',               owner_only: true,  description: 'Get AI risk assessment for a player' },
  { name: '/player_risk_by_discord',args: '<discord_id>',           owner_only: true,  description: 'Risk assessment by Discord ID' },
  { name: '/memory_list',           args: '',                       owner_only: false, description: 'List bot memory entries' },
  { name: '/memory_set',            args: '<key> <value>',          owner_only: true,  description: 'Set a memory key' },
  { name: '/memory_purge',          args: '',                       owner_only: true,  description: 'Clear all memory' },
  { name: '/knowledge_search',      args: '<query>',                owner_only: false, description: 'Search knowledge base' },
  { name: '/report',                args: '<player> <reason>',      owner_only: false, description: 'Report a player' },
  { name: '/crash_risk',            args: '<server_id>',            owner_only: true,  description: 'Predict crash risk from TPS trend' },
  { name: '/ops_query',             args: '<question>',             owner_only: true,  description: 'Run operational intelligence query' },
  { name: '/postmortem',            args: '<server_id>',            owner_only: true,  description: 'Generate incident postmortem' },
  { name: '/archive_search',        args: '<query>',                owner_only: true,  description: 'Search archived chat history' },
  { name: '/investigate',           args: '<player>',               owner_only: true,  description: 'Run full investigation on a player' },
  { name: '/ask',                   args: '<question>',             owner_only: false, description: 'Ask the AI copilot a question' },
];

// ─── Main ─────────────────────────────────────────────────────────────────────

export const DiscordView: React.FC = () => {
  const { addToast } = useDashboard();
  const { map: settings, loading: settingsLoading, reload: reloadSettings } = useSettings();

  // ── Verified player count ──
  const [verifiedCount, setVerifiedCount] = useState<number | null>(null);
  const [verifiedLoading, setVerifiedLoading] = useState(true);

  // ── Bot registration status ──
  const [botReg, setBotReg] = useState<{ registered: boolean; callback_url: string | null; registered_at: string | null } | null>(null);
  const [botRegLoading, setBotRegLoading] = useState(true);

  // ── Roles ──
  const [roles, setRoles] = useState<{ id: string; name: string; description: string; permissions: string[] }[]>([]);
  const [rolesLoading, setRolesLoading] = useState(true);

  // ── Bot commands ──
  const [botCommands, setBotCommands] = useState<{ name: string; description: string; args: string; owner_only: boolean }[]>([]);
  const [commandsLastPushed, setCommandsLastPushed] = useState<string | null>(null);
  const [commandsLoading, setCommandsLoading] = useState(true);

  // ── Guild channels + roles (from bot push) ──
  const [guildChannels, setGuildChannels] = useState<GuildChannel[]>([]);
  const [guildRoles, setGuildRoles] = useState<GuildRole[]>([]);

  // ── Broadcast ──
  const [embedTitle, setEmbedTitle] = useState('');
  const [embedDescription, setEmbedDescription] = useState('');
  const [embedChannel, setEmbedChannel] = useState('');
  const [embedMention, setEmbedMention] = useState('none');
  const [embedColor, setEmbedColor] = useState('bg-indigo-500');
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  const colors = ['bg-indigo-500', 'bg-emerald-500', 'bg-rose-500', 'bg-amber-500', 'bg-sky-500'];

  // ── Loaders ──
  const loadVerified = useCallback(async () => {
    setVerifiedLoading(true);
    try {
      const res = await api.getVerificationCount();
      setVerifiedCount(res.count);
    } catch {
      setVerifiedCount(null);
    } finally {
      setVerifiedLoading(false);
    }
  }, []);

  const loadBotReg = useCallback(async () => {
    setBotRegLoading(true);
    try {
      const reg = await api.getBotRegistration();
      setBotReg(reg);
    } catch {
      setBotReg({ registered: false, callback_url: null, registered_at: null });
    } finally {
      setBotRegLoading(false);
    }
  }, []);

  const loadRoles = useCallback(async () => {
    setRolesLoading(true);
    try {
      const r = await api.getRoles();
      setRoles(r);
    } catch {
      setRoles([]);
    } finally {
      setRolesLoading(false);
    }
  }, []);

  const loadCommands = useCallback(async () => {
    setCommandsLoading(true);
    try {
      const res = await api.getBotCommands();
      if (res.commands && res.commands.length > 0) {
        setBotCommands(res.commands);
        setCommandsLastPushed(res.pushed_at);
      } else {
        // Fall back to static list — bot hasn't pushed yet
        setBotCommands([]);
        setCommandsLastPushed(null);
      }
    } catch {
      setBotCommands([]);
      setCommandsLastPushed(null);
    } finally {
      setCommandsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVerified();
    loadBotReg();
    loadRoles();
    loadCommands();
  }, [loadVerified, loadBotReg, loadRoles, loadCommands]);

  // ── Guild channels + roles from bot push ──
  useEffect(() => {
    api.getGuildChannels()
      .then(r => { if (r.channels.length > 0) setGuildChannels(r.channels); })
      .catch(() => setGuildChannels([]));
    api.getGuildRoles()
      .then(r => { if (r.roles.length > 0) setGuildRoles(r.roles); })
      .catch(() => setGuildRoles([]));
  }, []);

  // ── Set initial channel after settings load ──
  useEffect(() => {
    if (!settingsLoading && !embedChannel) {
      const firstChannel =
        settings['discord.announcements_channel'] ||
        settings['discord.staff_alerts_channel_id'] ||
        settings['discord.staff_alert_channel_id'] ||
        '';
      setEmbedChannel(firstChannel);
    }
  }, [settingsLoading, settings, embedChannel]);

  const handleRefresh = async () => {
    setIsSyncing(true);
    await Promise.all([reloadSettings(), loadVerified(), loadBotReg(), loadRoles(), loadCommands()]);
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
      await api.broadcastMessage(`**${embedTitle ? embedTitle + '**\n' : ''}${embedDescription}`, 'Staff', embedChannel || undefined);
      addToast({ type: 'success', title: 'Broadcast sent', message: 'Message dispatched to the network.' });
      setEmbedTitle('');
      setEmbedDescription('');
    } catch (err: any) {
      addToast({ type: 'error', title: 'Broadcast failed', message: err.message });
    } finally {
      setIsBroadcasting(false);
    }
  };

  // ── Derived data ──
  const guildId = settings['discord.guild_id'] || '';
  const clientId = settings['discord.client_id'] || '';

  // Count non-empty discord.* settings
  const discordSettingKeys = Object.keys(settings).filter(k => k.startsWith('discord.'));
  const configuredCount = discordSettingKeys.filter(k => settings[k] && settings[k].trim() !== '').length;

  // Channel options — prefer live data from bot push; fall back to settings-based IDs
  const channelOptions: { value: string; label: string; category?: string }[] =
    guildChannels.length > 0
      ? guildChannels.map(ch => ({ value: ch.id, label: `#${ch.name}`, category: ch.category ?? undefined }))
      : (() => {
          const opts: { value: string; label: string }[] = [];
          if (settings['discord.announcements_channel']) opts.push({ value: settings['discord.announcements_channel'], label: '#announcements' });
          const staffAlertKey = settings['discord.staff_alerts_channel_id'] || settings['discord.staff_alert_channel_id'] || '';
          if (staffAlertKey) opts.push({ value: staffAlertKey, label: '#staff-alerts' });
          return opts;
        })();

  // Group channels by category for <optgroup> rendering
  const channelsByCategory = channelOptions.reduce((acc, ch) => {
    const cat = (ch as any).category ?? 'Uncategorized';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(ch);
    return acc;
  }, {} as Record<string, typeof channelOptions>);

  // Role mention options — prefer live data from bot push; fall back to hardcoded defaults
  const roleMentionOptions: { value: string; label: string }[] =
    guildRoles.length > 0
      ? guildRoles.map(r => ({ value: r.id, label: `@${r.name}` }))
      : [
          { value: 'everyone', label: '@everyone' },
          { value: 'here', label: '@here' },
          { value: 'Staff', label: '@Staff' },
        ];

  // Role → dashboard clearance mapping
  const clearanceMap: Record<string, string> = {
    owner: 'SUPERADMIN',
    admin: 'ADMIN',
    moderator: 'MODERATOR',
    helper: 'SUPPORT',
    member: 'VIEWER',
  };

  // Role → Discord role ID from settings
  // Fix (2026-09-01): only owner/member were looked up here despite
  // clearanceMap/roleColor above both defining all 5 roles — admin/
  // moderator/helper always showed "Not mapped" regardless of what was
  // configured, because there was no case for them at all (not because the
  // settings were empty). discord.admin_role_id/moderator_role_id/
  // helper_role_id are new settings keys — see settings_service.py's
  // DEFAULT_SETTINGS for the corresponding backend addition.
  const roleDiscordId = (roleName: string): string => {
    if (roleName === 'owner') return settings['discord.owner_role_id'] || '—';
    if (roleName === 'admin') return settings['discord.admin_role_id'] || '—';
    if (roleName === 'moderator') return settings['discord.moderator_role_id'] || '—';
    if (roleName === 'helper') return settings['discord.helper_role_id'] || '—';
    if (roleName === 'member') return settings['discord.verified_role_id'] || '—';
    return '—';
  };

  // Role color dots
  const roleColor: Record<string, string> = {
    owner: 'bg-rose-500',
    admin: 'bg-amber-500',
    moderator: 'bg-purple-500',
    helper: 'bg-blue-500',
    member: 'bg-emerald-500',
  };

  // Commands to display
  const displayCommands = botCommands.length > 0 ? botCommands : STATIC_COMMANDS;
  const commandsSource = botCommands.length > 0 ? 'live' : 'static'; // static = bot hasn't pushed manifest yet

  return (
    <div className="space-y-6 max-w-7xl">
      <DisconnectedBanner />

      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">
          Discord Gateway status, role synchronization, embed broadcaster, and slash command registry.
        </p>
        <button
          onClick={handleRefresh}
          disabled={isSyncing}
          className="inline-flex items-center gap-2 rounded-lg border border-[#141d3d] bg-[#060b1c]/80 px-3 py-2 text-xs text-slate-400 hover:text-white transition cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Top 4 Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">

        {/* Bot Status */}
        <div className="rounded-xl border border-[#141d3d] bg-[#060b1c]/80 p-5">
          <div className="text-[10px] font-mono text-slate-500 font-bold mb-3 uppercase tracking-wider flex items-center justify-between">
            DISCORD BOT STATUS
            <div className="h-6 w-6 rounded flex items-center justify-center bg-indigo-950/40 text-indigo-400 border border-indigo-500/20">
              <Bot className="h-3.5 w-3.5" />
            </div>
          </div>
          {botRegLoading ? (
            <><Skeleton className="h-5 w-32 mb-2" /><Skeleton className="h-3 w-40" /></>
          ) : botReg?.registered ? (
            <>
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-2 rounded-full bg-emerald-500" />
                <div className="text-sm font-bold text-emerald-400 leading-none">REGISTERED</div>
              </div>
              <div className="text-xs text-slate-400 truncate">
                {botReg.registered_at ? `Last seen ${timeAgo(botReg.registered_at)}` : 'Registration time unknown'}
              </div>
              {botReg.callback_url && (
                <div className="text-[10px] font-mono text-slate-600 mt-1 truncate">
                  {new URL(botReg.callback_url).host}
                </div>
              )}
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-2 rounded-full bg-slate-600" />
                <div className="text-sm font-bold text-slate-400 leading-none">NOT REGISTERED</div>
              </div>
              <div className="text-xs text-slate-500">Bot hasn't registered its callback URL</div>
            </>
          )}
        </div>

        {/* Community Guild */}
        <div className="rounded-xl border border-[#141d3d] bg-[#060b1c]/80 p-5">
          <div className="text-[10px] font-mono text-slate-500 font-bold mb-3 uppercase tracking-wider flex items-center justify-between">
            COMMUNITY GUILD
            <div className="h-6 w-6 rounded flex items-center justify-center bg-indigo-950/40 text-indigo-400 border border-indigo-500/20">
              <Users className="h-3.5 w-3.5" />
            </div>
          </div>
          {settingsLoading ? (
            <><Skeleton className="h-5 w-36 mb-2" /><Skeleton className="h-3 w-44" /></>
          ) : guildId ? (
            <>
              <div className="text-xs font-mono text-white leading-none mb-1 truncate">
                <span className="text-slate-500 text-[10px]">Guild ID: </span>{guildId}
              </div>
              <div className="text-xs text-slate-500">Member counts available when bot is online</div>
            </>
          ) : (
            <>
              <div className="text-sm font-bold text-slate-400 leading-none mb-1">Not Configured</div>
              <div className="text-xs text-slate-500">Set discord.guild_id in Settings</div>
            </>
          )}
        </div>

        {/* Minecraft Linked */}
        <div className="rounded-xl border border-[#141d3d] bg-[#060b1c]/80 p-5">
          <div className="text-[10px] font-mono text-slate-500 font-bold mb-3 uppercase tracking-wider flex items-center justify-between">
            MINECRAFT LINKED
            <div className="h-6 w-6 rounded flex items-center justify-center bg-emerald-950/40 text-emerald-400 border border-emerald-500/20">
              <Shield className="h-3.5 w-3.5" />
            </div>
          </div>
          {verifiedLoading ? (
            <><Skeleton className="h-5 w-24 mb-2" /><Skeleton className="h-3 w-28" /></>
          ) : verifiedCount !== null ? (
            <>
              <div className="text-lg font-bold text-emerald-400 leading-none mb-1">
                {verifiedCount.toLocaleString()} Verified
              </div>
              <div className="text-xs text-slate-400">/verify active</div>
            </>
          ) : (
            <>
              <div className="text-lg font-bold text-slate-400 leading-none mb-1">— Verified</div>
              <div className="text-xs text-slate-500">Could not load player data</div>
            </>
          )}
        </div>

        {/* Discord Settings Configured */}
        <div className="rounded-xl border border-[#141d3d] bg-[#060b1c]/80 p-5">
          <div className="text-[10px] font-mono text-slate-500 font-bold mb-3 uppercase tracking-wider flex items-center justify-between">
            SETTINGS CONFIGURED
            <div className="h-6 w-6 rounded flex items-center justify-center bg-purple-950/40 text-purple-400 border border-purple-500/20">
              <Settings className="h-3.5 w-3.5" />
            </div>
          </div>
          {settingsLoading ? (
            <><Skeleton className="h-5 w-20 mb-2" /><Skeleton className="h-3 w-36" /></>
          ) : (
            <>
              <div className="text-lg font-bold text-white leading-none mb-1">
                {configuredCount} / {discordSettingKeys.length}
              </div>
              <div className="text-xs text-slate-400">discord.* settings non-empty</div>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-6">

        {/* Discord Server Identity */}
        <div className="rounded-2xl border border-[#141d3d] bg-[#060b1c]/80 p-6 flex flex-col">
          <h2 className="text-sm font-bold text-white flex items-center gap-2 mb-6">
            <Radio className="h-4 w-4 text-indigo-400" /> DISCORD SERVER IDENTITY
          </h2>

          <div className="space-y-4">
            <div className="rounded-lg border border-[#141d3d] bg-[#070914] p-4 flex items-center justify-between">
              <div>
                <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">DISCORD GUILD ID</div>
                {settingsLoading ? (
                  <Skeleton className="h-4 w-40 mt-1" />
                ) : (
                  <div className="text-sm font-mono text-white">{guildId || 'Not configured'}</div>
                )}
              </div>
              {guildId && <CopyBtn text={guildId} />}
            </div>

            <div className="rounded-lg border border-[#141d3d] bg-[#070914] p-4 flex items-center justify-between">
              <div>
                <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">BOT CLIENT ID</div>
                {settingsLoading ? (
                  <Skeleton className="h-4 w-40 mt-1" />
                ) : (
                  <div className="text-sm font-mono text-white">{clientId || 'Not configured'}</div>
                )}
              </div>
              {clientId && <CopyBtn text={clientId} />}
            </div>

            {botReg?.registered && botReg.callback_url && (
              <div className="rounded-lg border border-[#141d3d] bg-[#070914] p-4 flex items-center justify-between">
                <div className="min-w-0">
                  <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">BOT CALLBACK URL</div>
                  <div className="text-xs font-mono text-slate-300 truncate">{botReg.callback_url}</div>
                </div>
                <CopyBtn text={botReg.callback_url} />
              </div>
            )}

            <div className="rounded-lg border border-indigo-500/20 bg-indigo-950/10 p-4 mt-2">
              <div className="flex items-center gap-2 text-indigo-300 text-xs font-bold mb-2">
                <Bot className="h-4 w-4" /> FastAPI Discord Gateway Integration
              </div>
              <div className="text-xs text-slate-400 leading-relaxed">
                Umbrella Sentinel handles automated verification codes, synced punishment announcements, AI appeal tickets, and live server TPS monitoring.
              </div>
            </div>
          </div>
        </div>

        {/* Direct Discord Embed Broadcaster */}
        <div className="rounded-2xl border border-[#141d3d] bg-[#060b1c]/80 p-6 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Send className="h-4 w-4 text-indigo-400" /> DIRECT DISCORD EMBED BROADCASTER
            </h2>
            <div className="text-[10px] font-mono text-slate-500 uppercase">
              DISPATCH VIA BOT WEBHOOK
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1.5 font-mono">Target Discord Channel</label>
              <select
                value={embedChannel}
                onChange={e => setEmbedChannel(e.target.value)}
                className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] px-3 py-2.5 text-sm text-white focus:border-indigo-500 focus:outline-none appearance-none"
              >
                {channelOptions.length > 0 ? (
                  guildChannels.length > 0
                    ? Object.entries(channelsByCategory).map(([cat, opts]) => (
                        <optgroup key={cat} label={cat}>
                          {opts.map(opt => (
                            <option key={opt.value} value={opt.value}>#{(opt.label as string).replace(/^#/, '')}</option>
                          ))}
                        </optgroup>
                      ))
                    : channelOptions.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))
                ) : (
                  <option value="" disabled>No channels available — bot offline</option>
                )}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1.5 font-mono">Role Mention</label>
              <select
                value={embedMention}
                onChange={e => setEmbedMention(e.target.value)}
                className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] px-3 py-2.5 text-sm text-white focus:border-indigo-500 focus:outline-none appearance-none"
              >
                <option value="none">No Mention (Silent)</option>
                {roleMentionOptions.map(r => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-xs text-slate-400 mb-1.5 font-mono">Embed Header Title</label>
            <input
              type="text"
              value={embedTitle}
              onChange={(e) => setEmbedTitle(e.target.value)}
              className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] px-3 py-2.5 text-sm text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div className="mb-6">
            <label className="block text-xs text-slate-400 mb-1.5 font-mono">Embed Message Description</label>
            <textarea
              value={embedDescription}
              onChange={(e) => setEmbedDescription(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] px-3 py-2.5 text-sm text-white focus:border-indigo-500 focus:outline-none resize-none"
            />
          </div>

          <div className="rounded-lg border border-[#141d3d] bg-[#070914] p-4 mb-5">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[10px] font-mono text-slate-500 uppercase">DISCORD CLIENT EMBED PREVIEW</div>
              <div className="text-[10px] font-mono text-indigo-400 font-bold uppercase">UMBRELLA SENTINEL • TODAY AT 14:00</div>
            </div>
            <div className="flex">
              <div className={`w-1 rounded-l ${embedColor} shrink-0`}></div>
              <div className="bg-[#2b2d31] rounded-r p-4 flex-1">
                <div className="font-bold text-white text-[15px] mb-1">{embedTitle || 'Empty Title'}</div>
                <div className="text-[#dbdee1] text-sm whitespace-pre-wrap">{embedDescription || 'Empty description...'}</div>
                <div className="text-[11px] text-[#80848e] mt-3 font-mono">
                  UmbrellaOS Core Relay • Automated Dispatch
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between mt-auto">
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-400 font-mono">Accent Color:</span>
              <div className="flex gap-2">
                {colors.map(c => (
                  <button
                    key={c}
                    onClick={() => setEmbedColor(c)}
                    className={`w-4 h-4 rounded-full ${c} ${embedColor === c ? 'ring-2 ring-offset-2 ring-offset-[#060b1c] ring-white' : 'opacity-70 hover:opacity-100'}`}
                  />
                ))}
              </div>
            </div>
            <button
              onClick={handleBroadcast}
              disabled={isBroadcasting}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 px-6 py-2.5 text-sm font-bold text-white transition cursor-pointer disabled:opacity-50"
            >
              <Send className="h-4 w-4" /> Dispatch Embed to Discord
            </button>
          </div>
        </div>
      </div>

      {/* Role Sync Mapping */}
      <div className="rounded-2xl border border-[#141d3d] bg-[#060b1c]/80 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="h-4 w-4 text-indigo-400" /> DISCORD ROLE SYNC & DASHBOARD CLEARANCE MAPPING
          </h2>
          <div className="text-[10px] font-mono text-slate-500 uppercase">
            FROM ROLES API
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead>
              <tr className="border-b border-[#141d3d] text-[10px] font-mono text-slate-500 uppercase">
                <th className="pb-3 font-semibold">ROLE NAME</th>
                <th className="pb-3 font-semibold">DASHBOARD CLEARANCE</th>
                <th className="pb-3 font-semibold">DISCORD ROLE ID</th>
                <th className="pb-3 font-semibold text-right">PERMISSIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#141d3d]/50">
              {rolesLoading ? (
                [0,1,2,3,4].map(i => (
                  <tr key={i}>
                    <td className="py-4"><Skeleton className="h-4 w-32" /></td>
                    <td className="py-4"><Skeleton className="h-4 w-24" /></td>
                    <td className="py-4"><Skeleton className="h-4 w-36" /></td>
                    <td className="py-4 text-right"><Skeleton className="h-4 w-20 ml-auto" /></td>
                  </tr>
                ))
              ) : roles.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-500 text-sm">
                    No roles found — check /api/v1/roles
                  </td>
                </tr>
              ) : (
                roles.map((role) => {
                  const discordRoleId = roleDiscordId(role.name);
                  const clearance = clearanceMap[role.name] || 'VIEWER';
                  return (
                    <tr key={role.id} className="hover:bg-[#070914]/50 transition-colors">
                      <td className="py-4 flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full shrink-0 ${roleColor[role.name] || 'bg-slate-500'}`} />
                        <span className="font-bold text-white capitalize">@{role.name}</span>
                      </td>
                      <td className="py-4">
                        <span className="inline-flex px-2 py-0.5 rounded bg-indigo-950/40 border border-indigo-500/20 text-indigo-300 font-mono text-[11px] font-bold">
                          {clearance}
                        </span>
                      </td>
                      <td className="py-4 font-mono text-xs text-slate-400">
                        {discordRoleId === '—' ? (
                          <span className="text-slate-600">Not mapped</span>
                        ) : (
                          <span className="text-slate-300">{discordRoleId}</span>
                        )}
                      </td>
                      <td className="py-4 text-right text-slate-400 font-mono text-xs">
                        {role.permissions.length} permissions
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Slash Commands */}
      <div className="rounded-2xl border border-[#141d3d] bg-[#060b1c]/80 p-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Terminal className="h-4 w-4 text-sky-400" /> REGISTERED DISCORD SLASH COMMANDS
          </h2>
          <div className="text-[10px] font-mono text-slate-500 uppercase">
            {commandsSource === 'live' ? 'LIVE FROM BOT MANIFEST' : 'STATIC — BOT OFFLINE'}
          </div>
        </div>
        <div className="mb-4 text-xs text-slate-500 font-mono">
          {commandsLoading ? (
            <Skeleton className="h-3 w-48" />
          ) : commandsLastPushed ? (
            `Last synced by bot: ${timeAgo(commandsLastPushed)}`
          ) : (
            'No manifest pushed — bot is offline or hasn\'t started yet. Showing static command list.'
          )}
        </div>

        {commandsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[0,1,2,3,4,5].map(i => (
              <div key={i} className="rounded-xl border border-[#141d3d] bg-[#070914] p-4">
                <Skeleton className="h-4 w-32 mb-2" />
                <Skeleton className="h-3 w-full mb-1" />
                <Skeleton className="h-3 w-3/4" />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {displayCommands.map((cmd, i) => (
              <div key={i} className="rounded-xl border border-[#141d3d] bg-[#070914] p-4 flex flex-col justify-between">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <div className="font-bold text-white text-sm">
                      {cmd.name.startsWith('/') ? cmd.name : `/${cmd.name}`}
                      {cmd.args && <span className="text-slate-400 font-mono text-xs ml-1">{cmd.args}</span>}
                    </div>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${cmd.owner_only ? 'bg-rose-950/40 text-rose-300 border-rose-700/40' : 'bg-slate-800 text-slate-300 border-slate-700'}`}>
                      {cmd.owner_only ? 'owner only' : '@everyone'}
                    </span>
                  </div>
                </div>
                <div className="text-xs text-slate-400 leading-relaxed">
                  {cmd.description}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
};

export default DiscordView;
