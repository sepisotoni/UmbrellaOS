import React, { useState, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { api, ServerRecord } from '../../lib/api';
import {
  ShieldAlert,
  X,
  AlertTriangle,
  Ban,
  Clock,
  Server,
  Loader2,
  CheckCircle2,
} from 'lucide-react';

interface PunishModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialPlayerName?: string;
}

export const PunishModal: React.FC<PunishModalProps> = ({
  isOpen,
  onClose,
  initialPlayerName = '',
}) => {
  const { addToast } = useDashboard();
  const [servers, setServers] = useState<ServerRecord[]>([]);
  const [playerName, setPlayerName] = useState(initialPlayerName);
  const [punishmentType, setPunishmentType] = useState<
    'TEMP_BAN' | 'BAN' | 'IP_BAN' | 'TEMP_MUTE' | 'MUTE' | 'KICK' | 'WARN'
  >('TEMP_BAN');
  const [duration, setDuration] = useState('7d');
  const [serverScope, setServerScope] = useState('GLOBAL');
  const [reason, setReason] = useState('GrimAC Flag: Reach & Hitbox Expansion');
  const [evidenceUrl, setEvidenceUrl] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (initialPlayerName) {
      setPlayerName(initialPlayerName);
    }
  }, [initialPlayerName]);

  useEffect(() => {
    if (isOpen) {
      setErrorMessage(null);
      api.getServers().then((res) => {
        if (res) setServers(res);
      }).catch(() => {});
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const presetReasons = [
    'GrimAC Flag: Reach & Hitbox Expansion',
    'KillAura & AutoClicker (Unfair Advantages)',
    'Fly / Speed / Movement Exploit',
    'Severe Chat Toxicity / Harassment',
    'Illegal Multi-Account Ban Evasion',
    'Duplication & Economy Exploit',
    'Malicious Server Disruption',
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const trimmedName = playerName.trim();
    if (!trimmedName) {
      setErrorMessage('Player username or UUID cannot be empty.');
      return;
    }

    let expiresAt: string | undefined = undefined;
    if (punishmentType === 'TEMP_BAN' || punishmentType === 'TEMP_MUTE') {
      const now = new Date();
      if (duration === '1d') now.setDate(now.getDate() + 1);
      else if (duration === '7d') now.setDate(now.getDate() + 7);
      else if (duration === '30d') now.setDate(now.getDate() + 30);
      else if (duration === '90d') now.setDate(now.getDate() + 90);
      expiresAt = now.toISOString();
    }

    setIsSubmitting(true);

    try {
      await api.createPunishment({
        player_uuid: trimmedName,
        player_username: trimmedName,
        type: punishmentType,
        reason: reason.trim(),
        expires_at: expiresAt,
        evidence_url: evidenceUrl.trim() || undefined,
        server_scope: serverScope,
      });

      addToast({
        type: 'success',
        title: 'Punishment Issued',
        message: `Successfully applied ${punishmentType} to ${trimmedName}.`,
      });
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to dispatch punishment.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm font-sans">
      <div className="w-full max-w-xl rounded-2xl border border-[#141d3d] bg-[#060b1c] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#141d3d] bg-[#02040a] px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-rose-500/40 bg-rose-950/40 text-rose-400">
              <Ban className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white font-mono">Issue Network Punishment</h2>
              <p className="text-xs text-slate-400 font-sans">
                Apply real-time bans, mutes, or kicks across the UmbrellaOS network
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:text-white transition cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 font-mono text-xs overflow-y-auto flex-1">
          {errorMessage && (
            <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-3 text-xs text-rose-300 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Player Username */}
          <div>
            <label className="block text-slate-300 mb-1 font-semibold">Target Player (Username or UUID) *</label>
            <input
              type="text"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              placeholder="e.g. Notch, Alex, or 8667bafe-3c04-4090-a5fa-b68a1689dc7d"
              required
              className="w-full rounded-xl border border-[#141d3d] bg-[#02040a] px-3.5 py-2.5 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          {/* Punishment Type */}
          <div>
            <label className="block text-slate-300 mb-1 font-semibold">Punishment Type *</label>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
              {(['TEMP_BAN', 'BAN', 'IP_BAN', 'TEMP_MUTE', 'MUTE', 'KICK', 'WARN'] as const).map(
                (type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setPunishmentType(type)}
                    className={`py-2 px-2 rounded-lg border text-center font-bold text-[11px] transition cursor-pointer ${
                      punishmentType === type
                        ? 'bg-rose-950/80 border-rose-500 text-rose-200'
                        : 'bg-[#02040a] border-[#141d3d] text-slate-400 hover:text-white'
                    }`}
                  >
                    {type.replace('_', ' ')}
                  </button>
                )
              )}
            </div>
          </div>

          {/* Duration if temporary */}
          {(punishmentType === 'TEMP_BAN' || punishmentType === 'TEMP_MUTE') && (
            <div>
              <label className="block text-slate-300 mb-1 font-semibold">Duration</label>
              <div className="flex gap-2">
                {['1d', '7d', '30d', '90d'].map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDuration(d)}
                    className={`flex-1 py-1.5 rounded-lg border text-center font-bold transition cursor-pointer ${
                      duration === d
                        ? 'bg-indigo-950/80 border-indigo-500 text-indigo-200'
                        : 'bg-[#02040a] border-[#141d3d] text-slate-400 hover:text-white'
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Server Scope */}
          <div>
            <label className="block text-slate-300 mb-1 font-semibold">Server Scope</label>
            <select
              value={serverScope}
              onChange={(e) => setServerScope(e.target.value)}
              className="w-full rounded-xl border border-[#141d3d] bg-[#02040a] px-3.5 py-2.5 text-white focus:border-indigo-500 focus:outline-none cursor-pointer"
            >
              <option value="GLOBAL">Global (All Cluster Nodes)</option>
              {servers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.id})
                </option>
              ))}
            </select>
          </div>

          {/* Reason */}
          <div>
            <label className="block text-slate-300 mb-1 font-semibold">Reason *</label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              className="w-full rounded-xl border border-[#141d3d] bg-[#02040a] px-3.5 py-2.5 text-white focus:border-indigo-500 focus:outline-none"
            />
            <div className="flex flex-wrap gap-1.5 mt-2">
              {presetReasons.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setReason(p)}
                  className="px-2 py-0.5 rounded bg-[#02040a] border border-[#141d3d] text-[10px] text-slate-400 hover:text-indigo-300 hover:border-indigo-500/40 transition cursor-pointer"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Evidence URL */}
          <div>
            <label className="block text-slate-300 mb-1 font-semibold">Evidence URL (Optional)</label>
            <input
              type="url"
              value={evidenceUrl}
              onChange={(e) => setEvidenceUrl(e.target.value)}
              placeholder="https://imgur.com/... or https://youtube.com/..."
              className="w-full rounded-xl border border-[#141d3d] bg-[#02040a] px-3.5 py-2.5 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          {/* Footer actions */}
          <div className="flex justify-end gap-3 pt-3 border-t border-[#141d3d]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-[#141d3d] bg-[#02040a] text-slate-400 hover:text-white cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-xl border border-rose-500/50 bg-rose-600 hover:bg-rose-500 text-white font-bold transition disabled:opacity-50 cursor-pointer shadow-[0_0_12px_rgba(244,63,94,0.3)]"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Enforcing...</span>
                </>
              ) : (
                <>
                  <Ban className="h-3.5 w-3.5" />
                  <span>Enforce Punishment</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
