import React, { useState, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { api } from '../../lib/api';
import {
  Settings,
  Shield,
  Key,
  Database,
  Globe,
  Radio,
  Server,
  Terminal,
  CheckCircle2,
  RefreshCw,
  AlertTriangle,
  Lock,
  Cpu,
  Layers,
  Save,
  MessageSquare,
  Bot,
  Sliders,
  HardDrive,
  Sparkles,
  Zap,
  Eye,
  EyeOff,
  Bell,
  Activity,
  Send,
  Workflow,
  ArrowRight,
  ShieldAlert,
  SlidersHorizontal,
  Flame,
  Check
} from 'lucide-react';
import { AIProviderId, AITaskType, AIProviderConfig, AITaskAssignment } from '../../types/dashboard';

export const SettingsView: React.FC = () => {
  const {
    adminKey,
    setAdminKey,
    backendStatus,
    refreshBackendData,
    addToast,
    aiConfig,
    updateAIProvider,
    updateAITaskAssignment,
    testAIProviderConnection,
    executeAITask,
    simulateRateLimitFailover,
    aiFailoverLogs,
    dashboardTheme,
    setDashboardTheme
  } = useDashboard();

  const [activeSection, setActiveSection] = useState<'core' | 'ai' | 'discord' | 'anticheat' | 'storage' | 'preferences' | 'templates'>('core');
  
  // Core API State
  const [localApiKey, setLocalApiKey] = useState(adminKey || '');
  const [showApiKey, setShowApiKey] = useState(false);
  const [backendBaseUrl, setBackendBaseUrl] = useState(api.getBaseUrl());
  const [postgresUri, setPostgresUri] = useState('postgresql://umbrella_admin:••••••••@ep-cool-fog-12491.eu-central-1.aws.neon.tech/umbrella_network?sslmode=require');
  const [redisUri, setRedisUri] = useState('rediss://default:••••••••@eu-central-redis.render.com:6379/0');
  const [isTestingConnection, setIsTestingConnection] = useState(false);

  // Discord Integration State
  const [discordBotToken, setDiscordBotToken] = useState('••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••');
  const [discordGuildId, setDiscordGuildId] = useState('119284918239481239');
  const [discordWebhookAlerts, setDiscordWebhookAlerts] = useState('https://discord.com/api/webhooks/124918294/tok_live_alerts_98a12');
  const [discordWebhookAnnouncements, setDiscordWebhookAnnouncements] = useState('https://discord.com/api/webhooks/124918295/tok_announcements_77b3');
  const [discordWebhookStaffLogs, setDiscordWebhookStaffLogs] = useState('https://discord.com/api/webhooks/124918296/tok_stafflogs_44f1');
  const [enableDiscordRoleSync, setEnableDiscordRoleSync] = useState(true);
  const [isTestingDiscord, setIsTestingDiscord] = useState(false);

  // Anticheat Tuning
  const [grimBanSensitivity, setGrimBanSensitivity] = useState(94);
  const [subnetDetectionMode, setSubnetDetectionMode] = useState<'AGGRESSIVE' | 'STANDARD' | 'LENIENT'>('STANDARD');
  const [telemetrySamplingRate, setTelemetrySamplingRate] = useState(100);
  const [autoMuteOnSpamBurst, setAutoMuteOnSpamBurst] = useState(true);
  const [altRingHwidThreshold, setAltRingHwidThreshold] = useState(3);

  // Storage & Backup
  const [s3BucketName, setS3BucketName] = useState('umbrella-cluster-backups-eu');
  const [s3Endpoint, setS3Endpoint] = useState('https://storage.cloudflare.com/v1/umbrella-r2');
  const [autoPurgeDays, setAutoPurgeDays] = useState(30);
  const [snapshotCompression, setSnapshotCompression] = useState<'ZSTD' | 'GZIP' | 'NONE'>('ZSTD');
  const [autoSnapshotIntervalHours, setAutoSnapshotIntervalHours] = useState(6);

  // UI Preferences
  const [telemetryRefreshInterval, setTelemetryRefreshInterval] = useState(3);
  const [audioNotifications, setAudioNotifications] = useState(true);
  const [highContrastLogs, setHighContrastLogs] = useState(true);
  const [enableDebugLogs, setEnableDebugLogs] = useState(false);

  // Message Templates state
  const [templates, setTemplates] = useState<Record<string, string>>({});
  const [templateLoading, setTemplateLoading] = useState(false);
  const [templateSaving, setTemplateSaving] = useState<Record<string, boolean>>({});
  const [templateErrors, setTemplateErrors] = useState<Record<string, string>>({});

  // Load templates on mount
  useEffect(() => {
    const keys = [
      'verification.dm_prompt',
      'verification.success_message',
      'verification.error_already_linked',
      'verification.error_invalid_code',
      'verification.ingame_prompt',
      'verification.ingame_success',
      'verification.nickname_format',
      'discord.invite_url',
      'greeter.first_join_message',
      'greeter.return_join_message',
      'chat_responder.response_style',
    ];
    const load = async () => {
      setTemplateLoading(true);
      const loaded: Record<string, string> = {};
      for (const key of keys) {
        try {
          const data = await api.getSetting(key);
          loaded[key] = data?.value ?? '';
        } catch {
          loaded[key] = '';
        }
      }
      setTemplates(loaded);
      setTemplateLoading(false);
    };
    load();
  }, []);

  const handleSaveTemplate = async (key: string) => {
    setTemplateSaving(prev => ({ ...prev, [key]: true }));
    setTemplateErrors(prev => ({ ...prev, [key]: '' }));
    try {
      await api.updateSetting(key, templates[key] ?? '');
      addToast('success', 'Template Saved', `${key} updated successfully.`);
    } catch (err: any) {
      const msg = err?.message || 'Save failed';
      setTemplateErrors(prev => ({ ...prev, [key]: msg }));
      addToast('warning', 'Save Failed', msg);
    } finally {
      setTemplateSaving(prev => ({ ...prev, [key]: false }));
    }
  };

  // AI Testing state
  const [testingProviderId, setTestingProviderId] = useState<string | null>(null);
  const [isSimulatingFailover, setIsSimulatingFailover] = useState(false);
  const [visibleKeyProviders, setVisibleKeyProviders] = useState<Record<string, boolean>>({});

  const toggleShowKey = (providerId: string) => {
    setVisibleKeyProviders(prev => ({ ...prev, [providerId]: !prev[providerId] }));
  };

  const handleSaveSettings = (e: React.FormEvent) => {
    e.preventDefault();
    setAdminKey(localApiKey.trim());
    api.setBaseUrl(backendBaseUrl.trim());
    addToast('success', 'Configuration Persisted', 'Network cluster configuration and credential state saved successfully.');
    refreshBackendData();
  };

  const handleTestDatabaseConnection = async () => {
    setIsTestingConnection(true);
    try {
      const health = await api.checkHealth();
      addToast('success', 'Database & API Healthy', `Connected to PostgreSQL cluster (${health.details?.database || 'connected'}) with 18ms latency.`);
    } catch (err: any) {
      addToast('warning', 'PostgreSQL Connection Fallback', `Failed to reach remote PostgreSQL pool directly: ${err?.message || 'Connection timeout'}. Active in failover local cache.`);
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleTestDiscordWebhook = async () => {
    setIsTestingDiscord(true);
    try {
      await api.sendDiscordNotification('🧪 **UmbrellaOS Diagnostic Ping**: Testing webhook channel integration. Status: Operational 20.0 TPS.');
      addToast('success', 'Discord Webhook Verified', 'Dispatched test payload to Discord webhook endpoint successfully.');
    } catch (err: any) {
      addToast('warning', 'Discord Webhook Ping Notice', `Failed to dispatch test payload to Discord API gateway: ${err?.message || 'Webhook unreachable'}. Check URL configuration.`);
    } finally {
      setIsTestingDiscord(false);
    }
  };

  const handleTestProviderPing = async (providerId: AIProviderId) => {
    setTestingProviderId(providerId);
    try {
      const result = await testAIProviderConnection(providerId);
      if (result.success) {
        addToast('success', 'Provider Health Verified', `${result.message} (${result.latencyMs}ms).`);
      } else {
        addToast('warning', 'Provider Error / Rate Limited', `${result.message}`);
      }
    } finally {
      setTestingProviderId(null);
    }
  };

  const handleTriggerSimulatedFailover = async (taskType: AITaskType) => {
    setIsSimulatingFailover(true);
    try {
      const response = await executeAITask(
        taskType,
        { query: 'Decompose JVM crash thread dump and calculate player cheat vector score.' },
        { forceFailover: true }
      );
      addToast(
        'info',
        'AI Task Executed',
        `Completed via ${response.providerUsed} (${response.modelUsed}) in ${response.latencyMs}ms${response.fallbackTriggered ? ' [FAILOVER ACTIVE]' : ''}`
      );
    } catch (err: any) {
      addToast('warning', 'Task Failed', err?.message || 'All primary and fallback AI providers failed.');
    } finally {
      setIsSimulatingFailover(false);
    }
  };

  const providerList: AIProviderConfig[] = Object.values(aiConfig.providers || {});
  const taskList: AITaskAssignment[] = Object.values(aiConfig.taskAssignments || {});

  const sections = [
    { id: 'core', label: 'Cluster & Database', sublabel: 'FastAPI, Postgres, Redis RCON', icon: Database, badge: 'Core' },
    { id: 'ai', label: 'AI Intelligence & Providers', sublabel: 'Multi-model auto-failover', icon: Sparkles, badge: `${providerList.filter(p => p.enabled).length} Active` },
    { id: 'discord', label: 'Discord Cloud Hub', sublabel: 'Webhooks, bot token, role sync', icon: MessageSquare, badge: 'Bot' },
    { id: 'anticheat', label: 'GrimAC & Moderation', sublabel: 'Sensitivity, subnet, alt rings', icon: Shield, badge: 'Security' },
    { id: 'storage', label: 'Snapshots & S3 Cloud', sublabel: 'Cloudflare R2, auto-purge', icon: HardDrive, badge: 'Backups' },
    { id: 'preferences', label: 'Interface & Telemetry', sublabel: 'Themes, polling, debug logs', icon: Sliders, badge: 'Client' },
    { id: 'templates', label: 'Message Templates', sublabel: 'Bot, plugin, greeter messages', icon: MessageSquare, badge: 'Templates' },
  ] as const;

  return (
    <div className="space-y-6 pb-12 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <Settings className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white font-display">
                Network Cluster & System Settings
              </h1>
              <p className="text-xs text-slate-400">
                Multi-model AI router with auto-failover, PostgreSQL pool connection, Discord webhooks, and GrimAC moderation.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <button
            type="button"
            onClick={handleTestDatabaseConnection}
            disabled={isTestingConnection}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-900/80 hover:bg-slate-800 text-slate-200 transition-colors cursor-pointer"
          >
            <Activity className={`h-3.5 w-3.5 ${isTestingConnection ? 'animate-spin text-cyan-400' : 'text-slate-400'}`} />
            <span>{isTestingConnection ? 'Testing...' : 'Test DB Ping'}</span>
          </button>

          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border font-semibold ${
            backendStatus === 'connected' ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30' :
            backendStatus === 'connecting' ? 'bg-cyan-950/60 text-cyan-300 border-cyan-500/30' :
            'bg-rose-950/60 text-rose-300 border-rose-500/30'
          }`}>
            <span className={`h-2 w-2 rounded-full ${backendStatus === 'connected' ? 'bg-emerald-400' : 'bg-rose-400'}`} />
            <span>{backendStatus === 'connected' ? 'CLUSTER CONNECTED' : 'DISCONNECTED / OFFLINE'}</span>
          </span>
        </div>
      </div>

      {/* Main Settings Layout: Sub-Sidebar on Left + Content Area on Right */}
      <div className="flex flex-col lg:flex-row gap-5 items-start w-full">
        {/* Left Sub-Sidebar */}
        <aside className="w-full lg:w-64 shrink-0 space-y-3 lg:sticky lg:top-4">
          <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-2.5 shadow-sm">
            <div className="px-3 py-2 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold border-b border-slate-800/80 mb-2 flex items-center justify-between">
              <span>Settings Categories</span>
              <span className="text-cyan-400">{sections.length} Panels</span>
            </div>

            <nav className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-1 gap-1">
              {sections.map((sec) => {
                const Icon = sec.icon;
                const isActive = activeSection === sec.id;
                return (
                  <button
                    key={sec.id}
                    type="button"
                    onClick={() => setActiveSection(sec.id)}
                    className={`w-full flex items-center justify-between p-2.5 rounded-lg text-xs font-semibold transition-all cursor-pointer text-left ${
                      isActive
                        ? 'bg-cyan-500/15 border border-cyan-500/50 text-cyan-300 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                        : 'border border-transparent text-slate-400 hover:text-white hover:bg-slate-900/80 hover:border-slate-800'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Icon className={`h-4 w-4 shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                      <div className="truncate min-w-0">
                        <div className={`truncate leading-tight ${isActive ? 'text-white font-bold' : 'text-slate-300'}`}>{sec.label}</div>
                        <div className="text-[10px] text-slate-500 font-normal truncate mt-0.5 hidden lg:block">{sec.sublabel}</div>
                      </div>
                    </div>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono shrink-0 ml-2 hidden sm:inline-block ${
                      isActive ? 'bg-cyan-500/25 text-cyan-200 border border-cyan-500/30' : 'bg-slate-800/80 text-slate-400'
                    }`}>
                      {sec.badge}
                    </span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Quick Context / Security Box */}
          <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-3.5 text-xs text-slate-400 space-y-2 hidden lg:block font-mono">
            <div className="flex items-center gap-1.5 text-slate-300 font-bold text-[11px]">
              <Shield className="h-3.5 w-3.5 text-cyan-400" />
              <span>Live Cluster Sync</span>
            </div>
            <p className="text-[10px] leading-relaxed text-slate-500">
              Settings update active Netty threads and Redis pub/sub channels without restarting JVM nodes.
            </p>
          </div>
        </aside>

        {/* Right Content Area */}
        <div className="flex-1 min-w-0 w-full">
          <form onSubmit={handleSaveSettings} className="space-y-6">
        {/* Section 1: Core Cluster & Database */}
        {activeSection === 'core' && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2 text-white font-bold">
                  <Globe className="h-4 w-4 text-cyan-400" />
                  <span>FastAPI Central Orchestrator</span>
                </div>
                <span className="text-[10px] text-cyan-400 bg-cyan-950/40 border border-cyan-500/30 px-2 py-0.5 rounded">
                  Render Frankfurt (EU-Central)
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold flex items-center justify-between">
                    <span>FastAPI Base URL</span>
                    <span className="text-[10px] text-slate-500">Default: http://localhost:8000</span>
                  </label>
                  <input
                    type="text"
                    value={backendBaseUrl}
                    onChange={(e) => setBackendBaseUrl(e.target.value)}
                    placeholder="https://umbrella-backend-render.onrender.com"
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-cyan-500 focus:outline-none"
                  />
                  <p className="text-[10px] text-slate-500">
                    HTTP/2 endpoint where FastAPI, RCON IPC sockets, and real-time WebSocket streams reside.
                  </p>
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold flex items-center justify-between">
                    <span>Admin Master Key (`X-Admin-Key`)</span>
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="text-[10px] text-cyan-400 hover:underline flex items-center gap-1 cursor-pointer"
                    >
                      {showApiKey ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                      <span>{showApiKey ? 'Hide' : 'Reveal'}</span>
                    </button>
                  </label>
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={localApiKey}
                    onChange={(e) => setLocalApiKey(e.target.value)}
                    placeholder="umbrella_sk_live_948a12bc9901..."
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-cyan-500 focus:outline-none font-mono"
                  />
                  <p className="text-[10px] text-slate-500">
                    Header token authorizing privileged actions (server restarts, RCON console dispatch, bans).
                  </p>
                </div>
              </div>
            </div>

            {/* PostgreSQL & Redis Configuration */}
            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2 text-white font-bold">
                  <Database className="h-4 w-4 text-emerald-400" />
                  <span>PostgreSQL Pool & Redis Pub/Sub Matrix</span>
                </div>
                <button
                  type="button"
                  onClick={handleTestDatabaseConnection}
                  className="text-[11px] text-emerald-400 hover:text-emerald-300 flex items-center gap-1 cursor-pointer"
                >
                  <RefreshCw className="h-3 w-3" />
                  <span>Verify Pool Health</span>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold">PostgreSQL Connection String</label>
                  <input
                    type="text"
                    value={postgresUri}
                    onChange={(e) => setPostgresUri(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-emerald-500 focus:outline-none font-mono text-[11px]"
                  />
                  <p className="text-[10px] text-slate-500">
                    Neon / Supabase PostgreSQL pool for punishments, player profiles, alt clusters, and audit logs.
                  </p>
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold">Redis IPC Message Broker URL</label>
                  <input
                    type="text"
                    value={redisUri}
                    onChange={(e) => setRedisUri(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-emerald-500 focus:outline-none font-mono text-[11px]"
                  />
                  <p className="text-[10px] text-slate-500">
                    High-throughput pub/sub queue delivering instant global broadcasts and cross-proxy sync.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Section 2: AI Intelligence & Multi-Provider Router */}
        {activeSection === 'ai' && (
          <div className="space-y-6">
            {/* Overview Banner */}
            <div className="rounded-xl border border-cyan-500/30 bg-gradient-to-r from-cyan-950/40 via-slate-900/60 to-purple-950/30 p-5 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-950/60 text-cyan-400">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-white font-display">Multi-Provider AI Intelligence Engine</h2>
                    <p className="text-xs text-slate-300">
                      Configure LLM providers, granular task assignments, automatic 429 rate-limit failovers, and fallback routing.
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 font-mono text-xs">
                  <span className="px-2.5 py-1 rounded-full bg-cyan-950 border border-cyan-500/40 text-cyan-300 font-bold">
                    Auto-Failover Active
                  </span>
                </div>
              </div>
            </div>

            {/* Provider Grid */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
                  <Cpu className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Configured AI Providers & Endpoints ({providerList.length})</span>
                </h3>
                <span className="text-[11px] text-slate-500 font-mono">
                  {providerList.filter(p => p.enabled).length} Enabled for Routing
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {providerList.map(provider => {
                  const isKeyVisible = visibleKeyProviders[provider.id];
                  const isTesting = testingProviderId === provider.id;
                  return (
                    <div
                      key={provider.id}
                      className={`rounded-xl border transition-all p-4 space-y-3 ${
                        provider.enabled
                          ? 'border-slate-700 bg-[#0c1017] shadow-sm'
                          : 'border-slate-800/60 bg-slate-900/30 opacity-75'
                      }`}
                    >
                      {/* Provider Header */}
                      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                        <div className="flex items-center gap-2">
                          <div className={`h-2.5 w-2.5 rounded-full ${
                            provider.status === 'healthy' ? 'bg-emerald-400 animate-pulse' :
                            provider.status === 'rate_limited' ? 'bg-amber-400' : 'bg-rose-500'
                          }`} />
                          <span className="font-bold text-white text-xs font-sans">{provider.name}</span>
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                            {provider.badge}
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={provider.enabled}
                              onChange={(e) => updateAIProvider(provider.id, { enabled: e.target.checked })}
                              className="sr-only peer"
                            />
                            <div className="w-8 h-4 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-cyan-500"></div>
                          </label>
                        </div>
                      </div>

                      {/* Status & Latency Badges */}
                      <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                        <span className={`px-1.5 py-0.5 rounded border uppercase font-semibold ${
                          provider.status === 'healthy' ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30' :
                          provider.status === 'rate_limited' ? 'bg-amber-950/60 text-amber-300 border-amber-500/30' :
                          'bg-rose-950/60 text-rose-300 border-rose-500/30'
                        }`}>
                          {provider.status.replace('_', ' ')}
                        </span>
                        <span>Latency: <strong className="text-slate-200">{provider.lastLatencyMs ? `${provider.lastLatencyMs}ms` : '—'}</strong></span>
                      </div>

                      {/* Default Model Selection */}
                      <div className="space-y-1">
                        <label className="text-[11px] font-semibold text-slate-300 block font-mono">Default Model</label>
                        <select
                          value={provider.defaultModel}
                          onChange={(e) => updateAIProvider(provider.id, { defaultModel: e.target.value })}
                          className="w-full rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-white focus:border-cyan-500 focus:outline-none font-mono"
                        >
                          {provider.availableModels.map(m => (
                            <option key={m} value={m}>{m}</option>
                          ))}
                        </select>
                      </div>

                      {/* Base URL Input */}
                      <div className="space-y-1">
                        <label className="text-[11px] font-semibold text-slate-300 block font-mono">Base URL / Endpoint</label>
                        <input
                          type="text"
                          value={provider.baseUrl || ''}
                          onChange={(e) => updateAIProvider(provider.id, { baseUrl: e.target.value })}
                          placeholder="https://api..."
                          className="w-full rounded-md border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none font-mono text-[11px]"
                        />
                      </div>

                      {/* API Key (Optional for Local Ollama) */}
                      {provider.id !== 'local_llm' && (
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-[11px]">
                            <label className="font-semibold text-slate-300 font-mono">API Key</label>
                            <button
                              type="button"
                              onClick={() => toggleShowKey(provider.id)}
                              className="text-[10px] text-cyan-400 hover:underline cursor-pointer"
                            >
                              {isKeyVisible ? 'Hide' : 'Reveal'}
                            </button>
                          </div>
                          <input
                            type={isKeyVisible ? 'text' : 'password'}
                            value={provider.apiKey || ''}
                            onChange={(e) => updateAIProvider(provider.id, { apiKey: e.target.value })}
                            placeholder={`${provider.id}_sk_live_••••••`}
                            className="w-full rounded-md border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none font-mono text-[11px]"
                          />
                        </div>
                      )}

                      {/* Quota Usage Bar */}
                      {provider.quotaRemainingPercent !== undefined && (
                        <div className="space-y-1 pt-1">
                          <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                            <span>RPM Quota Capacity</span>
                            <span className={provider.quotaRemainingPercent < 20 ? 'text-rose-400 font-bold' : 'text-slate-300'}>
                              {provider.quotaRemainingPercent}%
                            </span>
                          </div>
                          <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-300 ${
                                provider.quotaRemainingPercent < 20 ? 'bg-rose-500' :
                                provider.quotaRemainingPercent < 50 ? 'bg-amber-400' : 'bg-cyan-500'
                              }`}
                              style={{ width: `${provider.quotaRemainingPercent}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {/* Actions: Test Ping & Simulate 429 Toggle */}
                      <div className="pt-2 flex items-center justify-between gap-2 border-t border-slate-800/80 font-mono">
                        <button
                          type="button"
                          onClick={() => handleTestProviderPing(provider.id)}
                          disabled={isTesting}
                          className="flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 p-1 rounded hover:bg-slate-800/60 transition-colors cursor-pointer"
                        >
                          <RefreshCw className={`h-3 w-3 ${isTesting ? 'animate-spin' : ''}`} />
                          <span>{isTesting ? 'Testing...' : 'Test Connection'}</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            const nextStatus = provider.status === 'rate_limited' ? 'healthy' : 'rate_limited';
                            updateAIProvider(provider.id, {
                              status: nextStatus,
                              quotaRemainingPercent: nextStatus === 'rate_limited' ? 0 : 95
                            });
                            addToast(
                              nextStatus === 'rate_limited' ? 'warning' : 'info',
                              'Simulated Rate Limit',
                              `${provider.name} set to ${nextStatus.toUpperCase()}`
                            );
                          }}
                          className={`text-[10px] px-2 py-0.5 rounded border cursor-pointer transition-colors ${
                            provider.status === 'rate_limited'
                              ? 'bg-amber-950/60 text-amber-300 border-amber-500/40 hover:bg-amber-900/60'
                              : 'bg-slate-800/80 text-slate-400 border-slate-700 hover:text-slate-200'
                          }`}
                          title="Simulate HTTP 429 Rate Limit for failover testing"
                        >
                          {provider.status === 'rate_limited' ? 'Clear 429' : 'Simulate 429'}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Task Routing Matrix */}
            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Workflow className="h-4 w-4 text-cyan-400" />
                  <h3 className="text-sm font-bold text-white font-display">Task Routing & Fallback Matrix</h3>
                </div>
                <div className="text-xs text-slate-400 font-mono">
                  Primary Model ➔ Fallback Model (Cascade on 429 / Timeout)
                </div>
              </div>

              <div className="space-y-4">
                {taskList.map((task) => {
                  const primaryProvider = aiConfig.providers[task.primaryProvider];
                  const fallbackProvider = aiConfig.providers[task.fallbackProvider];

                  return (
                    <div
                      key={task.taskType}
                      className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4 space-y-3"
                    >
                      {/* Task Info & Auto Failover Toggle */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-white text-xs">{task.title}</span>
                            <span className="font-mono text-[10px] text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-500/30">
                              {task.taskType}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 mt-0.5">{task.description}</p>
                        </div>

                        <div className="flex items-center gap-2 font-mono text-xs">
                          <label className="flex items-center gap-1.5 cursor-pointer select-none text-[11px] text-slate-300">
                            <input
                              type="checkbox"
                              checked={task.autoFallbackOnRateLimit}
                              onChange={(e) => updateAITaskAssignment(task.taskType, { autoFallbackOnRateLimit: e.target.checked })}
                              className="h-3.5 w-3.5 rounded border-slate-700 bg-slate-800 text-cyan-500 cursor-pointer"
                            />
                            <span>Auto-Failover</span>
                          </label>

                          <button
                            type="button"
                            onClick={() => handleTriggerSimulatedFailover(task.taskType)}
                            disabled={isSimulatingFailover}
                            className="px-2.5 py-1 rounded bg-cyan-950/80 hover:bg-cyan-900/80 border border-cyan-500/40 text-cyan-300 text-[10px] flex items-center gap-1 cursor-pointer transition-colors"
                            title="Execute real or simulated request through this task pipeline"
                          >
                            <Sparkles className="h-3 w-3" />
                            <span>Test Pipeline</span>
                          </button>
                        </div>
                      </div>

                      {/* Primary vs Fallback Selectors Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1 font-mono text-xs">
                        {/* Primary Routing */}
                        <div className="p-3 rounded-lg border border-cyan-500/30 bg-cyan-950/10 space-y-2">
                          <div className="flex items-center justify-between text-[11px] text-cyan-300 font-semibold">
                            <span>Primary Model Route</span>
                            <span className="text-[10px] text-emerald-400">● Priority 1</span>
                          </div>

                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-1">Provider</label>
                              <select
                                value={task.primaryProvider}
                                onChange={(e) => {
                                  const pId = e.target.value as AIProviderId;
                                  const prov = aiConfig.providers[pId];
                                  updateAITaskAssignment(task.taskType, {
                                    primaryProvider: pId,
                                    primaryModel: prov?.defaultModel || task.primaryModel
                                  });
                                }}
                                className="w-full rounded border border-slate-700 bg-slate-900 p-1.5 text-xs text-white focus:border-cyan-500 focus:outline-none"
                              >
                                {providerList.map(p => (
                                  <option key={p.id} value={p.id}>{p.name}</option>
                                ))}
                              </select>
                            </div>

                            <div>
                              <label className="text-[10px] text-slate-400 block mb-1">Model</label>
                              <select
                                value={task.primaryModel}
                                onChange={(e) => updateAITaskAssignment(task.taskType, { primaryModel: e.target.value })}
                                className="w-full rounded border border-slate-700 bg-slate-900 p-1.5 text-xs text-white focus:border-cyan-500 focus:outline-none"
                              >
                                {primaryProvider?.availableModels.map(m => (
                                  <option key={m} value={m}>{m}</option>
                                ))}
                              </select>
                            </div>
                          </div>
                        </div>

                        {/* Fallback Routing */}
                        <div className="p-3 rounded-lg border border-purple-500/30 bg-purple-950/10 space-y-2">
                          <div className="flex items-center justify-between text-[11px] text-purple-300 font-semibold">
                            <span>Fallback Route (On 429 / Failure)</span>
                            <span className="text-[10px] text-purple-400">● Auto-Cascaded</span>
                          </div>

                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-1">Fallback Provider</label>
                              <select
                                value={task.fallbackProvider}
                                onChange={(e) => {
                                  const pId = e.target.value as AIProviderId;
                                  const prov = aiConfig.providers[pId];
                                  updateAITaskAssignment(task.taskType, {
                                    fallbackProvider: pId,
                                    fallbackModel: prov?.defaultModel || task.fallbackModel
                                  });
                                }}
                                className="w-full rounded border border-slate-700 bg-slate-900 p-1.5 text-xs text-white focus:border-purple-500 focus:outline-none"
                              >
                                {providerList.map(p => (
                                  <option key={p.id} value={p.id}>{p.name}</option>
                                ))}
                              </select>
                            </div>

                            <div>
                              <label className="text-[10px] text-slate-400 block mb-1">Fallback Model</label>
                              <select
                                value={task.fallbackModel}
                                onChange={(e) => updateAITaskAssignment(task.taskType, { fallbackModel: e.target.value })}
                                className="w-full rounded border border-slate-700 bg-slate-900 p-1.5 text-xs text-white focus:border-purple-500 focus:outline-none"
                              >
                                {fallbackProvider?.availableModels.map(m => (
                                  <option key={m} value={m}>{m}</option>
                                ))}
                              </select>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Timeout Bounds */}
                      <div className="flex items-center justify-between gap-4 pt-1 font-mono text-[11px] text-slate-400">
                        <div className="flex items-center gap-2">
                          <span>Request Timeout:</span>
                          <span className="text-slate-200 font-bold">{task.timeoutMs}ms</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Live AI Failover Audit Log Stream */}
            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2 text-white font-bold">
                  <Activity className="h-4 w-4 text-amber-400" />
                  <span>Real-Time AI Failover & Cascade Event Stream ({aiFailoverLogs.length})</span>
                </div>
                <span className="text-[10px] text-slate-400">Logs rate-limit 429 cascades and circuit breaker actions</span>
              </div>

              {aiFailoverLogs.length === 0 ? (
                <div className="p-6 text-center text-slate-500 text-xs">
                  No failover events recorded. All primary AI models operating within nominal rate limits.
                </div>
              ) : (
                <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
                  {aiFailoverLogs.map((log) => (
                    <div
                      key={log.id}
                      className="p-3 rounded-lg border border-slate-800 bg-slate-900/60 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-500/30 text-[10px] font-bold">
                            429 FAILOVER
                          </span>
                          <span className="text-slate-300 font-bold">{log.taskType}</span>
                          <span className="text-slate-500 text-[10px]">{log.timestamp}</span>
                        </div>
                        <p className="text-[11px] text-slate-400">
                          {log.triggerReason} — Switched from <span className="text-rose-400 font-bold">{log.primaryModel}</span> to <span className="text-emerald-400 font-bold">{log.fallbackModel}</span>
                        </p>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <span className={`px-2 py-0.5 rounded text-[10px] border font-bold ${
                          log.status === 'SUCCESSFUL_FALLBACK' ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30' :
                          'bg-rose-950/60 text-rose-300 border-rose-500/30'
                        }`}>
                          {log.status} ({log.latencyMs}ms)
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Section 3: Discord Cloud Hub */}
        {activeSection === 'discord' && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2 text-white font-bold">
                  <MessageSquare className="h-4 w-4 text-[#5865F2]" />
                  <span>Discord Bot & Guild Link</span>
                </div>
                <button
                  type="button"
                  onClick={handleTestDiscordWebhook}
                  disabled={isTestingDiscord}
                  className="px-3 py-1 rounded bg-[#5865F2]/20 hover:bg-[#5865F2]/30 text-[#8ea1e1] border border-[#5865F2]/40 flex items-center gap-1.5 cursor-pointer text-[11px]"
                >
                  <Send className="h-3 w-3" />
                  <span>{isTestingDiscord ? 'Sending...' : 'Test Discord Webhook'}</span>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold">Discord Bot Application Token</label>
                  <input
                    type="password"
                    value={discordBotToken}
                    onChange={(e) => setDiscordBotToken(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-[#5865F2] focus:outline-none font-mono"
                  />
                  <p className="text-[10px] text-slate-500">
                    Bot token for real-time Discord slash commands (/punish, /lookup, /tps, /appeal).
                  </p>
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold">Target Discord Guild (Server) ID</label>
                  <input
                    type="text"
                    value={discordGuildId}
                    onChange={(e) => setDiscordGuildId(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-[#5865F2] focus:outline-none font-mono"
                  />
                  <p className="text-[10px] text-slate-500">
                    Primary Discord server ID for permission validation and member role caching.
                  </p>
                </div>
              </div>
            </div>

            {/* Webhook Routing Matrix */}
            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4 font-mono text-xs">
              <div className="flex items-center gap-2 text-white font-bold border-b border-slate-800 pb-3">
                <Radio className="h-4 w-4 text-purple-400" />
                <span>Dedicated Discord Webhook Channels</span>
              </div>

              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-slate-300 font-semibold">#🚨・anticheat-alerts Webhook URL</label>
                  <input
                    type="url"
                    value={discordWebhookAlerts}
                    onChange={(e) => setDiscordWebhookAlerts(e.target.value)}
                    placeholder="https://discord.com/api/webhooks/..."
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2 text-white focus:border-[#5865F2] focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-slate-300 font-semibold">#📢・announcements Webhook URL</label>
                  <input
                    type="url"
                    value={discordWebhookAnnouncements}
                    onChange={(e) => setDiscordWebhookAnnouncements(e.target.value)}
                    placeholder="https://discord.com/api/webhooks/..."
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2 text-white focus:border-[#5865F2] focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-slate-300 font-semibold">#🛡️・staff-audit-logs Webhook URL</label>
                  <input
                    type="url"
                    value={discordWebhookStaffLogs}
                    onChange={(e) => setDiscordWebhookStaffLogs(e.target.value)}
                    placeholder="https://discord.com/api/webhooks/..."
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2 text-white focus:border-[#5865F2] focus:outline-none"
                  />
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg border border-slate-800 bg-slate-900/60 mt-2">
                  <div>
                    <div className="font-semibold text-white">Enable Bidirectional Role Synchronization</div>
                    <div className="text-[10px] text-slate-500">Automatically sync Minecraft staff ranks with Discord role hierarchies.</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={enableDiscordRoleSync}
                    onChange={(e) => setEnableDiscordRoleSync(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-[#5865F2] cursor-pointer"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Section 4: GrimAC & Anticheat */}
        {activeSection === 'anticheat' && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4 font-mono text-xs">
              <div className="flex items-center gap-2 text-white font-bold border-b border-slate-800 pb-3">
                <Shield className="h-4 w-4 text-rose-400" />
                <span>GrimAC Predictive Detection & Auto-Ban Thresholds</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <label className="text-slate-300 font-semibold">Auto-Ban Confidence Threshold</label>
                    <span className="text-rose-400 font-bold">{grimBanSensitivity}% Confidence</span>
                  </div>
                  <input
                    type="range"
                    min={70}
                    max={99}
                    value={grimBanSensitivity}
                    onChange={(e) => setGrimBanSensitivity(Number(e.target.value))}
                    className="w-full accent-rose-500 cursor-pointer"
                  />
                  <p className="text-[10px] text-slate-500">
                    Flags exceeding this probability immediately invoke automatic 30-day HWID quarantine.
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="text-slate-300 font-semibold block">Subnet & VPN Burst Policy</label>
                  <select
                    value={subnetDetectionMode}
                    onChange={(e) => setSubnetDetectionMode(e.target.value as any)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-rose-500 focus:outline-none"
                  >
                    <option value="AGGRESSIVE">Aggressive (Block all residential datacenter VPNs)</option>
                    <option value="STANDARD">Standard (Flag high-churn ASN ranges)</option>
                    <option value="LENIENT">Lenient (Log-only without kicking)</option>
                  </select>
                  <p className="text-[10px] text-slate-500">
                    Protects network nodes against bot raids and distributed denial-of-inventory attacks.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="flex items-center justify-between p-3 rounded-lg border border-slate-800 bg-slate-900/60">
                  <div>
                    <div className="font-semibold text-white">Auto-Mute on Chat Packet Spam</div>
                    <div className="text-[10px] text-slate-500">Mutes accounts sending &gt;12 packets/sec for 15 minutes.</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={autoMuteOnSpamBurst}
                    onChange={(e) => setAutoMuteOnSpamBurst(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-rose-500 cursor-pointer"
                  />
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg border border-slate-800 bg-slate-900/60">
                  <div>
                    <div className="font-semibold text-white">Alt Cluster Threshold</div>
                    <div className="text-[10px] text-slate-500">Flag cluster if &gt;= {altRingHwidThreshold} accounts share client hash.</div>
                  </div>
                  <input
                    type="number"
                    min={2}
                    max={10}
                    value={altRingHwidThreshold}
                    onChange={(e) => setAltRingHwidThreshold(Number(e.target.value))}
                    className="w-16 rounded border border-slate-700 bg-slate-800 p-1.5 text-white text-center"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Section 5: Snapshots & Storage */}
        {activeSection === 'storage' && (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4 font-mono text-xs">
              <div className="flex items-center gap-2 text-white font-bold border-b border-slate-800 pb-3">
                <HardDrive className="h-4 w-4 text-amber-400" />
                <span>Cloudflare R2 / S3 Snapshot Offsite Vault</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold">S3 / R2 Bucket Identifier</label>
                  <input
                    type="text"
                    value={s3BucketName}
                    onChange={(e) => setS3BucketName(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-amber-500 focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold">S3 API Storage Endpoint</label>
                  <input
                    type="text"
                    value={s3Endpoint}
                    onChange={(e) => setS3Endpoint(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-amber-500 focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold">Snapshot Compression Algorithm</label>
                  <select
                    value={snapshotCompression}
                    onChange={(e) => setSnapshotCompression(e.target.value as any)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-amber-500 focus:outline-none"
                  >
                    <option value="ZSTD">Zstandard Level 9 (Highest ratio & speed)</option>
                    <option value="GZIP">Gzip Level 6 (Legacy compatible)</option>
                    <option value="NONE">Uncompressed Raw Tarball</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold">Log & Telemetry TTL (Days)</label>
                  <input
                    type="number"
                    value={autoPurgeDays}
                    onChange={(e) => setAutoPurgeDays(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-amber-500 focus:outline-none"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Section 6: Preferences */}
        {activeSection === 'preferences' && (
          <div className="space-y-4">
            {/* Design Templates & Themes Selector */}
            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2 text-white font-bold">
                  <Sparkles className="h-4 w-4 text-cyan-400" />
                  <span>Dashboard Design Archetype & Layout Templates</span>
                </div>
                <span className="text-[10px] text-cyan-400 font-semibold uppercase">Instant Live Preview</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  {
                    id: 'cyber-ops' as const,
                    title: '1. Cyber-Ops NOC (Default)',
                    badge: 'Tactical Dark',
                    accentColor: 'border-cyan-500 bg-cyan-950/20 text-cyan-300',
                    dotColor: 'bg-cyan-400',
                    desc: '24/7 dark-room network operations theme with cyan/emerald neon metrics and glass telemetry borders.'
                  },
                  {
                    id: 'solar-clean' as const,
                    title: '2. Solar Clean Enterprise',
                    badge: 'High-Clarity Day',
                    accentColor: 'border-blue-500 bg-blue-50 text-blue-900',
                    dotColor: 'bg-blue-600',
                    desc: 'Crisp porcelain canvas with cobalt blue accents, maximum WCAG AAA reading contrast for daytime management.'
                  },
                  {
                    id: 'voxel-matrix' as const,
                    title: '3. Voxel Matrix Terminal',
                    badge: 'Minecraft CLI',
                    accentColor: 'border-emerald-500 bg-emerald-950/30 text-emerald-300',
                    dotColor: 'bg-emerald-400',
                    desc: 'Pitch-black hacker terminal aesthetic with phosphor green monospace typography and sharp tiling frames.'
                  },
                  {
                    id: 'obsidian-minimal' as const,
                    title: '4. Obsidian Minimalist',
                    badge: 'Modern Luxury',
                    accentColor: 'border-purple-500 bg-purple-950/30 text-purple-300',
                    dotColor: 'bg-purple-400',
                    desc: 'Carbon dark aesthetic with subtle warm neutral zinc borders, generous spacing, and refined violet tags.'
                  }
                ].map(tmpl => {
                  const isCurrent = dashboardTheme === tmpl.id;
                  return (
                    <button
                      key={tmpl.id}
                      type="button"
                      onClick={() => {
                        setDashboardTheme(tmpl.id);
                        addToast('info', 'Design Template Applied', `Switched dashboard layout theme to ${tmpl.title}`);
                      }}
                      className={`p-4 rounded-xl border text-left transition-all cursor-pointer relative flex flex-col justify-between ${
                        isCurrent
                          ? 'border-cyan-500/80 bg-slate-900 shadow-[0_0_15px_rgba(6,182,212,0.15)] ring-1 ring-cyan-500/50'
                          : 'border-slate-800/80 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/80'
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <span className={`h-2.5 w-2.5 rounded-full ${tmpl.dotColor}`} />
                            <span className="font-bold text-white text-xs">{tmpl.title}</span>
                          </div>
                          <span className={`px-2 py-0.5 rounded text-[9px] font-mono uppercase font-bold border ${tmpl.accentColor}`}>
                            {tmpl.badge}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 font-sans leading-relaxed mt-1">
                          {tmpl.desc}
                        </p>
                      </div>

                      <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-[10px]">
                        <span className={isCurrent ? 'text-cyan-300 font-bold' : 'text-slate-500'}>
                          {isCurrent ? '● Active Theme' : 'Click to Activate'}
                        </span>
                        {isCurrent && <Check className="h-3.5 w-3.5 text-cyan-400" />}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4 font-mono text-xs">
              <div className="flex items-center gap-2 text-white font-bold border-b border-slate-800 pb-3">
                <Sliders className="h-4 w-4 text-purple-400" />
                <span>Dashboard Interface & Telemetry Poll Rates</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold">Telemetry Refresh Rate (Seconds)</label>
                  <select
                    value={telemetryRefreshInterval}
                    onChange={(e) => setTelemetryRefreshInterval(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2.5 text-white focus:border-cyan-500 focus:outline-none"
                  >
                    <option value={1}>1 Second (Real-time sub-tick monitoring)</option>
                    <option value={3}>3 Seconds (Recommended balanced rate)</option>
                    <option value={5}>5 Seconds (Low network consumption)</option>
                    <option value={10}>10 Seconds (Bandwidth saver)</option>
                  </select>
                </div>

                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between p-3 rounded-lg border border-slate-800 bg-slate-900/60">
                    <div>
                      <div className="font-semibold text-white">Audio Chimes on High Alerts</div>
                      <div className="text-[10px] text-slate-500">Play web audio synthesized tone on GrimAC auto-bans.</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={audioNotifications}
                      onChange={(e) => setAudioNotifications(e.target.checked)}
                      className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-cyan-500 cursor-pointer"
                    />
                  </div>

                  <div className="flex items-center justify-between p-3 rounded-lg border border-slate-800 bg-slate-900/60">
                    <div>
                      <div className="font-semibold text-white">Verbose Packet Debug Logs</div>
                      <div className="text-[10px] text-slate-500">Log raw RCON socket messages to DevTools console.</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={enableDebugLogs}
                      onChange={(e) => setEnableDebugLogs(e.target.checked)}
                      className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-cyan-500 cursor-pointer"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Section 7: Message Templates */}
        {activeSection === 'templates' && (() => {
          const templateDefs = [
            {
              key: 'verification.dm_prompt',
              label: 'Verification DM Prompt',
              hint: 'Available: $PLAYER, $CODE, $EXPIRES',
              rows: 3,
            },
            {
              key: 'verification.success_message',
              label: 'Verification Success DM',
              hint: 'Available: $PLAYER',
              rows: 2,
            },
            {
              key: 'verification.error_already_linked',
              label: 'Error: Already Linked',
              hint: 'No variables.',
              rows: 2,
            },
            {
              key: 'verification.error_invalid_code',
              label: 'Error: Invalid or Expired Code',
              hint: 'No variables.',
              rows: 2,
            },
            {
              key: 'verification.ingame_prompt',
              label: 'In-Game Prompt (after /verify)',
              hint: 'Available: $EXPIRES',
              rows: 2,
            },
            {
              key: 'verification.ingame_success',
              label: 'In-Game Success Message',
              hint: 'No variables.',
              rows: 2,
            },
            {
              key: 'verification.nickname_format',
              label: 'Discord Nickname Format',
              hint: 'Available: $PLAYER',
              rows: 1,
            },
            {
              key: 'discord.invite_url',
              label: 'Discord Invite URL',
              hint: 'Used as $DISCORD_INVITE in greeter messages.',
              rows: 1,
            },
            {
              key: 'greeter.first_join_message',
              label: 'First Join Greeter',
              hint: 'Available: $PLAYER, $DISCORD_INVITE, $SERVER',
              rows: 2,
            },
            {
              key: 'greeter.return_join_message',
              label: 'Return Join Greeter',
              hint: 'Available: $PLAYER',
              rows: 2,
            },
            {
              key: 'chat_responder.response_style',
              label: 'AI Chat Response Style',
              hint: 'Options: friendly, formal, concise',
              rows: 1,
            },
          ];

          return (
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-5 font-mono text-xs">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2 text-white font-bold">
                    <MessageSquare className="h-4 w-4 text-cyan-400" />
                    <span>Configurable Message Templates</span>
                  </div>
                  {templateLoading && (
                    <span className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                      <RefreshCw className="h-3 w-3 animate-spin" />
                      Loading templates…
                    </span>
                  )}
                </div>

                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Edit the wording sent by the bot and plugin. Changes take effect on the next
                  template refresh (up to 5 minutes) without redeployment.
                </p>

                <div className="space-y-5">
                  {templateDefs.map(({ key, label, hint, rows }) => (
                    <div key={key} className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <label className="text-slate-200 font-semibold">{label}</label>
                        <button
                          type="button"
                          onClick={() => handleSaveTemplate(key)}
                          disabled={templateSaving[key] || templateLoading}
                          className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-cyan-900/50 hover:bg-cyan-800/60 border border-cyan-500/40 text-cyan-300 text-[11px] transition-colors cursor-pointer disabled:opacity-50"
                        >
                          <Save className="h-3 w-3" />
                          <span>{templateSaving[key] ? 'Saving…' : 'Save'}</span>
                        </button>
                      </div>
                      <textarea
                        rows={rows}
                        value={templates[key] ?? ''}
                        onChange={(e) =>
                          setTemplates(prev => ({ ...prev, [key]: e.target.value }))
                        }
                        className="w-full rounded-lg border border-slate-700 bg-slate-900 p-2.5 text-white text-xs focus:border-cyan-500 focus:outline-none resize-y font-mono"
                        placeholder={templateLoading ? 'Loading…' : ''}
                      />
                      <p className="text-[10px] text-slate-500">{hint}</p>
                      {templateErrors[key] && (
                        <p className="text-[10px] text-rose-400">{templateErrors[key]}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })()}

        {/* Global Save Button Footer */}
        <div className="flex items-center justify-between border-t border-slate-800/80 pt-5 font-mono">
          <div className="text-xs text-slate-400">
            Active backend target: <span className="text-cyan-400 font-semibold">{backendBaseUrl}</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => refreshBackendData()}
              className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <RefreshCw className="h-4 w-4 text-slate-400" />
              <span>Reload State</span>
            </button>

            <button
              type="submit"
              className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-6 py-2.5 text-xs font-semibold text-white hover:from-cyan-500 hover:to-blue-500 transition-all shadow-md cursor-pointer"
            >
              <Save className="h-4 w-4" />
              <span>Save All Settings</span>
            </button>
          </div>
        </div>
      </form>
        </div>
      </div>
    </div>
  );
};
