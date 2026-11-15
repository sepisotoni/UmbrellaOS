import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, Loader2, Shield } from 'lucide-react';
import { useDashboard } from '../../context/DashboardContext';
import { supabase } from '../../lib/supabase';

export const MFAChallengeModal: React.FC = () => {
  const {
    mfaPending,
    mfaEnrollmentRequired,
    completeMfa,
    dismissMfa,
    setMfaEnrollmentRequired,
  } = useDashboard();
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [enrollment, setEnrollment] = useState<{
    factorId: string;
    challengeId: string;
    qrCode: string;
    secret: string;
  } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const isEnrolling = mfaEnrollmentRequired && !mfaPending;

  useEffect(() => {
    if (!isEnrolling || !supabase || enrollment) return;
    let active = true;
    void (async () => {
      try {
        const { data, error: enrollError } = await supabase.auth.mfa.enroll({
          factorType: 'totp',
          friendlyName: 'UmbrellaOS Dashboard',
        });
        if (enrollError) throw enrollError;
        const { data: challenge, error: challengeError } =
          await supabase.auth.mfa.challenge({ factorId: data.id });
        if (challengeError) throw challengeError;
        if (active) {
          setEnrollment({
            factorId: data.id,
            challengeId: challenge.id,
            qrCode: data.totp.qr_code,
            secret: data.totp.secret,
          });
        }
      } catch (enrollError: any) {
        if (active) setError(enrollError?.message || 'Unable to enroll a Supabase MFA factor.');
      }
    })();
    return () => { active = false; };
  }, [isEnrolling, enrollment]);

  useEffect(() => {
    if (mfaPending || isEnrolling) {
      setCode('');
      setError(null);
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [mfaPending, isEnrolling]);

  const handleSubmit = async () => {
    const trimmed = code.replace(/\s/g, '');
    if (!/^\d{6}$/.test(trimmed)) {
      setError('Enter the 6-digit code from your authenticator app.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      if (mfaPending) {
        await completeMfa(trimmed);
      } else if (supabase && enrollment) {
        const { error: verifyError } = await supabase.auth.mfa.verify({
          factorId: enrollment.factorId,
          challengeId: enrollment.challengeId,
          code: trimmed,
        });
        if (verifyError) throw verifyError;
        await supabase.auth.refreshSession();
        setMfaEnrollmentRequired(false);
        setEnrollment(null);
      }
    } catch (verifyError: any) {
      setError(verifyError?.message || 'The authenticator code was rejected.');
      setCode('');
    } finally {
      setLoading(false);
    }
  };

  if (!mfaPending && !mfaEnrollmentRequired) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-sm mx-4 rounded-2xl border border-white/10 bg-[oklch(0.14_0.02_264)] p-6 shadow-2xl space-y-4">
        <div className="flex items-center gap-3">
          <Shield className="h-5 w-5 text-indigo-300" />
          <div>
            <h2 className="text-sm font-semibold text-white">
              {isEnrolling ? 'Set up Supabase MFA' : 'Verify your identity'}
            </h2>
            <p className="text-xs text-white/40">
              {isEnrolling ? 'Required to migrate your existing MFA protection' : 'Enter your authenticator code'}
            </p>
          </div>
        </div>

        {isEnrolling && enrollment && (
          <div className="space-y-2 text-center">
            <img src={enrollment.qrCode} alt="Supabase MFA enrollment QR code" className="mx-auto h-40 w-40 rounded bg-white p-2" />
            <p className="text-[11px] text-white/50">Scan the QR code with your authenticator app.</p>
            <code className="block break-all rounded bg-white/5 p-2 text-[10px] text-white/70">{enrollment.secret}</code>
          </div>
        )}

        {isEnrolling && !enrollment && !error && (
          <div className="flex justify-center py-4"><Loader2 className="h-5 w-5 animate-spin text-indigo-300" /></div>
        )}

        <input
          ref={inputRef}
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          placeholder="000000"
          value={code}
          onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
          className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-center text-xl font-mono tracking-[0.5em] text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
          disabled={loading}
          aria-label="Authenticator code"
        />

        {error && (
          <div className="flex gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-300">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <div className="flex gap-2">
          <button onClick={dismissMfa} className="flex-1 rounded-xl border border-white/10 px-3 py-2 text-xs text-white/60">
            Sign out
          </button>
          <button
            onClick={() => void handleSubmit()}
            disabled={loading || code.length !== 6 || (isEnrolling && !enrollment)}
            className="flex-1 rounded-xl bg-indigo-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40"
          >
            {loading ? 'Verifying…' : isEnrolling ? 'Verify & migrate MFA' : 'Verify & continue'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default MFAChallengeModal;
