import React from 'react';
import { ShieldX, LogOut, Mail, ArrowLeft } from 'lucide-react';
import { useDashboard } from '../../context/DashboardContext';
import { UmbrellaLogo } from '../common/UmbrellaLogo';

export const AccessDeniedView: React.FC = () => {
  const { currentUser, setCurrentUser, setAdminKey, setSessionToken, setActiveTab } = useDashboard();

  const handleLogout = () => {
    setCurrentUser(null);
    setAdminKey(null);
    setSessionToken(null);
    localStorage.removeItem('umbrella_session_token');
    localStorage.removeItem('umbrella_admin_key');
    localStorage.removeItem('umb_auth_user');
    setActiveTab('login');
  };

  return (
    <div className="min-h-screen w-screen bg-[#090b10] flex flex-col items-center justify-center px-4 relative overflow-hidden">

      {/* Background grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(220,38,38,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(220,38,38,0.03)_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />

      {/* Radial glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-rose-900/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 w-full max-w-md">

        {/* Logo */}
        <div className="flex justify-center mb-8">
          <UmbrellaLogo className="h-10 w-10 text-rose-500" />
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-rose-500/20 bg-[#0c0f16]/90 backdrop-blur-xl shadow-2xl shadow-rose-950/40 p-8 text-center space-y-6">

          {/* Icon */}
          <div className="flex justify-center">
            <div className="h-16 w-16 rounded-2xl bg-rose-950/50 border border-rose-500/30 flex items-center justify-center">
              <ShieldX className="h-8 w-8 text-rose-400" />
            </div>
          </div>

          {/* Heading */}
          <div className="space-y-2">
            <h1 className="text-xl font-bold text-white font-mono tracking-tight">
              ACCESS DENIED
            </h1>
            <p className="text-sm text-slate-400 leading-relaxed">
              Your account <span className="text-rose-400 font-mono font-semibold">@{currentUser?.username ?? 'unknown'}</span> does not have sufficient permissions to access the UmbrellaOS Control Panel.
            </p>
          </div>

          {/* Role badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/60 text-xs font-mono text-slate-400">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500 animate-pulse" />
            Role: <span className="text-slate-200 font-semibold">{currentUser?.role?.toUpperCase() ?? 'NONE'}</span>
            &nbsp;— Insufficient clearance
          </div>

          {/* Info box */}
          <div className="rounded-xl border border-amber-500/20 bg-amber-950/20 p-4 text-left space-y-1">
            <p className="text-xs font-semibold text-amber-300 font-mono">WHAT TO DO</p>
            <p className="text-xs text-slate-400 leading-relaxed">
              Contact a <span className="text-white font-semibold">superadmin</span> or <span className="text-white font-semibold">admin</span> to have your role elevated. Provide them with your Discord ID:
            </p>
            {currentUser?.discord_id && (
              <p className="text-xs font-mono text-cyan-400 mt-1 select-all">{currentUser.discord_id}</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-3 pt-1">
            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-sm font-semibold transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Sign Out
            </button>
            <a
              href="mailto:ops@umbrella-mc.net"
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/60 hover:bg-slate-700/60 text-slate-300 hover:text-white text-sm font-semibold transition-colors"
            >
              <Mail className="h-4 w-4" />
              Contact Admin
            </a>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-slate-600 mt-6 font-mono">
          UmbrellaOS · Restricted Zone · {new Date().getFullYear()}
        </p>
      </div>
    </div>
  );
};
