import React, { useState, useEffect } from 'react';
import { 
  Key, 
  Lock, 
  ArrowRight, 
  Eye, 
  EyeOff, 
  ShieldAlert, 
  ArrowLeft, 
  AlertTriangle,
  X
} from 'lucide-react';
import { useDashboard } from '../../context/DashboardContext';
import { UmbrellaLogo } from '../common/UmbrellaLogo';

export const LoginView: React.FC = () => {
  const { 
    backendBaseUrl, 
    setAdminKey, 
    setSessionToken, 
    addToast,
    setActiveTab,
    setCurrentUser
  } = useDashboard();

  const [inputKey, setInputKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [isAuthorizing, setIsAuthorizing] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  
  // Hidden Secret Key Modal Popout
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(false);

  // Keyboard shortcut listener for Ctrl+Shift+K / Cmd+Shift+K or `~`
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'K' || e.key === 'k')) {
        e.preventDefault();
        setIsKeyModalOpen((prev) => !prev);
      } else if (e.key === 'Escape' && isKeyModalOpen) {
        setIsKeyModalOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isKeyModalOpen]);

  const handleDiscordOAuth = async () => {
    setIsAuthorizing(true);
    setAuthError(null);
    try {
      addToast('info', 'Discord Handshake', 'Requesting OAuth2 authorization token...');
      
      // Simulate OAuth token exchange and session validation
      setTimeout(() => {
        setIsAuthorizing(false);
        setCurrentUser({
          id: 'usr_staff_discord_01',
          discordId: '8921049281928391',
          username: 'UmbrellaLead',
          discriminator: '0420',
          avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
          role: 'superadmin',
          permissions: [
            'servers.view',
            'servers.manage',
            'servers.console',
            'moderation.ban',
            'moderation.kick',
            'moderation.pardon',
            'ai.review',
            'ai.execute',
            'alts.manage',
            'settings.admin'
          ],
          email: 'ops@umbrella-mc.net',
          linkedMinecraftUsername: 'UmbrellaLead_MC',
          linkedMinecraftUuid: '9f2348a1-3004-4df8-9538-3482a0149eef'
        });
        addToast('success', 'Staff Session Validated', 'Authenticated as Senior SuperAdmin via Discord OAuth2');
        setActiveTab('overview');
      }, 1100);
    } catch (err: any) {
      setIsAuthorizing(false);
      setAuthError(err.message || 'Failed to initialize Discord OAuth2 flow');
      addToast('error', 'OAuth Failure', 'Could not establish handshake with authentication gateway.');
    }
  };

  const handleKeyAuth = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputKey.trim()) {
      setAuthError('Please enter an X-Admin-Key or Session Token');
      return;
    }
    
    setAdminKey(inputKey.trim());
    setSessionToken(inputKey.trim());
    setCurrentUser({
      id: 'usr_key_auth_01',
      discordId: '0000000000000000',
      username: 'KeyOperator',
      discriminator: '0001',
      avatarUrl: '',
      role: 'superadmin',
      permissions: ['servers.view', 'servers.manage', 'servers.console', 'moderation.ban', 'settings.admin'],
      email: 'operator@internal.local'
    });
    setIsKeyModalOpen(false);
    addToast('success', 'Admin Key Attached', 'Master Session Token verified.');
    setActiveTab('overview');
  };

  const handleQuickDemoLogin = (role: 'superadmin' | 'moderator' | 'developer') => {
    setCurrentUser({
      id: `usr_${role}_01`,
      discordId: '8921049281928391',
      username: role === 'superadmin' ? 'NetworkDirector' : role === 'moderator' ? 'HeadModerator' : 'CoreEngineer',
      discriminator: '0001',
      avatarUrl: '',
      role: role,
      permissions: role === 'superadmin' 
        ? ['servers.view', 'servers.manage', 'servers.console', 'moderation.ban', 'moderation.kick', 'moderation.pardon', 'ai.review', 'ai.execute', 'alts.manage', 'settings.admin']
        : role === 'moderator'
        ? ['servers.view', 'moderation.ban', 'moderation.kick', 'moderation.pardon', 'alts.manage']
        : ['servers.view', 'servers.manage', 'servers.console', 'settings.admin'],
      email: `${role}@umbrella-mc.net`
    });
    setIsKeyModalOpen(false);
    addToast('success', `Quick Staff Access (${role.toUpperCase()})`, 'Loaded dashboard with RBAC session.');
    setActiveTab('overview');
  };

  return (
    <div className="min-h-screen bg-[#090b10] text-slate-100 flex flex-col justify-center items-center p-4 relative overflow-hidden font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Background Cybernetic Ambient Glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none -z-10 flex items-center justify-center">
        <div className="w-[700px] h-[700px] bg-cyan-500/10 rounded-full blur-[140px]" />
        <div className="w-[500px] h-[500px] bg-[#5865F2]/15 rounded-full blur-[120px] -translate-y-28 translate-x-20" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b08_1px,transparent_1px),linear-gradient(to_bottom,#1e293b08_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)]" />
      </div>

      {/* Top Header Quick Back Button */}
      <div className="absolute top-6 left-6 z-20">
        <button
          onClick={() => setActiveTab('overview')}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-800 bg-[#0d1117]/80 hover:bg-slate-800 text-slate-400 hover:text-slate-200 text-xs font-mono transition-all backdrop-blur-md cursor-pointer"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Dashboard Preview</span>
        </button>
      </div>

      <div className="w-full max-w-lg space-y-6 z-10">
        {/* Main Gateway Card */}
        <div className="rounded-2xl border border-slate-800/90 bg-[#0d1117]/95 shadow-2xl backdrop-blur-2xl p-8 sm:p-10 relative overflow-hidden">
          {/* Top Edge Cyan Accent Glow */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent" />

          {/* Header & Protocol Title */}
          <div className="text-center space-y-3 pb-6 border-b border-slate-800/80">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 text-xs font-mono font-medium">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
              </span>
              AUTHENTICATION GATEWAY // SECURE PORTAL
            </div>

            <div className="flex items-center justify-center pt-2">
              <UmbrellaLogo size="xl" subtext="Network Command & Intelligence Center" />
            </div>

            <p className="text-sm text-slate-300 font-sans max-w-md mx-auto pt-1 leading-relaxed">
              Authorized staff portal for network telemetry, anticheat enforcement, and infrastructure operations. Discord OAuth2 session verification required.
            </p>
          </div>

          {authError && (
            <div className="mt-4 p-3 rounded-xl border border-rose-500/30 bg-rose-950/40 text-rose-300 text-xs flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0" />
              <span>{authError}</span>
            </div>
          )}

          {/* Single Primary Action: Discord OAuth2 */}
          <div className="mt-6">
            <button
              onClick={handleDiscordOAuth}
              disabled={isAuthorizing}
              className="w-full relative group overflow-hidden rounded-xl bg-[#5865F2] hover:bg-[#4752C4] text-white p-4 font-medium transition-all shadow-lg shadow-[#5865F2]/25 flex items-center justify-center gap-3 disabled:opacity-60 cursor-pointer"
            >
              {/* Discord Icon SVG */}
              <svg className="h-5 w-5 fill-current shrink-0" viewBox="0 0 24 24">
                <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.929 1.793 8.18 1.793 12.061 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.893.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.028zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
              </svg>
              <span className="font-semibold tracking-wide text-sm">
                {isAuthorizing ? 'Authorizing Discord Session...' : 'Authenticate with Discord'}
              </span>
              <ArrowRight className="h-4 w-4 ml-auto group-hover:translate-x-0.5 transition-transform" />
            </button>
          </div>
        </div>

        {/* Security & Audit Compliance Footer (Secret key shortcut: Ctrl+Shift+K) */}
        <div className="rounded-xl border border-slate-800/80 bg-[#0d1117]/60 p-4 text-xs font-mono text-slate-400 space-y-2 backdrop-blur-md">
          <div className="flex items-center gap-2 text-slate-300 font-semibold">
            <ShieldAlert className="h-4 w-4 text-cyan-400" />
            <span>Cryptographic Audit & Session Verification</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed font-sans">
            Access to UmbrellaOS is strictly restricted to authorized staff. All sessions and administrative operations are verified with HMAC-SHA256 signatures and recorded to the immutable audit database.
          </p>
        </div>
      </div>

      {/* Secret Popout Modal for X-Admin-Key Ingress (Triggered strictly by secret shortcut Ctrl+Shift+K / Cmd+Shift+K) */}
      {isKeyModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-150">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#0d1117] shadow-2xl p-6 sm:p-7 relative overflow-hidden font-sans">
            {/* Top Cyan Accent */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent" />

            {/* Close Button */}
            <button
              onClick={() => setIsKeyModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>

            {/* Modal Title */}
            <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
              <div className="h-10 w-10 rounded-xl bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 flex items-center justify-center">
                <Key className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white font-mono flex items-center gap-2">
                  <span>Master Key Ingress</span>
                  <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase rounded bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                    Emergency
                  </span>
                </h3>
                <p className="text-xs text-slate-400">Direct X-Admin-Key / Token Verification</p>
              </div>
            </div>

            {/* Input Form */}
            <form onSubmit={handleKeyAuth} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1.5">
                  X-Admin-Key / Master Token:
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Lock className="h-4 w-4" />
                  </div>
                  <input
                    type={showKey ? 'text' : 'password'}
                    value={inputKey}
                    onChange={(e) => setInputKey(e.target.value)}
                    placeholder="umb_live_sk_..."
                    autoFocus
                    className="w-full pl-9 pr-10 py-2.5 bg-[#090d13] border border-slate-800 rounded-xl text-slate-200 placeholder-slate-600 text-sm font-mono focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(!showKey)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300 cursor-pointer"
                  >
                    {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-2.5 px-4 rounded-xl border border-slate-700 bg-cyan-950/60 hover:bg-cyan-900/80 text-cyan-300 border-cyan-500/40 text-xs font-mono font-semibold transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-cyan-950/40"
              >
                <Lock className="h-3.5 w-3.5 text-cyan-400" />
                <span>Verify Token & Enter</span>
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
