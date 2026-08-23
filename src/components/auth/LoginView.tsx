import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { api } from '../../lib/api';
import { UmbrellaLogo } from '../common/UmbrellaLogo';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  Key,
  Shield,
  LogIn,
  AlertCircle,
  CheckCircle2,
  Lock,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';

export const LoginView: React.FC = () => {
  const {
    setSessionToken,
    setCurrentUser,
    setActiveTab,
    addToast,
    isDisconnected,
  } = useDashboard();

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Direct Token or Admin Key fallback input
  const [tokenInput, setTokenInput] = useState('');
  const [isTokenAuth, setIsTokenAuth] = useState(false);

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
    if (!tokenInput.trim()) return;

    setIsLoading(true);
    setErrorMessage(null);

    try {
      // First try as a session token (Bearer token)
      api.setSessionToken(tokenInput.trim());
      try {
        const user = await api.getMe();
        setSessionToken(tokenInput.trim());
        setCurrentUser(user);
        addToast({
          type: 'success',
          title: 'Session Authenticated',
          message: `Logged in as ${user.username}`,
        });
        setActiveTab('overview');
        return;
      } catch {
        // If Bearer auth fails, test as X-Admin-Key
        api.setSessionToken(null);
        api.setAdminKey(tokenInput.trim());
        const health = await api.getHealth();
        if (health.status) {
          // Valid admin key
          const fallbackUser = {
            id: 'admin-key-holder',
            discord_id: '0',
            username: 'Administrator (Key)',
            email: null,
            role_id: 'admin',
            role: 'owner',
            permissions: ['*'],
            is_active: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          };
          setCurrentUser(fallbackUser);
          addToast({
            type: 'success',
            title: 'Admin Key Verified',
            message: 'Authenticated with administrative privileges.',
          });
          setActiveTab('overview');
          return;
        }
      }
      throw new Error('Invalid Session Token or Admin Key.');
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
      className="min-h-screen w-full flex items-center justify-center p-4 bg-[#02040a] text-slate-100 font-sans"
    >
      <div className="w-full max-w-md space-y-6">
        <DisconnectedBanner />

        <div className="rounded-2xl border border-[#141d3d] bg-[#060b1c]/90 p-8 shadow-2xl backdrop-blur-xl">
          {/* Header */}
          <div className="text-center space-y-3 mb-8">
            <div className="flex justify-center">
              <UmbrellaLogo size="lg" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                Staff Authentication
              </h1>
              <p className="text-xs text-indigo-300/80 mt-1">
                UmbrellaOS Network Administration Gateway
              </p>
            </div>
          </div>

          {errorMessage && (
            <div
              id="login-error-alert"
              className="mb-6 flex items-start gap-2.5 rounded-lg border border-rose-500/40 bg-rose-950/50 p-3 text-xs text-rose-300"
            >
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Primary: Discord OAuth */}
          {!isTokenAuth ? (
            <div className="space-y-4">
              <button
                id="login-discord-button"
                onClick={handleDiscordLogin}
                disabled={isLoading || isDisconnected}
                className="w-full flex items-center justify-center gap-3 rounded-xl border border-[#5865F2]/50 bg-[#5865F2] hover:bg-[#4752C4] px-4 py-3 text-sm font-semibold text-white transition shadow-[0_0_20px_rgba(88,101,242,0.25)] active:scale-[0.98] disabled:opacity-50 cursor-pointer"
              >
                <LogIn className="h-4 w-4" />
                <span>{isLoading ? 'Connecting to Discord...' : 'Continue with Discord'}</span>
                <ExternalLink className="h-3.5 w-3.5 opacity-70" />
              </button>

              <div className="relative my-6 flex items-center justify-center">
                <div className="w-full border-t border-[#141d3d]" />
                <span className="bg-[#060b1c] px-3 text-[11px] font-mono uppercase text-slate-500 absolute">
                  or
                </span>
              </div>

              <button
                id="switch-to-token-auth"
                type="button"
                onClick={() => setIsTokenAuth(true)}
                className="w-full flex items-center justify-center gap-2 rounded-xl border border-[#141d3d] bg-[#02040a] hover:bg-[#0a122e] px-4 py-2.5 text-xs font-medium text-indigo-300 transition cursor-pointer"
              >
                <Key className="h-3.5 w-3.5" />
                <span>Authenticate with Admin Key / Token</span>
              </button>
            </div>
          ) : (
            /* Secondary: Direct Token / Key Form */
            <form onSubmit={handleDirectAuth} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5 font-mono">
                  Session Token or Admin Key (X-Admin-Key)
                </label>
                <div className="relative">
                  <input
                    id="direct-auth-input"
                    type="password"
                    value={tokenInput}
                    onChange={(e) => setTokenInput(e.target.value)}
                    placeholder="Enter bearer token or admin key..."
                    required
                    className="w-full rounded-xl border border-[#141d3d] bg-[#02040a] px-3.5 py-2.5 text-xs text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none font-mono"
                  />
                  <Lock className="absolute right-3 top-3 h-4 w-4 text-slate-600 pointer-events-none" />
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setIsTokenAuth(false)}
                  className="flex-1 rounded-xl border border-[#141d3d] bg-[#02040a] px-3 py-2.5 text-xs font-medium text-slate-400 hover:bg-[#0a122e] transition cursor-pointer"
                >
                  Back
                </button>
                <button
                  id="submit-direct-auth"
                  type="submit"
                  disabled={isLoading || !tokenInput.trim()}
                  className="flex-2 flex items-center justify-center gap-2 rounded-xl border border-indigo-500/50 bg-indigo-600 hover:bg-indigo-500 px-3 py-2.5 text-xs font-bold text-white transition shadow-[0_0_15px_rgba(99,102,241,0.3)] disabled:opacity-50 cursor-pointer"
                >
                  <span>{isLoading ? 'Verifying...' : 'Authenticate'}</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </form>
          )}

          {/* Security notice */}
          <div className="mt-8 pt-4 border-t border-[#141d3d]/60 flex items-center justify-center gap-2 text-[11px] text-slate-500">
            <Shield className="h-3.5 w-3.5 text-indigo-400/70" />
            <span>Encrypted Session • Role-Based Access Control</span>
          </div>
        </div>
      </div>
    </div>
  );
};
