import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { api } from '../../lib/api';
import { 
  ShieldAlert, 
  X, 
  AlertTriangle,
  Ban,
  Clock,
  Server,
  Loader2,
  CheckCircle2
} from 'lucide-react';

interface PunishModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialPlayerName?: string;
}

export const PunishModal: React.FC<PunishModalProps> = ({
  isOpen,
  onClose,
  initialPlayerName = ''
}) => {
  const { issuePunishment, servers, currentUser } = useDashboard();

  const [playerName, setPlayerName] = useState(initialPlayerName);
  const [punishmentType, setPunishmentType] = useState<'TEMP_BAN' | 'BAN' | 'HWID_BAN' | 'TEMP_MUTE' | 'MUTE' | 'KICK' | 'WARN'>('TEMP_BAN');
  const [duration, setDuration] = useState('7d');
  const [serverScope, setServerScope] = useState('GLOBAL');
  const [reason, setReason] = useState('GrimAC Flag: Reach & Hitbox Expansion');
  const [evidenceUrl, setEvidenceUrl] = useState('');
  const [ipBan, setIpBan] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  React.useEffect(() => {
    if (initialPlayerName) {
      setPlayerName(initialPlayerName);
    }
  }, [initialPlayerName]);

  React.useEffect(() => {
    if (isOpen) {
      setErrorMessage(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const presetReasons = [
    'GrimAC Flag: Reach & Hitbox Expansion',
    'KillAura & AutoClicker (Unfair Advantages)',
    'Fly / Speed / Movement Exploit',
    'Severe Chat Toxicity / Hate Speech',
    'Illegal Multi-Account Ban Evasion',
    'Duplication & Economy Exploit',
    'Malicious Lag Machine / Server Disruption'
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const trimmedName = playerName.trim();
    if (!trimmedName) {
      setErrorMessage('Player username cannot be empty.');
      return;
    }

    // Strict validation
    const validation = api.validateMinecraftUsername(trimmedName);
    if (!validation.valid) {
      setErrorMessage(validation.error || 'Invalid Minecraft username format.');
      return;
    }

    let expiresAt: string | null = null;
    if (punishmentType === 'TEMP_BAN' || punishmentType === 'TEMP_MUTE') {
      const now = new Date();
      if (duration === '1d') now.setDate(now.getDate() + 1);
      else if (duration === '7d') now.setDate(now.getDate() + 7);
      else if (duration === '30d') now.setDate(now.getDate() + 30);
      else if (duration === '90d') now.setDate(now.getDate() + 90);
      expiresAt = now.toISOString().replace('T', ' ').substring(0, 19);
    }

    setIsSubmitting(true);

    try {
      const res = await issuePunishment({
        playerUuid: 'manual-' + Math.random().toString(36).substr(2, 8),
        playerName: trimmedName,
        staffName: currentUser?.username || 'SolarisAdmin',
        type: ipBan ? 'IP_BAN' : punishmentType,
        reason: reason.trim(),
        expiresAt,
        serverScope,
        evidenceUrl: evidenceUrl.trim() || undefined
      });

      if (res && res.success === false) {
        // Preserves modal state with original values entered and reveals error
        setErrorMessage(res.error || 'Failed to enforce punishment. Check player existence and node connection.');
        setIsSubmitting(false);
        return;
      }

      setIsSubmitting(false);
      onClose();
    } catch (err: any) {
      setErrorMessage(err?.message || 'Network exception occurred during punishment dispatch.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 font-sans animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-[#0f131a] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/80 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-rose-500/30 bg-rose-950/40 text-rose-400">
              <ShieldAlert className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Issue Punishment / Enforcement</h3>
              <p className="text-[11px] text-slate-400">Synchronized across Velocity Proxies and Game Nodes</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Error Alert Display */}
        {errorMessage && (
          <div className="mx-5 mt-4 flex items-start gap-2.5 rounded-lg border border-rose-500/30 bg-rose-950/40 p-3 text-rose-200 animate-in fade-in slide-in-from-top-1">
            <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs">
              <p className="font-semibold text-rose-300">Action Failed</p>
              <p className="text-rose-200/90 mt-0.5">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 font-mono text-xs">
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block font-semibold text-slate-300 font-sans">Player Username / UUID</label>
              <span className="text-[10px] text-slate-500 font-sans">3-16 chars, a-z, 0-9, _</span>
            </div>
            <input
              type="text"
              value={playerName}
              onChange={(e) => {
                setPlayerName(e.target.value);
                if (errorMessage) setErrorMessage(null);
              }}
              placeholder="e.g. VoidReaper_X"
              required
              className={`w-full rounded-md border ${
                errorMessage ? 'border-rose-500 bg-rose-950/20' : 'border-slate-700 bg-slate-900'
              } px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono transition-colors`}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-300 mb-1 font-sans">Action Type</label>
              <select
                value={punishmentType}
                onChange={(e) => setPunishmentType(e.target.value as any)}
                className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none"
              >
                <option value="TEMP_BAN">Temporary Ban</option>
                <option value="BAN">Permanent Ban</option>
                <option value="HWID_BAN">Hardware HWID Ban</option>
                <option value="TEMP_MUTE">Temporary Mute</option>
                <option value="MUTE">Permanent Mute</option>
                <option value="KICK">Kick Player</option>
                <option value="WARN">Formal Warning</option>
              </select>
            </div>

            {(punishmentType === 'TEMP_BAN' || punishmentType === 'TEMP_MUTE') && (
              <div>
                <label className="block font-semibold text-slate-300 mb-1 font-sans">Duration</label>
                <select
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                  className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none"
                >
                  <option value="1d">1 Day (24 Hours)</option>
                  <option value="7d">7 Days (1 Week)</option>
                  <option value="30d">30 Days (1 Month)</option>
                  <option value="90d">90 Days (3 Months)</option>
                </select>
              </div>
            )}
          </div>

          <div>
            <label className="block font-semibold text-slate-300 mb-1 font-sans">Server Scope</label>
            <select
              value={serverScope}
              onChange={(e) => setServerScope(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none"
            >
              <option value="GLOBAL">Network-Wide (Global Across All Instances)</option>
              {servers.map(s => (
                <option key={s.id} value={s.id}>{s.name} ({s.id})</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-300 mb-1 font-sans">Reason</label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Specify rule violation details..."
              required
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
            />
            {/* Quick Chips */}
            <div className="flex flex-wrap gap-1 mt-2">
              {presetReasons.map(r => (
                <button
                  type="button"
                  key={r}
                  onClick={() => setReason(r)}
                  className="rounded border border-slate-800 bg-slate-800/60 px-2 py-0.5 text-[10px] text-slate-400 hover:text-cyan-300 hover:border-slate-700 transition-colors cursor-pointer"
                >
                  {r}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-300 mb-1 font-sans">Evidence / Replay URL (Optional)</label>
            <input
              type="text"
              value={evidenceUrl}
              onChange={(e) => setEvidenceUrl(e.target.value)}
              placeholder="https://grim.umbrella-mc.net/logs/... or video url"
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
            />
          </div>

          <div className="flex items-center gap-2 pt-1 font-sans">
            <input
              type="checkbox"
              id="ipBan"
              checked={ipBan}
              onChange={(e) => setIpBan(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-slate-700 bg-slate-900 text-rose-500 focus:ring-0 cursor-pointer"
            />
            <label htmlFor="ipBan" className="text-xs text-slate-300 cursor-pointer select-none flex items-center gap-1.5">
              <span>Also blacklist player's current IP address</span>
              <AlertTriangle className="h-3 w-3 text-amber-400" />
            </label>
          </div>

          {/* Footer actions */}
          <div className="flex items-center justify-end gap-2 border-t border-slate-800 pt-4 mt-2 font-sans">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="rounded-md border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-md bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-500 transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Enforcing...</span>
                </>
              ) : (
                <>
                  <ShieldAlert className="h-3.5 w-3.5" />
                  <span>Confirm & Enforce</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
