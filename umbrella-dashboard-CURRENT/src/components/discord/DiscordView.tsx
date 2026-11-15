import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Clock3,
  Hash,
  Megaphone,
  RefreshCw,
  Send,
  Server,
  ShieldCheck,
  Terminal,
  Users,
} from 'lucide-react';
import {
  api,
  BotCommand,
  BotGuildConfig,
  BotRegistrationStatus,
  GuildChannel,
} from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';

type GuildRoleField = 'owner_role_id' | 'verified_role_id';
type GuildConfigPatch = Partial<
  Pick<
    BotGuildConfig,
    'staff_alert_channel_id' | 'owner_role_id' | 'verified_role_id'
  >
>;

const roleMappings: {
  field: GuildRoleField;
  title: string;
  description: string;
}[] = [
  {
    field: 'owner_role_id',
    title: 'Owner command access',
    description: 'Role required for owner-restricted slash commands.',
  },
  {
    field: 'verified_role_id',
    title: 'Verified member',
    description: 'Role granted after a player links their Minecraft account.',
  },
];

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unexpected API error';
}

function timeAgo(value: string | null | undefined): string {
  if (!value) return 'Not recorded';
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return 'Unknown';

  const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function fullDate(value: string | null | undefined): string {
  if (!value) return 'Not recorded';
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp)
    ? new Date(timestamp).toLocaleString()
    : 'Unknown';
}

const DEFAULT_BROADCAST_TITLE = '📢 Staff Broadcast';
const DEFAULT_BROADCAST_COLOR = '#9B59B6';
const PRESET_BROADCAST_EMOJIS = ['📢', '✅', '⚠️', '🚨', '🎉', '📅', '🛠️', '🎮'];

function isHttpsUrl(value: string): boolean {
  if (!value.trim()) return true;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password;
  } catch {
    return false;
  }
}

function Card({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl border border-[#1b2445] bg-[#090e20]/90 p-5 shadow-[0_12px_40px_rgba(0,0,0,0.16)] ${className}`}
    >
      {children}
    </section>
  );
}

function CardTitle({
  icon,
  children,
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-white">
      <span className="text-indigo-300">{icon}</span>
      {children}
    </h2>
  );
}

function Metric({
  label,
  value,
  detail,
  icon,
  color = 'text-indigo-300',
}: {
  label: string;
  value: string;
  detail: string;
  icon: React.ReactNode;
  color?: string;
}) {
  return (
    <Card>
      <div className="mb-4 flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400">{label}</span>
        <span className={color}>{icon}</span>
      </div>
      <div className="text-2xl font-semibold tracking-tight text-white">{value}</div>
      <div className="mt-1 truncate text-xs text-slate-500">{detail}</div>
    </Card>
  );
}

function EmptyState({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <div className="rounded-xl border border-dashed border-[#293252] bg-[#070b18] px-5 py-8 text-center">
      <p className="text-sm font-medium text-slate-300">{title}</p>
      <p className="mx-auto mt-1 max-w-lg text-xs leading-relaxed text-slate-500">
        {detail}
      </p>
    </div>
  );
}

export const DiscordView: React.FC = () => {
  const { addToast } = useDashboard();
  const [guilds, setGuilds] = useState<BotGuildConfig[]>([]);
  const [selectedGuildId, setSelectedGuildId] = useState('');
  const [commands, setCommands] = useState<BotCommand[]>([]);
  const [commandsPushedAt, setCommandsPushedAt] = useState<string | null>(null);
  const [registration, setRegistration] = useState<BotRegistrationStatus | null>(
    null,
  );
  const [verifiedCount, setVerifiedCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadErrors, setLoadErrors] = useState<string[]>([]);
  const [savingField, setSavingField] = useState<string | null>(null);
  const [targetChannelId, setTargetChannelId] = useState('');
  const [broadcastText, setBroadcastText] = useState('');
  const [broadcastTitle, setBroadcastTitle] = useState(DEFAULT_BROADCAST_TITLE);
  const [broadcastColor, setBroadcastColor] = useState(DEFAULT_BROADCAST_COLOR);
  const [broadcastIconUrl, setBroadcastIconUrl] = useState('');
  const [broadcastImageUrl, setBroadcastImageUrl] = useState('');
  const [emojiTarget, setEmojiTarget] = useState<'title' | 'message'>('message');
  const [sending, setSending] = useState(false);

  const selectedGuild = guilds.find(
    guild => guild.guild_id === selectedGuildId,
  );
  const channels = selectedGuild?.channels ?? [];
  const roles = selectedGuild?.roles ?? [];

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    const errors: string[] = [];
    const [
      guildsResult,
      commandsResult,
      registrationResult,
      verificationResult,
    ] = await Promise.allSettled([
      api.getBotGuilds(),
      api.getBotCommands(),
      api.getBotRegistration(),
      api.getVerificationCount(),
    ]);

    if (guildsResult.status === 'fulfilled') {
      const nextGuilds = guildsResult.value.guilds;
      setGuilds(nextGuilds);
      setSelectedGuildId(current =>
        nextGuilds.some(guild => guild.guild_id === current)
          ? current
          : nextGuilds[0]?.guild_id ?? '',
      );
    } else {
      errors.push(`Server list: ${errorMessage(guildsResult.reason)}`);
    }

    if (commandsResult.status === 'fulfilled') {
      setCommands(commandsResult.value.commands);
      setCommandsPushedAt(commandsResult.value.pushed_at);
    } else {
      errors.push(`Command manifest: ${errorMessage(commandsResult.reason)}`);
    }

    if (registrationResult.status === 'fulfilled') {
      setRegistration(registrationResult.value);
    } else {
      errors.push(`Webhook registration: ${errorMessage(registrationResult.reason)}`);
    }

    if (verificationResult.status === 'fulfilled') {
      setVerifiedCount(verificationResult.value.count);
    } else {
      errors.push(`Verified account count: ${errorMessage(verificationResult.reason)}`);
    }

    setLoadErrors(errors);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    setTargetChannelId(current =>
      channels.some(channel => channel.id === current)
        ? current
        : channels[0]?.id ?? '',
    );
  }, [selectedGuildId, channels]);

  const channelById = useMemo(
    () => new Map(channels.map(channel => [channel.id, channel])),
    [channels],
  );

  const configuredItems = selectedGuild
    ? [
        selectedGuild.staff_alert_channel_id,
        selectedGuild.owner_role_id,
        selectedGuild.verified_role_id,
      ].filter(Boolean).length
    : 0;

  const updateGuildConfig = async (
    field: string,
    patch: GuildConfigPatch,
  ) => {
    if (!selectedGuild) return;
    setSavingField(field);
    try {
      const updated = await api.updateBotGuildConfig(
        selectedGuild.guild_id,
        patch,
      );
      setGuilds(current =>
        current.map(guild =>
          guild.guild_id === updated.guild_id ? updated : guild,
        ),
      );
      addToast({
        type: 'success',
        title: 'Server settings saved',
        message: `Updated ${selectedGuild.name}.`,
      });
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Could not save setting',
        message: errorMessage(error),
      });
    } finally {
      setSavingField(null);
    }
  };

  const handleBroadcast = async () => {
    const message = broadcastText.trim();
    if (!selectedGuild || !targetChannelId) {
      addToast({
        type: 'error',
        title: 'Choose a destination',
        message: 'Select a server and text channel before sending.',
      });
      return;
    }
    if (!message) {
      addToast({
        type: 'error',
        title: 'Message is empty',
        message: 'Write a message before sending it to Discord.',
      });
      return;
    }
    if (!isHttpsUrl(broadcastIconUrl) || !isHttpsUrl(broadcastImageUrl)) {
      addToast({
        type: 'error',
        title: 'Image URL must use HTTPS',
        message: 'Use a valid HTTPS URL for the thumbnail icon and banner image.',
      });
      return;
    }

    setSending(true);
    try {
      const result = await api.broadcastMessage(
        message,
        'Staff',
        targetChannelId,
        {
          embedTitle: broadcastTitle.trim() || DEFAULT_BROADCAST_TITLE,
          embedColor: Number.parseInt(broadcastColor.slice(1), 16),
          iconUrl: broadcastIconUrl.trim() || undefined,
          imageUrl: broadcastImageUrl.trim() || undefined,
        },
      );
      if (!result.forwarded || !result.targets.includes('discord')) {
        addToast({
          type: 'warning',
          title: 'Message was not sent',
          message:
            'Core accepted the request, but Discord forwarding is disabled or unavailable.',
        });
        return;
      }

      if (result.delivery_status === 'queued') {
        addToast({
          type: 'warning',
          title: 'Broadcast queued',
          message:
            'Core will retry delivery when the bot polls. Undelivered broadcasts expire after 24 hours.',
        });
      } else {
        addToast({
          type: 'success',
          title: 'Broadcast sent',
          message: `Delivered to #${channelById.get(targetChannelId)?.name ?? 'the selected channel'} in ${selectedGuild.name}.`,
        });
      }
      setBroadcastText('');
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Broadcast failed',
        message: errorMessage(error),
      });
    } finally {
      setSending(false);
    }
  };

  const configuredCommands = commands.filter(command => command.owner_only).length;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <DisconnectedBanner />

      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-indigo-300">
            <Bot className="h-4 w-4" />
            Integrations / Discord
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-white">
            Discord bot
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            Review the bot's synced servers and commands, configure server roles,
            and send a dashboard announcement.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor="discord-server-select">
            Select Discord server
          </label>
          <select
            id="discord-server-select"
            value={selectedGuildId}
            onChange={event => setSelectedGuildId(event.target.value)}
            disabled={guilds.length === 0 || loading}
            className="min-w-48 rounded-lg border border-[#293252] bg-[#0a1023] px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-400 disabled:opacity-50"
          >
            {guilds.length === 0 ? (
              <option value="">No servers connected</option>
            ) : (
              guilds.map(guild => (
                <option key={guild.guild_id} value={guild.guild_id}>
                  {guild.name}
                </option>
              ))
            )}
          </select>
          <button
            type="button"
            onClick={() => void loadData(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-lg border border-[#293252] bg-[#0a1023] px-3 py-2.5 text-sm text-slate-300 transition hover:border-indigo-400/60 hover:text-white disabled:opacity-50"
          >
            <RefreshCw
              className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`}
            />
            Refresh
          </button>
        </div>
      </header>

      {loadErrors.length > 0 && (
        <div
          role="alert"
          className="rounded-xl border border-amber-500/25 bg-amber-950/20 p-4"
        >
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-amber-200">
            <AlertCircle className="h-4 w-4" />
            Some Discord data could not be loaded
          </div>
          <ul className="space-y-1 text-xs text-amber-100/70">
            {loadErrors.map(error => <li key={error}>{error}</li>)}
          </ul>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Server records"
          value={loading ? '-' : guilds.length.toLocaleString()}
          detail="Per-server configurations in Core"
          icon={<Server className="h-4 w-4" />}
        />
        <Metric
          label="Slash commands"
          value={loading ? '-' : commands.length.toLocaleString()}
          detail={commandsPushedAt ? `Manifest synced ${timeAgo(commandsPushedAt)}` : 'No bot manifest received'}
          icon={<Terminal className="h-4 w-4" />}
          color="text-sky-300"
        />
        <Metric
          label="Verified accounts"
          value={loading || verifiedCount === null ? '-' : verifiedCount.toLocaleString()}
          detail="Linked Minecraft accounts"
          icon={<ShieldCheck className="h-4 w-4" />}
          color="text-emerald-300"
        />
        <Metric
          label="Server setup"
          value={selectedGuild ? `${configuredItems}/3` : '-'}
          detail={selectedGuild ? `Configured for ${selectedGuild.name}` : 'Select a connected server'}
          icon={<CheckCircle2 className="h-4 w-4" />}
          color="text-violet-300"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardTitle icon={<Server className="h-4 w-4" />}>
            Server snapshots
          </CardTitle>
          {loading && guilds.length === 0 ? (
            <div className="space-y-2">
              {[0, 1].map(item => (
                <div key={item} className="h-24 animate-pulse rounded-xl bg-[#111a31]" />
              ))}
            </div>
          ) : guilds.length > 0 ? (
            <div className="space-y-2">
              {guilds.map(guild => {
                const isSelected = guild.guild_id === selectedGuildId;
                const configured = [
                  guild.staff_alert_channel_id,
                  guild.owner_role_id,
                  guild.verified_role_id,
                ].filter(Boolean).length;
                return (
                  <button
                    key={guild.guild_id}
                    type="button"
                    onClick={() => setSelectedGuildId(guild.guild_id)}
                    aria-pressed={isSelected}
                    className={`w-full rounded-xl border p-4 text-left transition ${
                      isSelected
                        ? 'border-indigo-400/50 bg-indigo-500/[0.08]'
                        : 'border-[#202a49] bg-[#070b18] hover:border-[#39466d]'
                    }`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-white">
                          {guild.name}
                        </div>
                        <div className="mt-1 break-all font-mono text-[11px] text-slate-500">
                          {guild.guild_id}
                        </div>
                      </div>
                      <span className={`rounded-full px-2 py-1 text-[10px] ${
                        isSelected
                          ? 'bg-indigo-400/15 text-indigo-200'
                          : 'bg-[#111a31] text-slate-400'
                      }`}>
                        {isSelected ? 'Selected' : 'Select server'}
                      </span>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-400">
                      <span className="inline-flex items-center gap-1.5">
                        <Hash className="h-3.5 w-3.5 text-indigo-300" />
                        {guild.channels.length} text channels
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <Users className="h-3.5 w-3.5 text-indigo-300" />
                        {guild.roles.length} roles
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <ShieldCheck className="h-3.5 w-3.5 text-indigo-300" />
                        {configured}/3 settings
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <Clock3 className="h-3.5 w-3.5 text-indigo-300" />
                        Synced {timeAgo(guild.pushed_at)}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <EmptyState
              title={loadErrors.length ? 'Server data is unavailable' : 'No Discord servers synced'}
              detail="When the bot starts and joins a server, its server snapshot will appear here. Bot gateway presence is not reported by this configuration endpoint."
            />
          )}
        </Card>

        <Card>
          <CardTitle icon={<Bot className="h-4 w-4" />}>
            Webhook registration
          </CardTitle>
          {registration ? (
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <span className={`mt-0.5 h-2.5 w-2.5 rounded-full ${registration.registered ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                <div>
                  <div className="text-sm font-medium text-white">
                    {registration.registered ? 'Callback registered' : 'No callback registered'}
                  </div>
                  <div className="mt-1 text-xs text-slate-400">
                    {registration.registered
                      ? `Last registered ${timeAgo(registration.registered_at)}`
                      : 'Push events need a registered callback URL.'}
                  </div>
                </div>
              </div>
              {registration.callback_url && (
                <div className="rounded-xl border border-[#202a49] bg-[#070b18] p-3">
                  <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                    Callback endpoint
                  </div>
                  <a
                    href={registration.callback_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 block break-all text-xs text-indigo-300 hover:text-indigo-200"
                  >
                    {registration.callback_url}
                  </a>
                </div>
              )}
              <p className="text-xs leading-relaxed text-slate-500">
                Registration is not a live gateway heartbeat. The Core API
                currently reports the callback registration time only.
              </p>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              {loading ? 'Loading registration...' : 'Registration data unavailable.'}
            </p>
          )}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardTitle icon={<ShieldCheck className="h-4 w-4" />}>
            Server configuration
          </CardTitle>
          {!selectedGuild ? (
            <EmptyState
              title="Select a connected server"
              detail="Per-server settings become available after the bot syncs at least one Discord server."
            />
          ) : (
            <div className="space-y-4">
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-slate-300">
                  Staff alert channel
                </span>
                <select
                  value={selectedGuild.staff_alert_channel_id ?? ''}
                  onChange={event =>
                    void updateGuildConfig('staff_alert_channel_id', {
                      staff_alert_channel_id: event.target.value || null,
                    })
                  }
                  disabled={savingField === 'staff_alert_channel_id'}
                  className="w-full rounded-lg border border-[#293252] bg-[#070b18] px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-400 disabled:opacity-60"
                >
                  <option value="">Not configured</option>
                  {channels.map(channel => (
                    <option key={channel.id} value={channel.id}>
                      #{channel.name}
                    </option>
                  ))}
                </select>
                <span className="mt-1 block text-[11px] text-slate-500">
                  Destination for moderation and investigation escalations.
                </span>
              </label>

              {roleMappings.map(mapping => (
                <label key={mapping.field} className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-300">
                    {mapping.title}
                  </span>
                  <select
                    value={selectedGuild[mapping.field] ?? ''}
                    onChange={event => {
                      const value = event.target.value || null;
                      const patch = mapping.field === 'owner_role_id'
                        ? { owner_role_id: value }
                        : { verified_role_id: value };
                      void updateGuildConfig(mapping.field, patch);
                    }}
                    disabled={savingField === mapping.field}
                    className="w-full rounded-lg border border-[#293252] bg-[#070b18] px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-400 disabled:opacity-60"
                  >
                    <option value="">Not configured</option>
                    {roles.filter(role => !role.is_default).map(role => (
                      <option key={role.id} value={role.id}>
                        {role.name}
                      </option>
                    ))}
                  </select>
                  <span className="mt-1 block text-[11px] text-slate-500">
                    {mapping.description}
                  </span>
                </label>
              ))}
              {channels.length === 0 && (
                <p className="rounded-lg border border-amber-500/20 bg-amber-950/20 p-3 text-xs text-amber-200">
                  No text channels were discovered for this server. Refresh the
                  bot's Discord connection before choosing a staff alert channel.
                </p>
              )}
              {roles.length === 0 && (
                <p className="rounded-lg border border-amber-500/20 bg-amber-950/20 p-3 text-xs text-amber-200">
                  No Discord roles were discovered for this server. Refresh the
                  bot's Discord connection before configuring role mappings.
                </p>
              )}
            </div>
          )}
        </Card>

        <Card>
          <div className="mb-4 flex items-start justify-between gap-3">
            <CardTitle icon={<Terminal className="h-4 w-4" />}>
              Slash command manifest
            </CardTitle>
            <span className="shrink-0 text-[11px] text-slate-500">
              {commandsPushedAt ? `Synced ${timeAgo(commandsPushedAt)}` : 'No sync recorded'}
            </span>
          </div>
          {commands.length === 0 ? (
            <EmptyState
              title="No command manifest"
              detail="The dashboard will show commands reported by the running bot. It does not substitute a hard-coded list."
            />
          ) : (
            <>
              <div className="mb-3 flex items-center gap-2 text-xs text-slate-500">
                {commands.length} commands
                <span className="text-slate-700">/</span>
                {configuredCommands} owner-restricted
              </div>
              <div className="max-h-[28rem] space-y-2 overflow-y-auto pr-1">
                {commands.map(command => (
                  <div
                    key={command.name}
                    className="rounded-xl border border-[#202a49] bg-[#070b18] p-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <code className="text-sm font-semibold text-sky-200">
                        /{command.name}
                        {command.args && (
                          <span className="ml-2 text-xs font-normal text-slate-500">
                            {command.args}
                          </span>
                        )}
                      </code>
                      {command.owner_only && (
                        <span className="rounded-full border border-rose-400/20 bg-rose-400/10 px-2 py-0.5 text-[10px] text-rose-200">
                          Owner restricted
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-slate-400">
                      {command.description || 'No description supplied.'}
                    </p>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>
      </div>

      <Card>
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle icon={<Megaphone className="h-4 w-4" />}>
              Dashboard announcement
            </CardTitle>
            <p className="-mt-2 text-xs text-slate-500">
              Customize the announcement embed and send it through Core to the
              selected server's text channel.
            </p>
          </div>
          {selectedGuild && (
            <span className="rounded-full border border-[#293252] bg-[#070b18] px-2.5 py-1 text-xs text-slate-400">
              {selectedGuild.name}
            </span>
          )}
        </div>

        {!selectedGuild ? (
          <EmptyState
            title="No destination available"
            detail="Connect the bot to a Discord server and refresh this page to send an announcement."
          />
        ) : channels.length === 0 ? (
          <EmptyState
            title="No text channels discovered"
            detail="The bot needs access to a text channel before announcements can be sent."
          />
        ) : (
          <div className="grid gap-5 lg:grid-cols-[1fr_0.8fr]">
            <div className="space-y-4">
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-slate-300">
                  Destination channel
                </span>
                <select
                  value={targetChannelId}
                  onChange={event => setTargetChannelId(event.target.value)}
                  className="w-full rounded-lg border border-[#293252] bg-[#070b18] px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-400"
                >
                  {channels.map((channel: GuildChannel) => (
                    <option key={channel.id} value={channel.id}>
                      #{channel.name}
                      {channel.category ? ` - ${channel.category}` : ''}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-slate-300">
                  Message
                </span>
                <textarea
                  value={broadcastText}
                  onChange={event => setBroadcastText(event.target.value)}
                  maxLength={4000}
                  rows={5}
                  placeholder="Write an announcement for your Discord server..."
                  className="w-full resize-y rounded-lg border border-[#293252] bg-[#070b18] px-3 py-2.5 text-sm leading-relaxed text-white outline-none placeholder:text-slate-600 focus:border-indigo-400"
                />
                <span className="mt-1 block text-right text-[11px] text-slate-500">
                  {broadcastText.length}/4000
                </span>
              </label>
              <div className="space-y-3 rounded-xl border border-[#293252] bg-[#090e20] p-3">
                <p className="text-xs font-semibold text-slate-200">Embed appearance</p>
                <label className="block">
                  <span className="mb-1.5 block text-xs text-slate-400">Title</span>
                  <input
                    value={broadcastTitle}
                    onChange={event => setBroadcastTitle(event.target.value)}
                    maxLength={256}
                    placeholder="📢 Staff Broadcast"
                    className="w-full rounded-lg border border-[#293252] bg-[#070b18] px-3 py-2 text-sm text-white outline-none placeholder:text-slate-600 focus:border-indigo-400"
                  />
                </label>
                <div className="space-y-2">
                  <label className="flex items-center justify-between gap-3">
                    <span className="text-xs text-slate-400">Preset emoji</span>
                    <select
                      value={emojiTarget}
                      onChange={event =>
                        setEmojiTarget(event.target.value as 'title' | 'message')
                      }
                      className="rounded-md border border-[#293252] bg-[#070b18] px-2 py-1 text-xs text-slate-200"
                      aria-label="Insert emoji into"
                    >
                      <option value="message">Message</option>
                      <option value="title">Title</option>
                    </select>
                  </label>
                  <div className="flex flex-wrap gap-1.5" role="group" aria-label="Preset emojis">
                    {PRESET_BROADCAST_EMOJIS.map(emoji => (
                      <button
                        key={emoji}
                        type="button"
                        aria-label={`Insert ${emoji} emoji`}
                        title={`Insert ${emoji}`}
                        onClick={() => {
                          const update = emojiTarget === 'title'
                            ? setBroadcastTitle
                            : setBroadcastText;
                          update(current => current ? `${current} ${emoji}` : emoji);
                        }}
                        className="rounded-md border border-[#293252] bg-[#070b18] px-2 py-1 text-base transition hover:border-indigo-400 hover:bg-indigo-500/10"
                      >
                        {emoji}
                      </button>
                    ))}
                  </div>
                </div>
                <label className="flex items-center justify-between gap-3">
                  <span className="text-xs text-slate-400">Accent color</span>
                  <span className="flex items-center gap-2">
                    <input
                      type="color"
                      value={broadcastColor}
                      onChange={event => setBroadcastColor(event.target.value)}
                      aria-label="Embed accent color"
                      className="h-8 w-10 cursor-pointer rounded border border-[#293252] bg-transparent p-0.5"
                    />
                    <span className="font-mono text-xs text-slate-300">{broadcastColor}</span>
                  </span>
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs text-slate-400">Thumbnail icon URL (HTTPS)</span>
                  <input
                    type="url"
                    value={broadcastIconUrl}
                    onChange={event => setBroadcastIconUrl(event.target.value)}
                    placeholder="https://example.com/icon.png"
                    className="w-full rounded-lg border border-[#293252] bg-[#070b18] px-3 py-2 text-xs text-white outline-none placeholder:text-slate-600 focus:border-indigo-400"
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs text-slate-400">Banner image URL (HTTPS)</span>
                  <input
                    type="url"
                    value={broadcastImageUrl}
                    onChange={event => setBroadcastImageUrl(event.target.value)}
                    placeholder="https://example.com/banner.png"
                    className="w-full rounded-lg border border-[#293252] bg-[#070b18] px-3 py-2 text-xs text-white outline-none placeholder:text-slate-600 focus:border-indigo-400"
                  />
                </label>
              </div>
              <button
                type="button"
                onClick={() => void handleBroadcast()}
                disabled={sending || !broadcastText.trim()}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
                {sending ? 'Sending...' : 'Send announcement'}
              </button>
            </div>

            <div className="rounded-xl border border-[#293252] bg-[#070b18] p-4">
              <div className="mb-3 flex items-center justify-between text-xs">
                <span className="font-medium text-slate-300">Message preview</span>
                <span className="text-slate-500">Discord embed</span>
              </div>
              <div className="flex min-h-32 overflow-hidden rounded-lg bg-[#2b2d31]">
                <div className="w-1 shrink-0" style={{ backgroundColor: broadcastColor }} />
                <div className="min-w-0 flex-1 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="mb-2 text-sm font-semibold text-white">
                      {broadcastTitle.trim() || DEFAULT_BROADCAST_TITLE}
                    </div>
                    {broadcastIconUrl.trim() && isHttpsUrl(broadcastIconUrl) && (
                      <img
                        src={broadcastIconUrl}
                        alt="Embed thumbnail preview"
                        referrerPolicy="no-referrer"
                        className="h-12 w-12 shrink-0 rounded-md object-cover"
                      />
                    )}
                  </div>
                  <p className="whitespace-pre-wrap break-words text-sm text-[#dbdee1]">
                    {broadcastText.trim() || 'Your announcement will appear here.'}
                  </p>
                  {broadcastImageUrl.trim() && isHttpsUrl(broadcastImageUrl) && (
                    <img
                      src={broadcastImageUrl}
                      alt="Embed banner preview"
                      referrerPolicy="no-referrer"
                      className="mt-3 max-h-48 w-full rounded-md object-cover"
                    />
                  )}
                  <p className="mt-4 text-[11px] text-[#949ba4]">
                    Sent by Staff via UmbrellaOS Dashboard
                  </p>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-1.5 text-[11px] text-slate-500">
                <Hash className="h-3 w-3" />
                #{channelById.get(targetChannelId)?.name ?? 'Select a channel'}
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

export default DiscordView;
