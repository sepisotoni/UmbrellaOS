/**
 * DiscordIntegrationSettings Subcomponent
 * Manages Discord Guild parameters, verification channels, and $discord_invite link redirect routing.
 */

import React from 'react';
import { Bot, ExternalLink, HelpCircle, ArrowUpRight } from 'lucide-react';

interface DiscordIntegrationSettingsProps {
  discordGuildId: string;
  setDiscordGuildId: (id: string) => void;
  discordChannelId: string;
  setDiscordChannelId: (id: string) => void;
  discordInvite: string;
  setDiscordInvite: (url: string) => void;
}

export const DiscordIntegrationSettings: React.FC<DiscordIntegrationSettingsProps> = ({
  discordGuildId,
  setDiscordGuildId,
  discordChannelId,
  setDiscordChannelId,
  discordInvite,
  setDiscordInvite,
}) => {
  return (
    <div className="rounded-xl border border-[#141d3d] bg-[#060b1c] p-5 shadow-xl space-y-4 font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[#141d3d] pb-3">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-[#5865F2]" />
          <h2 className="font-bold text-white uppercase text-sm font-sans">
            Discord Integration & Redirect Routing
          </h2>
        </div>

        {discordInvite && (
          <a
            href={discordInvite}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[11px] font-sans text-indigo-400 hover:text-indigo-300 transition"
          >
            <span>Test Invite Link</span>
            <ArrowUpRight className="h-3 w-3" />
          </a>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-slate-300 mb-1 font-sans font-medium">Discord Guild (Server) ID</label>
          <input
            type="text"
            value={discordGuildId}
            onChange={(e) => setDiscordGuildId(e.target.value)}
            placeholder="e.g. 109283746581928374"
            className="w-full rounded-lg border border-[#141d3d] bg-[#02040a] p-2.5 text-white focus:border-indigo-500 focus:outline-none"
          />
          <p className="text-[10px] text-slate-500 mt-1">
            Required for staff role sync and bot guild presence.
          </p>
        </div>

        <div>
          <label className="block text-slate-300 mb-1 font-sans font-medium">Verification Channel ID</label>
          <input
            type="text"
            value={discordChannelId}
            onChange={(e) => setDiscordChannelId(e.target.value)}
            placeholder="e.g. 109283746581928375"
            className="w-full rounded-lg border border-[#141d3d] bg-[#02040a] p-2.5 text-white focus:border-indigo-500 focus:outline-none"
          />
          <p className="text-[10px] text-slate-500 mt-1">
            Channel where the Umbrella bot listens for `/verify` slash commands.
          </p>
        </div>
      </div>

      {/* Community Discord Invite URL ($discord_invite) */}
      <div className="rounded-xl border border-indigo-900/30 bg-[#02040a] p-4 space-y-3">
        <div>
          <label className="block text-slate-200 font-sans font-bold text-xs mb-1">
            Community Discord Server Invite URL (<code className="text-indigo-400 font-mono">$discord_invite</code>)
          </label>
          <input
            type="text"
            value={discordInvite}
            onChange={(e) => setDiscordInvite(e.target.value)}
            placeholder="e.g. https://discord.gg/umbrella or https://discord.gg/your-server"
            className="w-full rounded-lg border border-[#141d3d] bg-[#060b1c] p-2.5 text-white focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <div className="text-[11px] font-sans text-slate-400 space-y-1.5 pt-1 border-t border-[#141d3d]/50">
          <div className="font-semibold text-indigo-300 flex items-center gap-1.5">
            <HelpCircle className="h-3.5 w-3.5 text-indigo-400" />
            <span>How this redirect parameter is applied:</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-slate-400 pl-1 text-[11px]">
            <li>
              <strong className="text-slate-300">Login Page Footer:</strong> The &quot;Discord Server&quot; button opens this exact invite link.
            </li>
            <li>
              <strong className="text-slate-300">In-Game Chat Prompts:</strong> Replaces <code className="text-indigo-300">$discord_invite</code> and <code className="text-indigo-300">&#123;discord_invite&#125;</code> in Minecraft chat broadcasts and join messages.
            </li>
            <li>
              <strong className="text-slate-300">Ban Appeals &amp; Kicks:</strong> Included in disconnect screens when directing unverified or disciplined players to community support.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
