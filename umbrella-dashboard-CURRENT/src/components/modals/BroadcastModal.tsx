import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import {
  Megaphone,
  X,
  Send,
  MessageSquare,
  Bell,
  Sparkles,
  Server,
  Gamepad2,
  Globe,
  Radio,
  Volume2
} from 'lucide-react';

interface BroadcastModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export type BroadcastDestination = 'MINECRAFT_ONLY' | 'DISCORD_ONLY' | 'BOTH';

export const BroadcastModal: React.FC<BroadcastModalProps> = ({ isOpen, onClose }) => {
  const { broadcastGlobalMessage, servers } = useDashboard();
  const [message, setMessage] = useState('');
  const [destination, setDestination] = useState<BroadcastDestination>('BOTH');
  const [targetScope, setTargetScope] = useState<'ALL_NODES' | 'PROXY_ONLY' | 'GAME_NODES'>('ALL_NODES');
  const [includeTitleDisplay, setIncludeTitleDisplay] = useState(true);
  const [discordChannel, setDiscordChannel] = useState('#📢・announcements');
  const [soundAlert, setSoundAlert] = useState(true);

  if (!isOpen) return null;

  const totalPlayers = servers.reduce((acc, s) => acc + s.playersCount, 0);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    broadcastGlobalMessage(message.trim(), {
      destination,
      postToMinecraft: destination === 'MINECRAFT_ONLY' || destination === 'BOTH',
      postToDiscord: destination === 'DISCORD_ONLY' || destination === 'BOTH',
      discordChannel,
      targetScope,
      flashTitle: includeTitleDisplay,
      playChime: soundAlert
    });
    onClose();
    setMessage('');
  };

  const templates = [
    { text: '⚠️ Server maintenance in 15 minutes! Please finish your games and save items.', category: 'Maintenance' },
    { text: '🎉 Double XP & 2x Drop Multiplier is now live across all nodes!', category: 'Event' },
    { text: '🛡️ Anticheat engine updated to GrimAC v3.44. Clean competitive play enforced.', category: 'Security' },
    { text: '⚡ New Nether Dragon Boss event starting at warp /boss in 5 minutes!', category: 'Gameplay' },
    { text: '🏆 Season 4 Leaderboards have concluded. Rewards distributed to top 10 clans!', category: 'Season' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 font-sans animate-in fade-in duration-150">
      <div className="w-full max-w-xl rounded-2xl border border-slate-700 bg-[#0d1117] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/90 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <Megaphone className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white font-display">Broadcast Global Network Alert</h2>
              <p className="text-xs text-slate-400 font-sans">
                Dispatch announcements to Minecraft cluster, Discord channels, or both simultaneously
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 font-sans overflow-y-auto flex-1 text-xs">
          {/* Target Destination Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
              <Radio className="h-3.5 w-3.5 text-cyan-400" />
              <span>Broadcast Destination Target *</span>
            </label>
            
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {/* Option 1: Minecraft In-Game Only */}
              <button
                type="button"
                onClick={() => setDestination('MINECRAFT_ONLY')}
                className={`p-3 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between gap-1.5 ${
                  destination === 'MINECRAFT_ONLY'
                    ? 'border-emerald-500/60 bg-emerald-950/30 text-white shadow-sm ring-1 ring-emerald-500/40'
                    : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <Gamepad2 className={`h-4 w-4 ${destination === 'MINECRAFT_ONLY' ? 'text-emerald-400' : 'text-slate-500'}`} />
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                    {totalPlayers} online
                  </span>
                </div>
                <div>
                  <div className="font-bold text-xs text-white">In-Game Server</div>
                  <div className="text-[10px] text-slate-400">Minecraft cluster only</div>
                </div>
              </button>

              {/* Option 2: Discord Only */}
              <button
                type="button"
                onClick={() => setDestination('DISCORD_ONLY')}
                className={`p-3 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between gap-1.5 ${
                  destination === 'DISCORD_ONLY'
                    ? 'border-[#5865F2]/70 bg-[#5865F2]/20 text-white shadow-sm ring-1 ring-[#5865F2]/50'
                    : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <MessageSquare className={`h-4 w-4 ${destination === 'DISCORD_ONLY' ? 'text-[#8ea1e1]' : 'text-slate-500'}`} />
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-[#8ea1e1]">
                    Webhook
                  </span>
                </div>
                <div>
                  <div className="font-bold text-xs text-white">Discord Channel</div>
                  <div className="text-[10px] text-slate-400">Community channels only</div>
                </div>
              </button>

              {/* Option 3: Both */}
              <button
                type="button"
                onClick={() => setDestination('BOTH')}
                className={`p-3 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between gap-1.5 ${
                  destination === 'BOTH'
                    ? 'border-cyan-500/70 bg-cyan-950/40 text-white shadow-sm ring-1 ring-cyan-500/50'
                    : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <Globe className={`h-4 w-4 ${destination === 'BOTH' ? 'text-cyan-400' : 'text-slate-500'}`} />
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                    Dual Relay
                  </span>
                </div>
                <div>
                  <div className="font-bold text-xs text-white">Both (All Channels)</div>
                  <div className="text-[10px] text-slate-400">In-game + Discord sync</div>
                </div>
              </button>
            </div>
          </div>

          {/* Broadcast Message Input */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Announcement Content *</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              placeholder="Enter global broadcast text..."
              required
              className="w-full rounded-xl border border-slate-700 bg-slate-900 p-3 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
            />
          </div>

          {/* Quick Announcement Templates */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-amber-400" />
              <span>Preset Templates</span>
            </label>
            <div className="space-y-1.5 max-h-28 overflow-y-auto pr-1">
              {templates.map((t, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setMessage(t.text)}
                  className="w-full text-left rounded-lg border border-slate-800 bg-slate-900/60 p-2 text-[11px] text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 hover:bg-cyan-950/20 transition-all truncate cursor-pointer font-mono flex items-center justify-between"
                >
                  <span className="truncate mr-2">{t.text}</span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-sans shrink-0">{t.category}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Discord Specific Options (If Discord or Both) */}
          {(destination === 'DISCORD_ONLY' || destination === 'BOTH') && (
            <div className="rounded-xl border border-[#5865F2]/40 bg-[#5865F2]/10 p-3.5 space-y-2.5 animate-in fade-in duration-100">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-semibold text-white">
                  <MessageSquare className="h-4 w-4 text-[#8ea1e1]" />
                  <span>Discord Channel Configuration</span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#5865F2]/30 text-[#c2ccf8]">
                  DiscordSRV Connected
                </span>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <span className="text-[11px] text-slate-300 shrink-0">Channel:</span>
                <select
                  value={discordChannel}
                  onChange={(e) => setDiscordChannel(e.target.value)}
                  className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-white focus:border-[#5865F2] focus:outline-none font-mono cursor-pointer"
                >
                  <option value="#📢・announcements">#📢・announcements</option>
                  <option value="#🚨・server-alerts">#🚨・server-alerts</option>
                  <option value="#🎉・events-and-giveaways">#🎉・events-and-giveaways</option>
                  <option value="#💬・global-chat-bridge">#💬・global-chat-bridge</option>
                </select>
              </div>
            </div>
          )}

          {/* Minecraft Specific Options (If Minecraft or Both) */}
          {(destination === 'MINECRAFT_ONLY' || destination === 'BOTH') && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3.5 space-y-3 animate-in fade-in duration-100">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <Server className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Minecraft Node Scope</span>
                </label>
              </div>

              <select
                value={targetScope}
                onChange={(e) => setTargetScope(e.target.value as any)}
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none font-mono cursor-pointer"
              >
                <option value="ALL_NODES">All Network Nodes & Proxies</option>
                <option value="GAME_NODES">Game Servers Only (Survival, Skyblock, Bedwars)</option>
                <option value="PROXY_ONLY">Velocity / BungeeCord Proxies Only</option>
              </select>

              <div className="flex flex-col sm:flex-row sm:items-center gap-3 pt-1">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={includeTitleDisplay}
                    onChange={(e) => setIncludeTitleDisplay(e.target.checked)}
                    className="h-3.5 w-3.5 rounded border-slate-700 bg-slate-900 text-cyan-500 cursor-pointer"
                  />
                  <span className="text-xs text-slate-300">Screen Title Header (Actionbar + Subtitle)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={soundAlert}
                    onChange={(e) => setSoundAlert(e.target.checked)}
                    className="h-3.5 w-3.5 rounded border-slate-700 bg-slate-900 text-cyan-500 cursor-pointer"
                  />
                  <span className="text-xs text-slate-300 flex items-center gap-1">
                    <Volume2 className="h-3 w-3 text-amber-400" />
                    Chime Sound
                  </span>
                </label>
              </div>
            </div>
          )}

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2 text-xs font-semibold text-white hover:from-cyan-500 hover:to-blue-500 transition-all shadow-md cursor-pointer"
            >
              <Send className="h-3.5 w-3.5" />
              <span>
                {destination === 'MINECRAFT_ONLY' && 'Broadcast to In-Game'}
                {destination === 'DISCORD_ONLY' && 'Post to Discord'}
                {destination === 'BOTH' && 'Broadcast to All Channels'}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
