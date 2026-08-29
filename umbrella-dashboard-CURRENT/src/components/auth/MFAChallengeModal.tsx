import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Shield, KeyRound, X, Loader2, AlertCircle } from 'lucide-react';
import { useDashboard } from '../../context/DashboardContext';

/**
 * MFAChallengeModal
 *
 * Shown automatically when Discord OAuth returns a 403 mfa_required response.
 * The user enters their 6-digit TOTP code; on success a full session token is
 * issued and the dashboard proceeds normally.
 */
export const MFAChallengeModal: React.FC = () => {
  const { mfaPending, completeMfa, dismissMfa, addToast } = useDashboard();

  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus the input when the modal opens
  useEffect(() => {
    if (mfaPending) {
      setCode('');
      setError(null);
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [mfaPending]);

  const handleSubmit = useCallback(async () => {
    const trimmed = code.replace(/\s/g, '');
    if (trimmed.length !== 6 || !/^\d{6}$/.test(trimmed)) {
      setError('Enter your 6-digit authenticator code.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await completeMfa(trimmed);
    } catch (err: any) {
      const msg =
        err?.detail?.message ||
        err?.message ||
        'Invalid code — check your authenticator app and try again.';
      setError(msg);
      setCode('');
      setTimeout(() => inputRef.current?.focus(), 50);
    } finally {
      setLoading(false);
    }
  }, [code, completeMfa]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSubmit();
    if (e.key === 'Escape') dismissMfa();
  };

  if (!mfaPending) return null;

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) dismissMfa(); }}
    >
      <div
        className="relative w-full max-w-sm mx-4 rounded-2xl border border-white/10 bg-[oklch(0.14_0.02_264)] shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="mfa-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[oklch(0.55_0.2_264)/0.15]">
              <Shield className="h-4 w-4 text-[oklch(0.7_0.18_264)]" />
            </div>
            <div>
              <h2 id="mfa-title" className="text-sm font-semibold text-white">
                Two-Factor Authentication
              </h2>
              <p className="text-xs text-white/40">Required to complete sign-in</p>
            </div>
          </div>
          <button
            onClick={dismissMfa}
            className="rounded-lg p-1.5 text-white/30 transition hover:bg-white/5 hover:text-white/70"
            aria-label="Cancel MFA"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 pb-6 space-y-4">
          <p className="text-xs text-white/50 leading-relaxed">
            Your account has two-factor authentication enabled. Open your authenticator app and
            enter the 6-digit code below.
          </p>

          {/* Code input */}
          <div className="relative">
            <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30 pointer-events-none" />
            <input
              ref={inputRef}
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              placeholder="000000"
              value={code}
              onChange={(e) => {
                const v = e.target.value.replace(/\D/g, '').slice(0, 6);
                setCode(v);
                if (error) setError(null);
              }}
              onKeyDown={handleKeyDown}
              className="w-full rounded-xl border border-white/10 bg-white/5 pl-9 pr-4 py-3
                         text-center text-xl font-mono tracking-[0.5em] text-white
                         placeholder:text-white/15 placeholder:tracking-widest
                         focus:outline-none focus:ring-2 focus:ring-[oklch(0.55_0.2_264)/0.4]
                         transition disabled:opacity-50"
              disabled={loading}
              aria-label="TOTP code"
            />
          </div>

          {/* Error message */}
          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2">
              <AlertCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-red-400" />
              <p className="text-xs text-red-300">{error}</p>
            </div>
          )}

          {/* Actions */}
          <button
            onClick={handleSubmit}
            disabled={loading || code.length !== 6}
            className="w-full flex items-center justify-center gap-2 rounded-xl
                       bg-[oklch(0.55_0.2_264)] px-4 py-3 text-sm font-medium text-white
                       transition hover:bg-[oklch(0.6_0.2_264)] disabled:opacity-40
                       disabled:cursor-not-allowed focus:outline-none
                       focus:ring-2 focus:ring-[oklch(0.55_0.2_264)/0.5]"
          >
            {loading ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Verifying…</>
            ) : (
              <><Shield className="h-4 w-4" /> Verify & Sign In</>
            )}
          </button>

          <p className="text-center text-xs text-white/25">
            The code refreshes every 30 seconds.
          </p>
        </div>
      </div>
    </div>
  );
};

export default MFAChallengeModal;
