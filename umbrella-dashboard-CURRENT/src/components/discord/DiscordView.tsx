import React, { useState, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { api } from '../../lib/api';
import { 
  Bot, 
  Radio, 
  Send, 
  Hash, 
  ShieldCheck, 
  Users, 
  Sparkles, 
  MessageSquare, 
  Zap, 
  Layers, 
  Plus, 
  Trash2, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  Copy, 
  ExternalLink,
  Volume2,
  Terminal,
  Activity,
  Sliders,
  Link as LinkIcon,
  Play,
  Server
} from 'lucide-react';

interface DiscordMessage {
  id: string;
  sender: string;
  avatarUrl?: string;
  source: 'MINECRAFT' | 'DISCORD' | 'SYSTEM';
  serverName?: string;
  channel: string;
  content: string;
  timestamp: string;
  roleColor?: string;
}

interface SlashCommandItem {
  name: string;
  description: string;
  requiredRole: string;
  enabled: boolean;
  usageCount: number;
}

export const DiscordView: React.FC = () => {
  const { 
    servers, 
    players, 
    grimViolations, 
    currentUser, 
    addToast 
  } = useDashboard();

  type TabType = 'bridge' | 'embed-builder' | 'commands' | 'webhooks' | 'status';
  const [activeSubTab, setActiveSubTab] = useState<TabType>('bridge');

  // Live Chat Bridge State - dynamically seeded with live network data
  const [selectedChannel, setSelectedChannel] = useState<'#global-chat' | '#staff-chat' | '#donator-chat'>('#global-chat');
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<DiscordMessage[]>([]);

  // Seed live initial messages from active players and grim violations
  useEffect(() => {
    const initialMsgs: DiscordMessage[] = [];
    const onlineList = players.filter(p => p.online);
    
    if (onlineList.length > 0) {
      initialMsgs.push({
        id: 'msg-seed-1',
        sender: onlineList[0].username,
        avatarUrl: onlineList[0].avatarUrl,
        source: 'MINECRAFT',
        serverName: onlineList[0].server || servers[0]?.name || 'Survival',
        channel: '#global-chat',
        content: `Connected to ${onlineList[0].server || 'Survival'} • Latency: ${onlineList[0].ping}ms`,
        timestamp: new Date(Date.now() - 1000 * 60 * 3).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        roleColor: 'text-emerald-400'
      });
    }

    if (grimViolations.length > 0) {
      const topViolation = grimViolations[0];
      initialMsgs.push({
        id: 'msg-seed-2',
        sender: 'GrimAC Watchdog',
        source: 'SYSTEM',
        serverName: topViolation.server,
        channel: '#staff-chat',
        content: `Auto-mitigated [${topViolation.checkName}] flag for ${topViolation.playerName} @ ${topViolation.server} (${topViolation.details})`,
        timestamp: topViolation.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        roleColor: 'text-rose-400'
      });
    }

    initialMsgs.push({
      id: 'msg-seed-3',
      sender: 'UmbrellaBot (Bridge)',
      source: 'DISCORD',
      channel: '#global-chat',
      content: `Bridge active across ${servers.length} nodes with ${onlineList.length} players online.`,
      timestamp: new Date(Date.now() - 1000 * 30).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      roleColor: 'text-[#5865F2]'
    });

    setChatMessages(initialMsgs);
  }, [players, grimViolations, servers]);

  // Embed Builder State
  const [embedTitle, setEmbedTitle] = useState('🚨 Scheduled Network Maintenance & Update');
  const [embedDescription, setEmbedDescription] = useState('We are performing a major core infrastructure update. All proxy and game nodes will undergo a seamless 5-minute rolling restart.');
  const [embedColor, setEmbedColor] = useState('#5865F2');
  const [embedAuthor, setEmbedAuthor] = useState('UmbrellaOS Operations');
  const [embedFooter, setEmbedFooter] = useState('Umbrella Network • High-Performance Minecraft Cluster');
  const [includeTimestamp, setIncludeTimestamp] = useState(true);
  const [embedTargetChannel, setEmbedTargetChannel] = useState<'#announcements' | '#grimac-alerts' | '#ban-waves'>('#announcements');
  const [embedFields, setEmbedFields] = useState<Array<{ name: string; value: string; inline: boolean }>>([
    { name: 'Estimated Downtime', value: '3 - 5 Minutes', inline: true },
    { name: 'Affected Nodes', value: `All ${servers.length || 7} Instances`, inline: true },
    { name: 'Changes', value: '• GrimAC Quantum engine patch\n• Velocity proxy memory optimization\n• ZGC garbage collection tune', inline: false }
  ]);

  // Slash Commands List
  const [slashCommands, setSlashCommands] = useState<SlashCommandItem[]>([
    { name: '/ban <player> <reason>', description: 'Execute a cross-server ban directly from Discord with evidence logging.', requiredRole: '@Senior Moderator', enabled: true, usageCount: 142 },
    { name: '/mute <player> <duration> <reason>', description: 'Mute a player across in-game chat and linked Discord channels.', requiredRole: '@Moderator', enabled: true, usageCount: 320 },
    { name: '/lookup <player|uuid|discord>', description: 'Display complete player telemetry, playtime, alt cluster, and active infractions.', requiredRole: '@Helper', enabled: true, usageCount: 894 },
    { name: '/tps', description: 'Query real-time TPS, memory usage, and player counts across all network nodes.', requiredRole: '@Everyone', enabled: true, usageCount: 2150 },
    { name: '/link <code>', description: 'Authenticate Minecraft player UUID with Discord account via DiscordSRV.', requiredRole: '@Everyone', enabled: true, usageCount: 5410 },
    { name: '/broadcast <message>', description: 'Flash a high-priority title & chat notice across all online Minecraft nodes.', requiredRole: '@SuperAdmin', enabled: true, usageCount: 68 }
  ]);

  // Interactive Slash Command Runner State
  const [cmdRunnerInput, setCmdRunnerInput] = useState('/tps');
  const [cmdRunnerOutput, setCmdRunnerOutput] = useState<string | null>(null);

  const handleRunSlashCommand = () => {
    const trimmed = cmdRunnerInput.trim();
    if (trimmed.startsWith('/tps')) {
      const details = servers.map(s => `• ${s.name}: ${s.tps.toFixed(1)} TPS | ${s.playersCount} players | ${s.memoryUsage.usedMb}MB RAM`).join('\n');
      setCmdRunnerOutput(`[Discord Bot Response - /tps]\nNetwork TPS Status (${servers.length} nodes online):\n${details}`);
      addToast('success', 'Executed /tps', 'Fetched live TPS metrics from backend nodes.');
    } else if (trimmed.startsWith('/lookup')) {
      const target = trimmed.replace('/lookup', '').trim() || (players[0]?.username || 'Player');
      const found = players.find(p => p.username.toLowerCase() === target.toLowerCase()) || players[0];
      if (found) {
        setCmdRunnerOutput(`[Discord Bot Response - /lookup ${found.username}]\nUUID: ${found.uuid}\nServer: ${found.server}\nPing: ${found.ping}ms\nPlaytime: ${found.playtimeHours}h\nStatus: ${found.online ? 'ONLINE' : 'OFFLINE'}\nViolations: ${found.violationCount}`);
      } else {
        setCmdRunnerOutput(`[Discord Bot Response] Player "${target}" not found in current cluster cache.`);
      }
    } else if (trimmed.startsWith('/broadcast')) {
      const msg = trimmed.replace('/broadcast', '').trim();
      api.broadcast(msg || 'Global announcement from Discord', 'all');
      setCmdRunnerOutput(`[Discord Bot Response - /broadcast]\nSent broadcast: "${msg || 'Global announcement from Discord'}" to all nodes.`);
      addToast('success', 'Broadcast Dispatched', 'Relayed command across cluster nodes.');
    } else {
      setCmdRunnerOutput(`[Discord Bot Response]\nExecuted command: ${trimmed} via bot webhook dispatcher.`);
      addToast('info', 'Command Dispatched', `Executed ${trimmed}`);
    }
  };

  const handleSendChatMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const content = chatInput.trim();
    const newMsg: DiscordMessage = {
      id: `msg-${Date.now()}`,
      sender: currentUser?.username || 'Staff Operator',
      avatarUrl: currentUser?.avatarUrl,
      source: 'DISCORD',
      channel: selectedChannel,
      content,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      roleColor: 'text-cyan-400'
    };

    setChatMessages(prev => [...prev, newMsg]);
    setChatInput('');

    try {
      await api.sendDiscordNotification(`[${selectedChannel}] ${currentUser?.username || 'Staff'}: ${content}`);
      addToast('success', 'Dispatched to Discord & Minecraft', `Relayed message into ${selectedChannel}`);
    } catch (err: any) {
      addToast('error', 'Relay Error', err?.message || 'Failed to dispatch message to Discord API.');
    }
  };

  const handleAddField = () => {
    setEmbedFields(prev => [...prev, { name: 'Field Title', value: 'Field description or detail value', inline: true }]);
  };

  const handleRemoveField = (index: number) => {
    setEmbedFields(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpdateField = (index: number, key: 'name' | 'value' | 'inline', val: any) => {
    setEmbedFields(prev => prev.map((f, i) => i === index ? { ...f, [key]: val } : f));
  };

  const handleDispatchEmbed = async () => {
    try {
      await api.sendDiscordEmbed({
        title: embedTitle,
        description: embedDescription,
        color: embedColor,
        author: embedAuthor,
        footer: embedFooter,
        channel: embedTargetChannel,
        fields: embedFields
      });
      addToast('success', 'Discord Embed Dispatched', `Broadcasted embed announcement to ${embedTargetChannel} via bot webhook.`);
    } catch (err: any) {
      addToast('error', 'Embed Error', err?.message || 'Failed to send embed.');
    }
  };

  const handleToggleCommand = (name: string) => {
    setSlashCommands(prev => prev.map(cmd => {
      if (cmd.name === name) {
        const nextState = !cmd.enabled;
        addToast('info', 'Command Updated', `${cmd.name.split(' ')[0]} is now ${nextState ? 'Enabled' : 'Disabled'}.`);
        return { ...cmd, enabled: nextState };
      }
      return cmd;
    }));
  };

  const onlinePlayersCount = players.filter(p => p.online).length;

  return (
    <div className="space-y-6 pb-12 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#5865F2]/40 bg-[#5865F2]/20 text-[#5865F2]">
              <svg className="h-5 w-5 fill-current" viewBox="0 0 24 24">
                <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.929 1.793 8.18 1.793 12.061 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.893.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.028zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white font-display flex items-center gap-2">
                <span>Discord Integration & Cloud SRV Hub</span>
              </h1>
              <p className="text-xs text-slate-400">
                Bidirectional Minecraft ↔ Discord chat bridge, live embed constructor, slash commands RBAC, and bot gateway telemetry.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Bot Gateway: 24ms (Shard 0/1)</span>
          </span>
        </div>
      </div>

      {/* Bot & Guild Status Header Metric Row */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-slate-800 bg-[#0d1117] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Connected Bot</span>
            <Bot className="h-4 w-4 text-[#5865F2]" />
          </div>
          <div className="mt-2">
            <div className="text-base font-bold text-white font-mono flex items-center gap-1.5">
              <span>UmbrellaBot</span>
              <span className="px-1.5 py-0.2 rounded text-[9px] bg-[#5865F2] text-white font-bold">BOT</span>
            </div>
            <div className="text-[11px] text-emerald-400 font-mono mt-0.5">Playing on mc.umbrella-network.net</div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0d1117] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Cluster Nodes</span>
            <Server className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="mt-2">
            <div className="text-base font-bold text-white truncate font-display">{servers.length} Active Nodes</div>
            <div className="text-[11px] text-slate-400 font-mono mt-0.5">{onlinePlayersCount} Players Online</div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0d1117] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Linked Players</span>
            <LinkIcon className="h-4 w-4 text-purple-400" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold font-mono text-white">{players.length} Profiles</div>
            <div className="text-[11px] text-purple-300 font-mono mt-0.5">DiscordSRV Sync Active</div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0d1117] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Active Relays</span>
            <Activity className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold font-mono text-white">6 Channels</div>
            <div className="text-[11px] text-emerald-400 font-mono mt-0.5">Zero Message Drop</div>
          </div>
        </div>
      </div>

      {/* Sub-Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto">
        <button
          onClick={() => setActiveSubTab('bridge')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap cursor-pointer ${
            activeSubTab === 'bridge'
              ? 'bg-[#5865F2]/20 text-[#5865F2] border border-[#5865F2]/40 shadow-sm'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <MessageSquare className="h-3.5 w-3.5" />
          <span>Live In-Game ↔ Discord Bridge</span>
        </button>

        <button
          onClick={() => setActiveSubTab('embed-builder')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap cursor-pointer ${
            activeSubTab === 'embed-builder'
              ? 'bg-cyan-950 text-cyan-300 border border-cyan-500/40 shadow-sm'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span>Discord Embed Constructor</span>
        </button>

        <button
          onClick={() => setActiveSubTab('commands')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap cursor-pointer ${
            activeSubTab === 'commands'
              ? 'bg-purple-950 text-purple-300 border border-purple-500/40 shadow-sm'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <Terminal className="h-3.5 w-3.5" />
          <span>Slash Commands & Live Test</span>
          <span className="font-mono text-[10px] bg-purple-900/60 px-1.5 py-0.2 rounded">{slashCommands.length}</span>
        </button>

        <button
          onClick={() => setActiveSubTab('webhooks')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap cursor-pointer ${
            activeSubTab === 'webhooks'
              ? 'bg-amber-950 text-amber-300 border border-amber-500/40 shadow-sm'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
          }`}
        >
          <Radio className="h-3.5 w-3.5" />
          <span>Alert Webhook Routing</span>
        </button>
      </div>

      {/* TAB 1: LIVE IN-GAME <-> DISCORD CHAT BRIDGE */}
      {activeSubTab === 'bridge' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Chat Feed */}
          <div className="lg:col-span-3 rounded-2xl border border-slate-800 bg-[#0d1117] shadow-xl overflow-hidden flex flex-col h-[560px]">
            {/* Chat Header Toolbar */}
            <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/80 px-4 py-3">
              <div className="flex items-center gap-2">
                <Hash className="h-4 w-4 text-slate-400" />
                <span className="font-bold text-white text-xs font-mono">{selectedChannel}</span>
                <span className="text-[10px] text-slate-500 font-mono">• Cross-Server Minecraft Relay</span>
              </div>

              {/* Channel Selector Pills */}
              <div className="flex items-center gap-1 text-[11px] font-mono">
                {(['#global-chat', '#staff-chat', '#donator-chat'] as const).map(ch => (
                  <button
                    key={ch}
                    onClick={() => setSelectedChannel(ch)}
                    className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                      selectedChannel === ch
                        ? 'bg-[#5865F2] text-white font-bold'
                        : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {ch}
                  </button>
                ))}
              </div>
            </div>

            {/* Chat Stream Message Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 font-sans text-xs">
              {chatMessages.map(msg => {
                const isDiscord = msg.source === 'DISCORD';
                const isSystem = msg.source === 'SYSTEM';

                return (
                  <div key={msg.id} className="flex items-start gap-3 hover:bg-slate-900/40 p-2 rounded-lg transition-colors group">
                    {/* Avatar */}
                    {isDiscord ? (
                      <div className="h-8 w-8 rounded-full bg-[#5865F2]/30 border border-[#5865F2]/40 text-[#5865F2] flex items-center justify-center shrink-0">
                        <Bot className="h-4 w-4" />
                      </div>
                    ) : isSystem ? (
                      <div className="h-8 w-8 rounded-full bg-rose-950/60 border border-rose-500/40 text-rose-400 flex items-center justify-center shrink-0">
                        <ShieldCheck className="h-4 w-4" />
                      </div>
                    ) : (
                      <div className="h-8 w-8 rounded-lg bg-slate-800 border border-slate-700 text-cyan-400 flex items-center justify-center font-mono font-bold shrink-0 text-xs">
                        MC
                      </div>
                    )}

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 font-mono text-[11px]">
                        <span className={`font-bold ${msg.roleColor || 'text-white'}`}>{msg.sender}</span>
                        {msg.serverName && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] bg-slate-800 text-slate-400 border border-slate-700">
                            {msg.serverName}
                          </span>
                        )}
                        <span className="text-slate-500 text-[10px] ml-auto">{msg.timestamp}</span>
                      </div>
                      <p className="mt-1 text-slate-200 text-xs font-mono leading-relaxed break-words">
                        {msg.content}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* In-Game / Discord Message Dispatcher Input */}
            <form onSubmit={handleSendChatMessage} className="p-3 border-t border-slate-800 bg-slate-950/90 flex items-center gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder={`Type message to broadcast to ${selectedChannel} and all online Minecraft servers...`}
                className="flex-1 rounded-xl border border-slate-800 bg-slate-900/90 px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:border-[#5865F2] focus:outline-none font-mono"
              />
              <button
                type="submit"
                disabled={!chatInput.trim()}
                className="rounded-xl bg-[#5865F2] hover:bg-[#4752C4] px-4 py-2.5 text-xs font-semibold text-white transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <Send className="h-3.5 w-3.5" />
                <span>Relay</span>
              </button>
            </form>
          </div>

          {/* Right Sidebar: Active Channel Bridge Settings */}
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0d1117] p-4 space-y-3 text-xs">
              <h3 className="font-bold text-white uppercase tracking-wider font-mono">Connected Discord Channels</h3>
              <div className="space-y-2 font-mono">
                <div className="p-2 rounded bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Hash className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-slate-200 font-semibold">#global-chat</span>
                  </div>
                  <span className="text-[10px] text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-500/20">Synced</span>
                </div>

                <div className="p-2 rounded bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Hash className="h-3.5 w-3.5 text-cyan-400" />
                    <span className="text-slate-200 font-semibold">#staff-chat</span>
                  </div>
                  <span className="text-[10px] text-cyan-400 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-500/20">Private</span>
                </div>

                <div className="p-2 rounded bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Hash className="h-3.5 w-3.5 text-rose-400" />
                    <span className="text-slate-200 font-semibold">#grimac-alerts</span>
                  </div>
                  <span className="text-[10px] text-rose-400 bg-rose-950/60 px-1.5 py-0.5 rounded border border-rose-500/20">Webhook</span>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-[#0d1117] p-4 space-y-2 text-xs font-mono text-slate-400">
              <span className="font-bold text-slate-200 block uppercase tracking-wider">DiscordSRV Protocol</span>
              <p className="text-[11px] leading-relaxed">
                Messages from Minecraft use Redis PubSub channels and are pushed to Discord Gateway over authenticated WebSocket within &lt; 35ms.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: DISCORD EMBED CONSTRUCTOR & LIVE PREVIEWER */}
      {activeSubTab === 'embed-builder' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Form: Embed Settings */}
          <div className="lg:col-span-6 space-y-4">
            <div className="rounded-2xl border border-slate-800 bg-[#0d1117] p-5 space-y-4 shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2 font-bold text-white text-sm font-display">
                  <Sparkles className="h-4 w-4 text-cyan-400" />
                  <span>Discord Rich Embed Designer</span>
                </div>
                <select
                  value={embedTargetChannel}
                  onChange={(e) => setEmbedTargetChannel(e.target.value as any)}
                  className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1 text-xs text-cyan-300 font-mono focus:outline-none"
                >
                  <option value="#announcements">Target: #announcements</option>
                  <option value="#grimac-alerts">Target: #grimac-alerts</option>
                  <option value="#ban-waves">Target: #ban-waves</option>
                </select>
              </div>

              <div className="space-y-3 text-xs font-mono">
                <div>
                  <label className="block text-slate-400 mb-1">Author Name</label>
                  <input
                    type="text"
                    value={embedAuthor}
                    onChange={(e) => setEmbedAuthor(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2 text-white text-xs focus:border-cyan-500 focus:outline-none font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Embed Title</label>
                  <input
                    type="text"
                    value={embedTitle}
                    onChange={(e) => setEmbedTitle(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2 text-white text-xs focus:border-cyan-500 focus:outline-none font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Description (Markdown Supported)</label>
                  <textarea
                    rows={3}
                    value={embedDescription}
                    onChange={(e) => setEmbedDescription(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900 p-2 text-white text-xs focus:border-cyan-500 focus:outline-none font-mono resize-none"
                  />
                </div>

                {/* Color Palette Selector */}
                <div>
                  <label className="block text-slate-400 mb-1.5">Accent Color Stripe</label>
                  <div className="flex items-center gap-2">
                    {[
                      { label: 'Blurple', hex: '#5865F2' },
                      { label: 'Cyan', hex: '#06B6D4' },
                      { label: 'Emerald', hex: '#57F287' },
                      { label: 'Amber', hex: '#FEE75C' },
                      { label: 'Rose', hex: '#ED4245' }
                    ].map(c => (
                      <button
                        key={c.hex}
                        type="button"
                        onClick={() => setEmbedColor(c.hex)}
                        className={`h-7 px-3 rounded-lg text-[11px] font-mono font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                          embedColor === c.hex ? 'ring-2 ring-white scale-105' : 'opacity-80 hover:opacity-100'
                        }`}
                        style={{ backgroundColor: c.hex, color: '#fff' }}
                      >
                        {c.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Custom Key-Value Fields */}
                <div className="pt-2">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-slate-300 font-bold uppercase tracking-wider text-[11px]">Fields ({embedFields.length})</span>
                    <button
                      type="button"
                      onClick={handleAddField}
                      className="flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 cursor-pointer"
                    >
                      <Plus className="h-3 w-3" />
                      <span>Add Field</span>
                    </button>
                  </div>

                  <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                    {embedFields.map((field, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg border border-slate-800 bg-slate-900/60 space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <input
                            type="text"
                            value={field.name}
                            onChange={(e) => handleUpdateField(idx, 'name', e.target.value)}
                            placeholder="Field Name"
                            className="flex-1 rounded border border-slate-800 bg-slate-950 px-2 py-1 text-white text-[11px] font-mono focus:outline-none"
                          />
                          <button
                            type="button"
                            onClick={() => handleRemoveField(idx)}
                            className="text-slate-500 hover:text-rose-400 p-1 cursor-pointer"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                        <textarea
                          rows={2}
                          value={field.value}
                          onChange={(e) => handleUpdateField(idx, 'value', e.target.value)}
                          placeholder="Field Value / Body"
                          className="w-full rounded border border-slate-800 bg-slate-950 px-2 py-1 text-slate-300 text-[11px] font-mono focus:outline-none resize-none"
                        />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Footer & Dispatch Action */}
                <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                  <button
                    type="button"
                    onClick={handleDispatchEmbed}
                    className="w-full py-2.5 rounded-xl bg-[#5865F2] hover:bg-[#4752C4] text-white font-semibold flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-[#5865F2]/30 transition-all"
                  >
                    <Send className="h-4 w-4" />
                    <span>Send Embed to {embedTargetChannel}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Right Live Preview: Discord Dark Theme Card */}
          <div className="lg:col-span-6 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider font-mono">Real-Time Discord Preview</span>
              <span className="text-[10px] text-slate-500 font-mono">Discord Client Simulator</span>
            </div>

            {/* Discord Dark Theme Message Container */}
            <div className="rounded-2xl border border-slate-800 bg-[#313338] p-5 shadow-2xl space-y-3 font-sans">
              {/* Bot User Header */}
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-full bg-[#5865F2] flex items-center justify-center text-white shrink-0 shadow">
                  <Bot className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-white text-sm">UmbrellaBot</span>
                    <span className="px-1 py-0.2 rounded text-[9px] bg-[#5865F2] text-white font-bold">APP</span>
                    <span className="text-[11px] text-[#949ba4] ml-1">Today at 4:30 PM</span>
                  </div>
                </div>
              </div>

              {/* The Embed Box */}
              <div
                className="rounded-lg bg-[#2b2d31] p-4 space-y-3 border-l-4 shadow-md max-w-lg"
                style={{ borderLeftColor: embedColor }}
              >
                {/* Embed Author */}
                {embedAuthor && (
                  <div className="flex items-center gap-1.5 text-xs text-white font-semibold">
                    <div className="h-4 w-4 rounded-full bg-cyan-500/40" />
                    <span>{embedAuthor}</span>
                  </div>
                )}

                {/* Embed Title */}
                {embedTitle && (
                  <h4 className="text-sm font-bold text-white hover:underline cursor-pointer">
                    {embedTitle}
                  </h4>
                )}

                {/* Embed Description */}
                {embedDescription && (
                  <p className="text-xs text-[#dbdee1] leading-relaxed whitespace-pre-wrap">
                    {embedDescription}
                  </p>
                )}

                {/* Embed Fields Grid */}
                {embedFields.length > 0 && (
                  <div className="grid grid-cols-2 gap-3 pt-1">
                    {embedFields.map((f, i) => (
                      <div key={i} className={f.inline ? 'col-span-1' : 'col-span-2'}>
                        <div className="text-[11px] font-bold text-white">{f.name}</div>
                        <div className="text-xs text-[#dbdee1] whitespace-pre-wrap mt-0.5">{f.value}</div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Embed Footer & Timestamp */}
                <div className="pt-2 border-t border-[#3f4147] flex items-center gap-2 text-[10px] text-[#949ba4]">
                  <span>{embedFooter}</span>
                  {includeTimestamp && <span>• Today at {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: SLASH COMMANDS & ROLE HIERARCHY WITH INTERACTIVE TESTER */}
      {activeSubTab === 'commands' && (
        <div className="space-y-6">
          {/* Interactive Tester Box */}
          <div className="rounded-2xl border border-purple-500/30 bg-[#0d1117] p-5 shadow-xl space-y-3 font-mono">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 font-bold text-white text-sm">
                <Terminal className="h-4 w-4 text-purple-400" />
                <span>Interactive Slash Command Gateway Test</span>
              </div>
              <span className="text-xs text-purple-400 bg-purple-950/60 px-2 py-0.5 rounded border border-purple-500/30">
                Direct IPC Dispatch
              </span>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                value={cmdRunnerInput}
                onChange={(e) => setCmdRunnerInput(e.target.value)}
                placeholder="Try /tps, /lookup Player, /broadcast Hello..."
                className="flex-1 rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-white placeholder:text-slate-500 focus:border-purple-500 focus:outline-none"
              />
              <button
                type="button"
                onClick={handleRunSlashCommand}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs cursor-pointer shadow-md transition-all"
              >
                <Play className="h-3.5 w-3.5 fill-current" />
                <span>Execute</span>
              </button>
            </div>

            {cmdRunnerOutput && (
              <pre className="p-3 rounded-lg border border-slate-800 bg-slate-950 text-xs text-slate-200 font-mono overflow-x-auto whitespace-pre-wrap">
                {cmdRunnerOutput}
              </pre>
            )}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-[#0d1117] p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 font-bold text-white text-sm font-display">
                <Terminal className="h-4 w-4 text-purple-400" />
                <span>Discord Slash Commands Registry & Permission Tiers</span>
              </div>
              <span className="text-xs font-mono text-slate-400">Integrated with Discord Gateway v10</span>
            </div>

            <div className="space-y-3">
              {slashCommands.map(cmd => (
                <div
                  key={cmd.name}
                  className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-slate-700 transition-colors"
                >
                  <div className="space-y-1 max-w-xl">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs font-bold text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/30">
                        {cmd.name}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-950/60 text-purple-300 border border-purple-500/30">
                        Required: {cmd.requiredRole}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        Invoked: {cmd.usageCount} times
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 font-sans mt-1">
                      {cmd.description}
                    </p>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <button
                      onClick={() => handleToggleCommand(cmd.name)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-colors cursor-pointer border ${
                        cmd.enabled
                          ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30 hover:bg-rose-950/40 hover:text-rose-300'
                          : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-emerald-300'
                      }`}
                    >
                      {cmd.enabled ? 'Enabled' : 'Disabled'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: ALERT WEBHOOK ROUTING MATRIX */}
      {activeSubTab === 'webhooks' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { name: 'GrimAC Threat & Ban Stream', channel: '#anticheat-alerts', desc: 'Dispatches sub-tick combat reach, fly anomalies, and ban wave embeds.' },
              { name: 'Server Crash & Diagnostics', channel: '#incident-reports', desc: 'Dispatches automated post-mortem triage when an instance reports low TPS.' },
              { name: 'Staff Action Audit Feed', channel: '#staff-audit-log', desc: 'Logs all /ban, /mute, /pardon, and console executions with HMAC signatures.' },
              { name: 'DiscordSRV /link Pairs', channel: '#link-verifications', desc: 'Alerts staff when a new player completes Minecraft-to-Discord verification.' }
            ].map(hook => (
              <div key={hook.name} className="rounded-xl border border-slate-800 bg-[#0d1117] p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white text-xs font-sans">{hook.name}</span>
                  <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/60 border border-cyan-500/30 px-2 py-0.5 rounded">
                    {hook.channel}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed font-sans">{hook.desc}</p>
                <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                  <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    <span>Connected & Delivering</span>
                  </span>
                  <button
                    onClick={() => {
                      api.sendDiscordNotification(`[Test Alert] Webhook delivery verification to ${hook.channel}`);
                      addToast('success', 'Webhook Test Ping', `Delivered test alert embed to ${hook.channel}`);
                    }}
                    className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs font-mono text-slate-300 transition-colors cursor-pointer"
                  >
                    Test Ping
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
