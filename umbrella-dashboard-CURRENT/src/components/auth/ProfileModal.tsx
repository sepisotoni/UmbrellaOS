import React, { useState, useMemo, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { supabase } from '../../lib/supabase';
import {
  X, Copy, Check, LogOut, Shield, ShieldOff, ShieldCheck,
  Loader2, AlertCircle, KeyRound, QrCode,
} from 'lucide-react';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type MFAStep =
  | 'idle'          // not in enrollment flow
  | 'loading'       // waiting for /mfa/enable response
  | 'qr'            // showing QR + confirm input
  | 'confirming'    // waiting for /mfa/confirm response
  | 'disabling';    // waiting for /mfa/disable response

export const ProfileModal: React.FC<ProfileModalProps> = ({ isOpen, onClose }) => {
  const { currentUser, logout, addToast } = useDashboard();
  const [copiedId, setCopiedId] = useState(false);
  const [isMfaEnabled, setIsMfaEnabled] = useState(false);

  // MFA enrollment state
  const [mfaStep, setMfaStep] = useState<MFAStep>('idle');
  const [factorId, setFactorId] = useState<string | null>(null);
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [mfaSecret, setMfaSecret] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState('');
  const [mfaError, setMfaError] = useState<string | null>(null);
  const [showSecret, setShowSecret] = useState(false);

  useEffect(() => {
    if (!isOpen || !supabase) return;
    let active = true;
    void supabase.auth.mfa.listFactors().then(({ data, error }) => {
      if (active && !error) {
        setIsMfaEnabled(data.totp.some((factor) => factor.status === 'verified'));
      }
    });
    return () => { active = false; };
  }, [isOpen]);

  const groupedPermissions = useMemo(() => {
    if (!currentUser?.permissions) return {};
    const groups: Record<string, string[]> = {};
    for (const perm of currentUser.permissions) {
      const parts = perm.split('.');
      const prefix = parts.length > 1 ? parts[0] : 'general';
      if (!groups[prefix]) groups[prefix] = [];
      groups[prefix].push(perm);
    }
    return groups;
  }, [currentUser?.permissions]);

  if (!isOpen || !currentUser) return null;

  const handleCopyDiscordId = () => {
    if (currentUser.discord_id) {
      navigator.clipboard.writeText(currentUser.discord_id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  const handleSignOut = async () => {
    await logout();
    onClose();
  };

  // ---------------------------------------------------------------------------
  // MFA enrollment handlers
  // ---------------------------------------------------------------------------

  const handleBeginMFA = async () => {
    setMfaStep('loading');
    setMfaError(null);
    try {
      if (!supabase) throw new Error('Supabase Auth is not configured.');
      const { data, error } = await supabase.auth.mfa.enroll({
        factorType: 'totp',
        friendlyName: 'UmbrellaOS Dashboard',
      });
      if (error) throw error;
      setFactorId(data.id);
      setQrCode(data.totp.qr_code);
      setMfaSecret(data.totp.secret);
      setMfaCode('');
      setMfaStep('qr');
    } catch (err: any) {
      setMfaError(err?.message || 'Failed to start MFA enrollment.');
      setMfaStep('idle');
    }
  };

  const handleConfirmMFA = async () => {
    const trimmed = mfaCode.replace(/\s/g, '');
    if (!/^\d{6}$/.test(trimmed)) {
      setMfaError('Enter the 6-digit code from your authenticator app.');
      return;
    }
    setMfaStep('confirming');
    setMfaError(null);
    try {
      if (!supabase || !factorId) throw new Error('MFA enrollment is not active.');
      const { data: challenge, error: challengeError } =
        await supabase.auth.mfa.challenge({ factorId });
      if (challengeError) throw challengeError;
      const { error } = await supabase.auth.mfa.verify({
        factorId,
        challengeId: challenge.id,
        code: trimmed,
      });
      if (error) throw error;
      await supabase.auth.refreshSession();
      setIsMfaEnabled(true);
      addToast({ type: 'success', title: 'MFA Enabled', message: 'Two-factor authentication is now active on your account.' });
      setMfaStep('idle');
      setFactorId(null);
      setQrCode(null);
      setMfaSecret(null);
      setMfaCode('');
    } catch (err: any) {
      setMfaError(err?.message || 'Incorrect code — try again.');
      setMfaStep('qr');
    }
  };

  const handleDisableMFA = async () => {
    setMfaStep('disabling');
    setMfaError(null);
    try {
      if (currentUser.mfa_enabled) {
        throw new Error('MFA is required by this account during the migration and cannot be disabled here.');
      }
      if (!supabase) throw new Error('Supabase Auth is not configured.');
      const { data, error } = await supabase.auth.mfa.listFactors();
      if (error) throw error;
      const factor = data.totp.find((candidate) => candidate.status === 'verified');
      if (!factor) throw new Error('No verified Supabase MFA factor found.');
      const { error: unenrollError } = await supabase.auth.mfa.unenroll({ factorId: factor.id });
      if (unenrollError) throw unenrollError;
      setIsMfaEnabled(false);
      addToast({ type: 'info', title: 'MFA Disabled', message: 'Two-factor authentication has been removed from your account.' });
      setMfaStep('idle');
    } catch (err: any) {
      setMfaError(err?.message || 'MFA could not be disabled.');
      setMfaStep('idle');
    }
  };

  const cancelMFA = () => {
    setMfaStep('idle');
    setFactorId(null);
    setQrCode(null);
    setMfaSecret(null);
    setMfaCode('');
    setMfaError(null);
    setShowSecret(false);
  };

  const fallbackAvatar = `https://cdn.discordapp.com/embed/avatars/${Math.abs(parseInt(currentUser.discord_id, 10) || 0) % 5}.png`;
  const requiresMfaMigration = currentUser.mfa_enabled && !isMfaEnabled;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end pt-16 pr-4 bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-[#141d3d] bg-[#060b1c] p-6 shadow-2xl space-y-5 text-slate-100 font-sans">

        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#141d3d] pb-3">
          <h3 className="font-bold text-white text-sm">Your Profile</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Avatar + identity */}
        <div className="flex items-center gap-4">
          <img
            src={currentUser.avatar_url || fallbackAvatar}
            alt={currentUser.username}
            className="w-14 h-14 rounded-full border-2 border-[#141d3d] object-cover"
            onError={(e) => { (e.target as HTMLImageElement).src = fallbackAvatar; }}
          />
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-white text-sm truncate">{currentUser.username}</div>
            {currentUser.email && (
              <div className="text-xs text-slate-400 truncate">{currentUser.email}</div>
            )}
            <div className="mt-1 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-indigo-900/40 border border-indigo-700/30 text-[10px] font-mono text-indigo-300 capitalize">
              {currentUser.role || 'No role'}
            </div>
          </div>
          <button
            onClick={handleCopyDiscordId}
            title="Copy Discord ID"
            className="text-slate-500 hover:text-slate-300 transition"
          >
            {copiedId ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
          </button>
        </div>

        {/* Permissions */}
        {Object.keys(groupedPermissions).length > 0 && (
          <div>
            <div className="text-[10px] uppercase font-mono text-slate-500 font-bold mb-2">Permissions</div>
            <div className="rounded-lg border border-[#1e1b4b] bg-[#070914] p-3 space-y-2 max-h-36 overflow-y-auto">
              {(Object.entries(groupedPermissions) as [string, string[]][]).map(([ns, perms]) => (
                <div key={ns} className="space-y-1">
                  <div className="text-[9px] uppercase font-mono text-slate-600 font-bold">{ns}</div>
                  <div className="flex flex-wrap gap-1">
                    {perms.map((perm) => (
                      <span key={perm} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-950/60 text-indigo-300 border border-indigo-800/30">
                        {perm}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------ */}
        {/* Two-Factor Authentication Section                                   */}
        {/* ------------------------------------------------------------------ */}
        <div className="rounded-xl border border-white/8 bg-white/3 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isMfaEnabled
                ? <ShieldCheck className="h-4 w-4 text-emerald-400" />
                : <ShieldOff className="h-4 w-4 text-white/30" />}
              <span className="text-xs font-medium text-white/80">Two-Factor Authentication</span>
            </div>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${isMfaEnabled ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' : 'bg-white/5 text-white/30 border border-white/10'}`}>
              {isMfaEnabled ? 'ENABLED' : requiresMfaMigration ? 'MIGRATION REQUIRED' : 'DISABLED'}
            </span>
          </div>

          {/* idle: show enable or disable prompt */}
          {mfaStep === 'idle' && (
            <>
              {!isMfaEnabled ? (
                <div className="space-y-2">
                  <p className="text-[11px] text-white/40 leading-relaxed">
                    {requiresMfaMigration
                      ? 'Replace your existing Core authenticator with a new Supabase Auth factor. Your old code will stop working after migration.'
                      : 'Add a second layer of security with an authenticator app.'}
                  </p>
                  <button
                    onClick={handleBeginMFA}
                    className="w-full flex items-center justify-center gap-2 rounded-lg bg-indigo-600/80 hover:bg-indigo-600 px-3 py-2 text-xs font-medium text-white transition"
                  >
                    <Shield className="h-3.5 w-3.5" /> Enable MFA
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {currentUser.mfa_enabled ? (
                    <p className="text-[11px] text-white/40">This factor is required by your account policy.</p>
                  ) : (
                    <button
                      onClick={handleDisableMFA}
                      className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs font-medium text-red-400 hover:bg-red-500/20 transition"
                    >
                      Disable MFA
                    </button>
                  )}
                  {mfaError && (
                    <div className="flex items-center gap-1.5 text-[11px] text-red-400">
                      <AlertCircle className="h-3 w-3" />{mfaError}
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* loading: spinner while fetching QR */}
          {mfaStep === 'loading' && (
            <div className="flex justify-center py-3">
              <Loader2 className="h-5 w-5 animate-spin text-white/30" />
            </div>
          )}

          {/* qr: show provisioning URI as QR + confirm input */}
          {(mfaStep === 'qr' || mfaStep === 'confirming') && qrCode && (
            <div className="space-y-3">
              <p className="text-[11px] text-white/50 leading-relaxed">
                Scan the QR code in your authenticator app, then enter the 6-digit code to confirm.
              </p>

              <div className="flex justify-center">
                <img
                  src={qrCode}
                  alt="MFA QR Code"
                  className="rounded-lg border border-white/10"
                  width={180}
                  height={180}
                />
              </div>

              {/* Manual secret toggle */}
              <button
                onClick={() => setShowSecret((s) => !s)}
                className="flex items-center gap-1.5 text-[10px] text-white/30 hover:text-white/50 transition mx-auto"
              >
                <KeyRound className="h-3 w-3" />
                {showSecret ? 'Hide' : 'Can\'t scan?'} manual entry code
              </button>
              {showSecret && mfaSecret && (
                <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-center font-mono text-xs text-white/70 tracking-widest break-all">
                  {mfaSecret}
                </div>
              )}

              {/* Code confirm input */}
              <div className="flex gap-2">
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="000000"
                  value={mfaCode}
                  onChange={(e) => { setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6)); setMfaError(null); }}
                  onKeyDown={(e) => e.key === 'Enter' && handleConfirmMFA()}
                  autoFocus
                  className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-center font-mono text-sm text-white placeholder:text-white/20 focus:outline-none focus:ring-1 focus:ring-indigo-500/40"
                  disabled={mfaStep === 'confirming'}
                />
                <button
                  onClick={handleConfirmMFA}
                  disabled={mfaCode.length !== 6 || mfaStep === 'confirming'}
                  className="rounded-lg bg-indigo-600/80 hover:bg-indigo-600 px-3 py-2 text-xs font-medium text-white transition disabled:opacity-40 flex items-center gap-1.5"
                >
                  {mfaStep === 'confirming' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
                  Verify
                </button>
              </div>

              {mfaError && (
                <div className="flex items-center gap-1.5 text-[11px] text-red-400">
                  <AlertCircle className="h-3 w-3" />{mfaError}
                </div>
              )}

              <button onClick={cancelMFA} className="w-full text-[10px] text-white/25 hover:text-white/40 transition">
                Cancel
              </button>
            </div>
          )}

          {mfaStep === 'disabling' && (
            <div className="flex justify-center py-3">
              <Loader2 className="h-5 w-5 animate-spin text-white/30" />
            </div>
          )}
        </div>

        {/* Sign out */}
        <button
          onClick={handleSignOut}
          className="w-full flex items-center justify-center gap-2 rounded-xl border border-red-900/40 bg-red-950/20 px-4 py-2.5 text-sm font-medium text-red-400 hover:bg-red-950/40 transition cursor-pointer"
        >
          <LogOut className="w-4 h-4" /> Sign Out
        </button>
      </div>
    </div>
  );
};
