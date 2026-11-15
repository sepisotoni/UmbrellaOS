/**
 * CoreGatewaySettings Subcomponent
 * Manages FastAPI backend endpoint display and secret X-Admin-Key configuration.
 */

import React from 'react';
import { Server, ShieldCheck } from 'lucide-react';

interface CoreGatewaySettingsProps {
  coreUrl: string;
}

export const CoreGatewaySettings: React.FC<CoreGatewaySettingsProps> = ({ coreUrl }) => {
  return (
    <div className="rounded-xl border border-[#141d3d] bg-[#060b1c] p-5 shadow-xl space-y-4 font-mono text-xs">
      <div className="flex items-center gap-2 border-b border-[#141d3d] pb-3">
        <Server className="h-4 w-4 text-indigo-400" />
        <h2 className="font-bold text-white uppercase text-sm font-sans">Core Connection & Gateway</h2>
      </div>

      <div className="grid grid-cols-1 gap-4">
        <div>
          <label className="block text-slate-300 mb-1 font-sans font-medium">FastAPI Backend Endpoint</label>
          <input
            type="text"
            value={coreUrl}
            disabled
            className="w-full rounded-lg border border-[#141d3d] bg-[#02040a] p-2.5 text-slate-400 cursor-not-allowed opacity-80"
          />
          <p className="text-[10px] text-slate-500 mt-1">Configured via environment variable VITE_UMBRELLA_CORE_URL</p>
        </div>

        <p className="flex items-center gap-2 text-[10px] text-emerald-300/80">
          <ShieldCheck className="h-3.5 w-3.5" />
          Dashboard requests use Supabase Auth and server-managed permissions. Core service keys are never stored in the browser.
        </p>
      </div>
    </div>
  );
};
