/**
 * CoreGatewaySettings Subcomponent
 * Manages FastAPI backend endpoint display and secret X-Admin-Key configuration.
 */

import React from 'react';
import { Server, Lock } from 'lucide-react';

interface CoreGatewaySettingsProps {
  coreUrl: string;
  adminKey: string;
  setAdminKey: (key: string) => void;
}

export const CoreGatewaySettings: React.FC<CoreGatewaySettingsProps> = ({
  coreUrl,
  adminKey,
  setAdminKey,
}) => {
  return (
    <div className="rounded-xl border border-[#141d3d] bg-[#060b1c] p-5 shadow-xl space-y-4 font-mono text-xs">
      <div className="flex items-center gap-2 border-b border-[#141d3d] pb-3">
        <Server className="h-4 w-4 text-indigo-400" />
        <h2 className="font-bold text-white uppercase text-sm font-sans">Core Connection & Gateway</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

        <div>
          <label className="block text-slate-300 mb-1 font-sans font-medium flex items-center gap-1.5">
            <Lock className="h-3 w-3 text-indigo-400" />
            <span>Admin API Key (X-Admin-Key)</span>
          </label>
          <input
            type="password"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            placeholder="Enter secret admin key to override session..."
            className="w-full rounded-lg border border-[#141d3d] bg-[#02040a] p-2.5 text-white focus:border-indigo-500 focus:outline-none"
          />
          <p className="text-[10px] text-slate-500 mt-1">
            Enables full administrative bypass and server console access.
          </p>
        </div>
      </div>
    </div>
  );
};
