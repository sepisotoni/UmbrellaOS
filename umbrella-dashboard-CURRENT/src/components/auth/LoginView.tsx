import React, { useState, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { api } from '../../lib/api';
import {
  BrandLogo,
  BrandLogoVariant,
  LogoRenderMode,
  BRAND_DEFINITIONS,
} from '../common/BrandLogos';
import { AtmosphericBackground } from '../common/AtmosphericBackground';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  Key,
  Shield,
  LogIn,
  AlertCircle,
  Lock,
  ArrowRight,
  ExternalLink,
  Eye,
  EyeOff,
  HelpCircle,
  Code2,
  Image as ImageIcon,
  Command,
} from 'lucide-react';

export const LoginView: React.FC = () => {
  const {
    setSessionToken,
    setAdminKey,
    setCurrentUser,
    setActiveTab,
    addToast,
    isDisconnected,
    showDoodles,
    doodleOpacity,
    discordInvite,
  } = useDashboard();

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Direct Token / Admin Key or User input
  const [tokenInput, setTokenInput] = useState('');
  const [usernameInput, setUsernameInput] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isTokenAuth, setIsTokenAuth] = useState(false);

  // Default brand for login
  const [selectedBrand] = useState<BrandLogoVariant>('os');

  // Secret Staff Bypass Key and Click Triggers
  const [logoClickCount, setLogoClickCount] = useState(0);

  // Keyboard shortcut listener for Ctrl+Shift+K / Cmd+Shift+K (Global Capture)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isKKey =
        e.key === 'K' ||
        e.key === 'k' ||
        e.code === 'KeyK' ||
        e.keyCode === 75 ||
        e.which === 75;

      // Catch Ctrl+Shift+K, Cmd+Shift+K, or Alt+Shift+K
      const isModifierActive = (e.ctrlKey || e.metaKey || e.altKey) && e.shiftKey;

      if (isModifierActive && isKKey) {
        e.preventDefault();
        e.stopPropagation();
        setIsTokenAuth((prev) => !prev);
        setErrorMessage(null);
      } else if (e.key === 'Escape' && isTokenAuth) {
        setIsTokenAuth(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown, { capture: true });
    document.addEventListener('keydown', handleKeyDown, { capture: true });
    return () => {
      window.removeEventListener('keydown', handleKeyDown, { capture: true });
      document.removeEventListener('keydown', handleKeyDown, { capture: true });
    };
  }, [isTokenAuth]);

  // Secret multi-click trigger on emblem (3 clicks within 1.5 seconds)
  const handleLogoClick = () => {
    setLogoClickCount((prev) => {
      const next = prev + 1;
      if (next >= 3) {
        setIsTokenAuth((curr) => !curr);
        setErrorMessage(null);
        return 0;
      }
      return next;
    });
  };

  useEffect(() => {
    if (logoClickCount > 0) {
      const timer = setTimeout(() => setLogoClickCount(0), 1500);
      return () => clearTimeout(timer);
    }
  }, [logoClickCount]);

  const handleDiscordLogin = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const redirectUri = `${window.location.origin}/`;
      const res = await api.discordAuthorize(redirectUri);
      if (res.authorize_url) {
        window.location.href = res.authorize_url;
      } else {
        throw new Error('No authorization URL returned from Core');
      }
    } catch (err: any) {
      setErrorMessage(
        err.message || 'Failed to initiate Discord OAuth flow. Check Core connection.'
      );
      setIsLoading(false);
    }
  };

  const handleDirectAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    const cred = tokenInput.trim();
    if (!cred) return;

    setIsLoading(true);
    setErrorMessage(null);

    try {
      // First try as a session token (Bearer token)
      api.setSessionToken(cred);
      try {
        const user = await api.getMe();
        setSessionToken(cred);
        setCurrentUser(user);
        addToast({
          type: 'success',
          title: 'Session Authenticated',
          message: `Logged in as ${user.username}`,
        });
        setActiveTab('overview');
        return;
      } catch {
        // Bearer token failed — try as X-Admin-Key
        api.setSessionToken(null);
        api.setAdminKey(cred);
        try {
          // Verify against a protected endpoint. getHealth() is public (always 200)
          // so we must hit an authed route to actually validate the key.
          await api.getRoles();
        } catch {
          api.setAdminKey(null);
          throw new Error('Invalid Session Token or Admin Key.');
        }

        // Key accepted — persist via context so isAuthenticated becomes true
        setAdminKey(cred);
        const fallbackUser = {
          id: 'admin-key-holder',
          discord_id: '0',
          username: usernameInput.trim() || 'Administrator (Key)',
          email: null,
          avatar_url: null,
          role_id: 'owner',
          role: 'owner',
          permissions: ['*'],
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        localStorage.setItem('umbrella_admin_user', JSON.stringify(fallbackUser));
        setCurrentUser(fallbackUser);
        addToast({
          type: 'success',
          title: 'Admin Key Verified',
          message: 'Authenticated with administrative privileges.',
        });
        setActiveTab('overview');
        return;
      }
    } catch (err: any) {
      api.setSessionToken(null);
      api.setAdminKey(null);
      setErrorMessage(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      id="umbrella-login-page"
      className="min-h-screen w-full relative flex flex-col items-center justify-center p-4 text-slate-100 font-sans select-none overflow-hidden"
    >
      {/* 1. Atmospheric Heaven Cloud-Style Night Sky & WhatsApp-Style Scrambled Doodle Background */}
      <AtmosphericBackground
        variant="login"
        showDoodles={showDoodles}
        doodleOpacity={doodleOpacity}
        showStars={true}
        showHorizon={true}
      />

      {/* Top Banner */}
      <div className="z-10 w-full max-w-md space-y-4 mb-2">
        <DisconnectedBanner />
      </div>

      {/* 2. Main Centered Login Card */}
      <div className="z-10 w-full max-w-[420px] rounded-2xl border border-[#141d3d] bg-[#060b1c]/90 p-8 shadow-2xl backdrop-blur-xl transition-all">
        {/* Centered Brand Emblem & Heading */}
        <div className="text-center space-y-3 mb-6">
          <div
            className="flex justify-center items-center cursor-default select-none"
            onClick={handleLogoClick}
            title=""
          >
            <BrandLogo
              variant={selectedBrand}
              size="xl"
              renderMode="vector"
              showWordmark={false}
              showBadge={false}
              glow={true}
            />
          </div>

          <div className="flex flex-col items-center justify-center text-center pt-1">
            <div className="flex items-center justify-center gap-1 font-bold text-2xl tracking-tight text-white font-sans">
              <span>Umbrella</span>
              <span className="font-mono font-black text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-sky-400 to-cyan-400">
                OS
              </span>
            </div>
            <p className="text-xs text-indigo-300/80 mt-1 font-mono">
              {isTokenAuth
                ? 'Authorized Administrator & Staff Bypass'
                : 'Minecraft Multi-Node Fleet Operations & Sentinel Security'}
            </p>
          </div>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div
            id="login-error-alert"
            className="mb-5 flex items-start gap-2.5 rounded-xl border border-rose-500/40 bg-rose-950/60 p-3 text-xs text-rose-300"
          >
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-400" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Main Flow: Discord SSO (Default) vs Staff Key Mode (Ctrl+Shift+K) */}
        {!isTokenAuth ? (
          <div className="space-y-4">
            {/* Primary Discord SSO Button */}
            <button
              id="login-discord-button"
              onClick={handleDiscordLogin}
              disabled={isLoading || isDisconnected}
              className="w-full flex items-center justify-center gap-3 rounded-xl border border-[#5865F2]/50 bg-[#5865F2] hover:bg-[#4752C4] px-4 py-3 text-sm font-semibold text-white transition shadow-[0_0_20px_rgba(88,101,242,0.3)] active:scale-[0.98] disabled:opacity-50 cursor-pointer"
            >
              <LogIn className="h-4 w-4" />
              <span>{isLoading ? 'Connecting to Discord...' : 'Continue with Discord'}</span>
              <ExternalLink className="h-3.5 w-3.5 opacity-70" />
            </button>
          </div>
        ) : (
          /* Secret Staff Form (Revealed via Ctrl+Shift+K) */
          <form onSubmit={handleDirectAuth} className="space-y-4">
            <div className="rounded-lg border border-indigo-900/50 bg-indigo-950/30 p-2.5 flex items-center justify-between text-[11px] font-mono text-indigo-300">
              <span className="flex items-center gap-1.5">
                <Shield className="h-3.5 w-3.5 text-indigo-400" />
                <span>Staff Emergency Access Mode</span>
              </span>
              <kbd className="text-[10px] bg-[#02040a] border border-[#141d3d] px-1.5 py-0.5 rounded text-slate-400">
                Esc to cancel
              </kbd>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5 font-sans">
                Username or Staff Identifier (Optional)
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={usernameInput}
                  onChange={(e) => setUsernameInput(e.target.value)}
                  placeholder="e.g. Administrator, Staff-01"
                  className="w-full rounded-xl border border-[#141d3d] bg-[#02040a] px-3.5 py-2.5 text-xs text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none font-sans"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-medium text-slate-300 font-sans">
                  Password / Admin Key / Bearer Token
                </label>
              </div>
              <div className="relative">
                <input
                  id="direct-auth-input"
                  type={showPassword ? 'text' : 'password'}
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="Enter staff key or token..."
                  autoFocus
                  required
                  className="w-full rounded-xl border border-[#141d3d] bg-[#02040a] px-3.5 py-2.5 text-xs text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none font-mono pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-slate-500 hover:text-slate-300 transition cursor-pointer"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsTokenAuth(false)}
                className="flex-1 rounded-xl border border-[#141d3d] bg-[#02040a] px-3 py-2.5 text-xs font-medium text-slate-400 hover:bg-[#0a122e] hover:text-slate-200 transition cursor-pointer"
              >
                Back to Discord
              </button>
              <button
                id="submit-direct-auth"
                type="submit"
                disabled={isLoading || !tokenInput.trim()}
                className="flex-2 flex items-center justify-center gap-2 rounded-xl border border-indigo-500/50 bg-indigo-600 hover:bg-indigo-500 px-3 py-2.5 text-xs font-bold text-white transition shadow-[0_0_15px_rgba(99,102,241,0.3)] disabled:opacity-50 cursor-pointer"
              >
                <Key className="h-3.5 w-3.5" />
                <span>{isLoading ? 'Verifying...' : 'Authenticate'}</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </form>
        )}
      </div>

      {/* 3. Quick Links Row below Card (Clean Discord & Support Center) */}
      <div className="z-10 mt-6 flex items-center gap-5 text-xs text-slate-400 font-sans">
        <a
          href={discordInvite || 'https://discord.gg/umbrella'}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 hover:text-indigo-300 transition"
        >
          <svg className="h-4 w-4 fill-current text-indigo-400" viewBox="0 0 24 24">
            <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.929 1.793 8.18 1.793 12.061 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.893.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.028zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
          </svg>
          <span>Discord Server</span>
        </a>

        <span className="text-slate-700">•</span>

        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 hover:text-indigo-300 transition"
        >
          <HelpCircle className="h-4 w-4 text-indigo-400" />
          <span>Support Center</span>
        </a>
      </div>

      {/* 4. Footer Watermark */}
      <div className="z-10 mt-8 text-center text-[11px] font-mono text-slate-500">
        <div>UmbrellaOS Network Gateway • Version 2.4.0</div>
        <div className="text-[10px] text-slate-600 mt-0.5">
          Enterprise Fleet Architecture • Minecraft Multi-Node Hypervisor
        </div>
      </div>
    </div>
  );
};
