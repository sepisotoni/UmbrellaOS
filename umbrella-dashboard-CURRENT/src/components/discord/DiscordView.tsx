import React, { useState, useEffect, useCallback } from 'react';
import {
  Bot, Hash, RefreshCw, Send, Radio, Copy, Check, Info,
  Users, Server, Activity, Terminal, Shield, Layers, Box, Settings,
  Pencil, X, Loader2
} from 'lucide-react';
import {
  api,
  SettingRecord,
  GuildChannel,
  GuildRole,
  BotGuildConfig,
} from '../../lib/api';
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

  // ── Per-guild data and configuration (from bot push) ──
  const [botGuilds, setBotGuilds] = useState<BotGuildConfig[]>([]);
  const [selectedGuildId, setSelectedGuildId] = useState('');
  const selectedGuild = botGuilds.find(guild => guild.guild_id === selectedGuildId);
  const guildChannels: GuildChannel[] = selectedGuild?.channels ?? [];
  const guildRoles: GuildRole[] = selectedGuild?.roles ?? [];

  // ── Broadcast ──
  const [embedTitle, setEmbedTitle] = useState('');
  const [embedDescription, setEmbedDescription] = useState('');
  const [embedChannel, setEmbedChannel] = useState('');
  const [embedMention, setEmbedMention] = useState('none');
  const [embedColor, setEmbedColor] = useState('bg-indigo-500');
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  // ── Role Discord ID inline editing ──
  const [editingRole, setEditingRole] = useState<string | null>(null);
  const [editRoleValue, setEditRoleValue] = useState('');
  const [savingRole, setSavingRole] = useState<string | null>(null);

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

  const loadBotGuilds = useCallback(async () => {
    try {
      const result = await api.getBotGuilds();
      setBotGuilds(result.guilds);
      setSelectedGuildId(current =>
        result.guilds.some(guild => guild.guild_id === current)
          ? current
          : result.guilds[0]?.guild_id ?? '',
      );
    } catch {
      setBotGuilds([]);
      setSelectedGuildId('');
    }
  }, []);

  useEffect(() => {
    loadVerified();
    loadBotReg();
    loadRoles();
    loadCommands();
  }, [loadVerified, loadBotReg, loadRoles, loadCommands]);

  useEffect(() => { loadBotGuilds(); }, [loadBotGuilds]);

  // ── Set initial channel after settings load ──
  useEffect(() => {
    if (selectedGuild && !selectedGuild.channels.some(channel => channel.id === embedChannel)) {
      setEmbedChannel(selectedGuild.channels[0]?.id ?? '');
    } else if (!selectedGuild && !settingsLoading && !embedChannel) {
      const firstChannel =
        settings['discord.announcements_channel'] ||
        settings['discord.staff_alerts_channel_id'] ||
        settings['discord.staff_alert_channel_id'] ||
        '';
      setEmbedChannel(firstChannel);
    }
  }, [selectedGuild, settingsLoading, settings, embedChannel]);

  const handleRefresh = async () => {
    setIsSyncing(true);
    await Promise.all([
      reloadSettings(),
      loadVerified(),
      loadBotReg(),
      loadRoles(),
      loadCommands(),
      loadBotGuilds(),
    ]);
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
  const guildId = selectedGuild?.guild_id || '';
  const clientId = settings['discord.client_id'] || '';

  const guildConfigKeys: (keyof BotGuildConfig)[] = [
    'staff_alert_channel_id',
    'verified_role_id',
    'owner_role_id',
    'admin_role_id',
    'moderator_role_id',
    'helper_role_id',
  ];
  const configuredCount = guildConfigKeys.filter(key => selectedGuild?.[key]).length;

  // Channel options are scoped to the selected guild.
  const channelOptions: { value: string; label: string; category?: string }[] =
    selectedGuild
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

  // Role mention options are scoped to the selected guild.
  const roleMentionOptions: { value: string; label: string }[] =
    selectedGuild
      ? [
          { value: 'everyone', label: '@everyone' },
          { value: 'here', label: '@here' },
          ...guildRoles
            .filter(role => role.name !== '@everyone' && role.mentionable !== false)
            .map(role => ({ value: role.id, label: `@${role.name}` })),
        ]
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

  type GuildRoleIdKey = 'owner_role_id' | 'admin_role_id' | 'moderator_role_id' |
    'helper_role_id' | 'verified_role_id';

  const roleSettingKey = (roleName: string): GuildRoleIdKey | null => {
    if (roleName === 'owner') return 'owner_role_id';
    if (roleName === 'admin') return 'admin_role_id';
    if (roleName === 'moderator') return 'moderator_role_id';
    if (roleName === 'helper') return 'helper_role_id';
    if (roleName === 'member') return 'verified_role_id';
    return null;
  };

  const roleDiscordId = (roleName: string): string => {
    const key = roleSettingKey(roleName);
    return key ? selectedGuild?.[key] || '—' : '—';
  };

  const startEditingRole = (roleName: string) => {
    const current = roleDiscordId(roleName);
    setEditingRole(roleName);
    setEditRoleValue(current === '—' ? '' : current);
  };

  const cancelEditingRole = () => {
    setEditingRole(null);
    setEditRoleValue('');
  };

  const saveRoleDiscordId = async (roleName: string) => {
    const key = roleSettingKey(roleName);
    if (!key || !selectedGuildId) return;
    setSavingRole(roleName);
    try {
      await api.updateBotGuildConfig(selectedGuildId, {
        [key]: editRoleValue.trim() || null,
      });
      await loadBotGuilds();
      addToast({
        type: 'success',
        title: 'Role mapping saved',
        message: `@${roleName} mapping saved for ${selectedGuild?.name}.`,
      });
      setEditingRole(null);
      setEditRoleValue('');
    } catch (err: any) {
      addToast({ type: 'error', title: 'Save failed', message: err.message || 'Only the owner role can edit settings.' });
    } finally {
      setSavingRole(null);
    }
  };

  const saveStaffAlertChannel = async (channelId: string) => {
    if (!selectedGuildId) return;
    try {
      await api.updateBotGuildConfig(selectedGuildId, {
        staff_alert_channel_id: channelId || null,
      });
      await loadBotGuilds();
      addToast({
        type: 'success',
        title: 'Staff alert channel saved',
        message: `Updated for ${selectedGuild?.name}.`,
      });
    } catch (err: any) {
      addToast({ type: 'error', title: 'Save failed', message: err.message });
    }
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
          Discord Gateway, per-server role mappings, channel discovery, and broadcast tools.
        </p>
        <div className="flex items-center gap-2">
          <select
            value={selectedGuildId}
            onChange={event => setSelectedGuildId(event.target.value)}
            disabled={botGuilds.length === 0}
            aria-label="Select Discord server"
            className="max-w-56 rounded-lg border border-[#141d3d] bg-[#060b1c]/80 px-3 py-2 text-xs text-white disabled:opacity-50"
          >
            {botGuilds.length === 0 ? (
              <option value="">No servers connected</option>
            ) : botGuilds.map(guild => (
              <option key={guild.guild_id} value={guild.guild_id}>{guild.name}</option>
            ))}
          </select>
          <button
            onClick={handleRefresh}
            disabled={isSyncing}
            className="inline-flex items-center gap-2 rounded-lg border border-[#141d3d] bg-[#060b1c]/80 px-3 py-2 text-xs text-slate-400 hover:text-white transition cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
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
            CONNECTED SERVERS
            <div className="h-6 w-6 rounded flex items-center justify-center bg-indigo-950/40 text-indigo-400 border border-indigo-500/20">
              <Users className="h-3.5 w-3.5" />
            </div>
          </div>
          {settingsLoading ? (
            <><Skeleton className="h-5 w-36 mb-2" /><Skeleton className="h-3 w-44" /></>
          ) : selectedGuild ? (
            <>
              <div className="text-sm font-bold text-white leading-none mb-1 truncate">
                {botGuilds.length} {botGuilds.length === 1 ? 'server' : 'servers'} connected
              </div>
              <div className="text-xs text-slate-500 truncate">Selected: {selectedGuild.name}</div>
            </>
          ) : (
            <>
              <div className="text-sm font-bold text-slate-400 leading-none mb-1">No servers connected</div>
              <div className="text-xs text-slate-500">Invite the bot to a Discord server.</div>
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
                {configuredCount} / {guildConfigKeys.length}
              </div>
              <div className="text-xs text-slate-400">selected server settings</div>
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

            <div className="rounded-lg border border-[#141d3d] bg-[#070914] p-4">
              <label className="block text-[10px] font-mono text-slate-500 uppercase mb-2">
                STAFF ALERT CHANNEL
              </label>
              <select
                value={selectedGuild?.staff_alert_channel_id ?? ''}
                onChange={event => saveStaffAlertChannel(event.target.value)}
                disabled={!selectedGuild}
                className="w-full rounded-lg border border-[#1e1b4b] bg-[#02040a] px-3 py-2 text-sm text-white disabled:opacity-50"
              >
                <option value="">Not configured</option>
                {guildChannels.map(channel => (
                  <option key={channel.id} value={channel.id}>#{channel.name}</option>
                ))}
              </select>
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
              <div className="text-[10px] font-mono text-indigo-400 font-bold uppercase">UMBRELLA SENTINEL • TODAY AT {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
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
                        {editingRole === role.name ? (
                          <div className="flex items-center gap-1.5">
                            <input
                              autoFocus
                              value={editRoleValue}
                              onChange={(e) => setEditRoleValue(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') saveRoleDiscordId(role.name);
                                if (e.key === 'Escape') cancelEditingRole();
                              }}
                              placeholder="Discord role ID"
                              className="w-40 rounded border border-indigo-500/40 bg-[#070914] px-2 py-1 text-xs text-white font-mono focus:outline-none focus:border-indigo-400"
                            />
                            <button
                              onClick={() => saveRoleDiscordId(role.name)}
                              disabled={savingRole === role.name}
                              className="p-1 rounded text-emerald-400 hover:bg-emerald-950/40 transition cursor-pointer disabled:opacity-50"
                              title="Save"
                            >
                              {savingRole === role.name ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                            </button>
                            <button
                              onClick={cancelEditingRole}
                              disabled={savingRole === role.name}
                              className="p-1 rounded text-slate-500 hover:bg-slate-800 hover:text-white transition cursor-pointer disabled:opacity-50"
                              title="Cancel"
                            >
                              <X className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        ) : (
                          <div className="group flex items-center gap-2">
                            {discordRoleId === '—' ? (
                              <span className="text-slate-600">Not mapped</span>
                            ) : (
                              <span className="text-slate-300">{discordRoleId}</span>
                            )}
                            {roleSettingKey(role.name) && (
                              <button
                                onClick={() => startEditingRole(role.name)}
                                className="p-1 rounded text-slate-600 hover:text-indigo-300 hover:bg-indigo-950/40 transition cursor-pointer opacity-0 group-hover:opacity-100"
                                title="Edit Discord role ID"
                              >
                                <Pencil className="h-3 w-3" />
                              </button>
                            )}
                          </div>
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
