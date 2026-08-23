/**
 * MessagingTemplatesSettings Subcomponent
 * Manages Minecraft in-game player notifications, join greetings, and verification messages.
 */

import React from 'react';
import { MessageSquare, Info } from 'lucide-react';

interface MessagingTemplatesSettingsProps {
  verificationTemplate: string;
  setVerificationTemplate: (tpl: string) => void;
  greeterTemplate: string;
  setGreeterTemplate: (tpl: string) => void;
}

export const MessagingTemplatesSettings: React.FC<MessagingTemplatesSettingsProps> = ({
  verificationTemplate,
  setVerificationTemplate,
  greeterTemplate,
  setGreeterTemplate,
}) => {
  return (
    <div className="rounded-xl border border-[#141d3d] bg-[#060b1c] p-5 shadow-xl space-y-4 font-mono text-xs">
      <div className="flex items-center gap-2 border-b border-[#141d3d] pb-3">
        <MessageSquare className="h-4 w-4 text-emerald-400" />
        <h2 className="font-bold text-white uppercase text-sm font-sans">
          Messaging & Announcement Templates
        </h2>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-slate-300 mb-1 font-sans font-medium">
            Verification Prompt Message (Shown to Unlinked Players)
          </label>
          <input
            type="text"
            value={verificationTemplate}
            onChange={(e) => setVerificationTemplate(e.target.value)}
            className="w-full rounded-lg border border-[#141d3d] bg-[#02040a] p-2.5 text-white focus:border-indigo-500 focus:outline-none"
          />
          <p className="text-[10px] text-slate-500 mt-1">
            Available tags: <code className="text-indigo-400">&#123;player&#125;</code>, <code className="text-indigo-400">&#123;code&#125;</code>, <code className="text-indigo-400">$discord_invite</code>
          </p>
        </div>

        <div>
          <label className="block text-slate-300 mb-1 font-sans font-medium">
            Player Join Greeter Message
          </label>
          <input
            type="text"
            value={greeterTemplate}
            onChange={(e) => setGreeterTemplate(e.target.value)}
            className="w-full rounded-lg border border-[#141d3d] bg-[#02040a] p-2.5 text-white focus:border-indigo-500 focus:outline-none"
          />
          <p className="text-[10px] text-slate-500 mt-1">
            Available tags: <code className="text-indigo-400">&#123;player&#125;</code>, <code className="text-indigo-400">&#123;server&#125;</code>, <code className="text-indigo-400">&#123;online_count&#125;</code>
          </p>
        </div>
      </div>
    </div>
  );
};
