import React, { useState } from 'react';
import { AlertCircle, ExternalLink, LogIn } from 'lucide-react';
import { useDashboard } from '../../context/DashboardContext';
import { supabase } from '../../lib/supabase';
import { BrandLogo } from '../common/BrandLogos';
import { AtmosphericBackground } from '../common/AtmosphericBackground';
import { DisconnectedBanner } from '../common/DisconnectedBanner';

export const LoginView: React.FC = () => {
  const {
    addToast,
    isDisconnected,
    authConfigLoaded,
    authConfigError,
    showDoodles,
    doodleOpacity,
    discordInvite,
  } = useDashboard();
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleDiscordLogin = async () => {
    if (!supabase) {
      setErrorMessage(authConfigError || 'Core did not provide Supabase Auth settings.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'discord',
      options: { redirectTo: `${window.location.origin}/` },
    });
    if (error) {
      setErrorMessage(error.message);
      setIsLoading(false);
      addToast({ type: 'error', title: 'Discord sign-in failed', message: error.message });
    }
  };

  return (
    <div className="min-h-screen w-full relative flex flex-col items-center justify-center p-4 text-slate-100 font-sans select-none overflow-hidden">
      <AtmosphericBackground
        variant="login"
        showDoodles={showDoodles}
        doodleOpacity={doodleOpacity}
        showStars
        showHorizon
      />
      <div className="z-10 w-full max-w-md space-y-4 mb-2">
        <DisconnectedBanner />
      </div>
      <div className="z-10 w-full max-w-[420px] rounded-2xl border border-[#141d3d] bg-[#060b1c]/90 p-8 shadow-2xl backdrop-blur-xl">
        <div className="text-center space-y-3 mb-6">
          <div className="flex justify-center items-center">
            <BrandLogo variant="os" size="xl" renderMode="vector" showWordmark={false} showBadge={false} glow />
          </div>
          <div className="font-bold text-2xl tracking-tight text-white">
            Umbrella <span className="font-mono font-black text-indigo-300">OS</span>
          </div>
          <p className="text-xs text-indigo-300/80 font-mono">
            Minecraft Multi-Node Fleet Operations &amp; Sentinel Security
          </p>
        </div>

        {errorMessage && (
          <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-rose-500/40 bg-rose-950/60 p-3 text-xs text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-400" />
            <span>{errorMessage}</span>
          </div>
        )}

        <button
          onClick={handleDiscordLogin}
          disabled={isLoading || isDisconnected || !authConfigLoaded || !supabase}
          className="w-full flex items-center justify-center gap-3 rounded-xl border border-[#5865F2]/50 bg-[#5865F2] hover:bg-[#4752C4] px-4 py-3 text-sm font-semibold text-white transition disabled:opacity-50"
        >
          <LogIn className="h-4 w-4" />
          <span>{isLoading ? 'Connecting to Discord…' : 'Continue with Discord'}</span>
          <ExternalLink className="h-3.5 w-3.5 opacity-70" />
        </button>
        {!authConfigLoaded && (
          <p className="mt-3 text-center text-[11px] text-amber-300/80">
            Loading sign-in settings from Core…
          </p>
        )}
        {authConfigError && (
          <p className="mt-3 text-center text-[11px] text-amber-300/80">{authConfigError}</p>
        )}
      </div>
      <div className="z-10 mt-6 flex items-center gap-5 text-xs text-slate-400">
        <a href={discordInvite} target="_blank" rel="noopener noreferrer" className="hover:text-indigo-300 transition">
          Discord Server
        </a>
        <span className="text-slate-700">•</span>
        <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="hover:text-indigo-300 transition">
          Support Center
        </a>
      </div>
      <div className="z-10 mt-8 text-center text-[11px] font-mono text-slate-500">
        UmbrellaOS Network Gateway
      </div>
    </div>
  );
};
