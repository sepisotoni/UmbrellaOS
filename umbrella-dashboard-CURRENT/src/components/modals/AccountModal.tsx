import React from 'react';
import { 
  X, 
  ShieldCheck, 
  LogOut, 
  User, 
  Key, 
  ExternalLink,
  Lock,
  CheckCircle2,
  Cpu
} from 'lucide-react';
import { useDashboard } from '../../context/DashboardContext';

export const AccountModal: React.FC = () => {
  const { 
    accountModalOpen, 
    setAccountModalOpen, 
    currentUser, 
    setCurrentUser, 
    setActiveTab, 
    backendStatus,
    backendLatencyMs,
    addToast
  } = useDashboard();

  if (!accountModalOpen) return null;

  const handleLogout = () => {
    setCurrentUser(null);
    setAccountModalOpen(false);
    setActiveTab('login');
    addToast('info', 'Logged Out', 'Staff session terminated. Redirected to /login gateway.');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#0d1117] shadow-2xl p-6 relative overflow-hidden font-sans">
        {/* Top Edge Cyan Glow */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent" />

        {/* Close Button */}
        <button
          onClick={() => setAccountModalOpen(false)}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
          <div className="h-10 w-10 rounded-xl bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 flex items-center justify-center font-bold font-mono text-sm">
            {currentUser?.username ? currentUser.username.charAt(0).toUpperCase() : <User className="h-5 w-5" />}
          </div>
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <span>{currentUser?.username || 'Guest Staff Operator'}</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-cyan-950/90 text-cyan-300 border border-cyan-500/30">
                {currentUser?.role || 'Operator'}
              </span>
            </h2>
            <p className="text-xs text-slate-400 font-mono">
              {currentUser?.email || 'Authenticated Session'}
            </p>
          </div>
        </div>

        {/* Session Details */}
        <div className="py-4 space-y-3 font-mono text-xs">
          <div className="p-3 rounded-xl border border-slate-800/80 bg-[#090d13] space-y-2">
            <div className="flex justify-between text-slate-400">
              <span>Discord ID:</span>
              <span className="text-slate-200 font-semibold">{currentUser?.discordId || 'Linked'}</span>
            </div>
            {currentUser?.linkedMinecraftUsername && (
              <div className="flex justify-between text-slate-400">
                <span>Minecraft IGN:</span>
                <span className="text-cyan-300 font-semibold">{currentUser.linkedMinecraftUsername}</span>
              </div>
            )}
            <div className="flex justify-between text-slate-400">
              <span>Backend Link:</span>
              <span className="text-emerald-400 font-medium">
                {backendStatus === 'connected' ? `ONLINE (${backendLatencyMs || 2}ms)` : 'Active'}
              </span>
            </div>
          </div>

          <div>
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block mb-2">
              Assigned Permissions ({currentUser?.permissions?.length || 0})
            </span>
            <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto pr-1">
              {(currentUser?.permissions || ['servers.view', 'moderation.ban', 'settings.admin']).map((perm) => (
                <span
                  key={perm}
                  className="px-2 py-0.5 rounded-md border border-slate-800 bg-slate-900/90 text-[10px] text-slate-300 font-mono"
                >
                  {perm}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="pt-3 border-t border-slate-800 flex gap-2">
          <button
            onClick={() => {
              setAccountModalOpen(false);
              setActiveTab('login');
            }}
            className="flex-1 py-2.5 px-4 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono font-medium transition-colors flex items-center justify-center gap-2 cursor-pointer"
          >
            <Key className="h-3.5 w-3.5 text-cyan-400" />
            <span>Switch Role / Key</span>
          </button>

          <button
            onClick={handleLogout}
            className="py-2.5 px-4 rounded-xl border border-rose-500/40 bg-rose-950/30 hover:bg-rose-950/60 text-rose-300 text-xs font-mono font-medium transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </div>
  );
};
