import React, { useState, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { api, ServerRecord } from '../../lib/api';
import {
  Megaphone,
  X,
  Send,
  Radio,
  Loader2,
  AlertTriangle,
  Sparkles,
} from 'lucide-react';

interface BroadcastModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const BroadcastModal: React.FC<BroadcastModalProps> = ({ isOpen, onClose }) => {
  const { addToast } = useDashboard();
  const [servers, setServers] = useState<ServerRecord[]>([]);
  const [message, setMessage] = useState('');
  const [targetServerId, setTargetServerId] = useState<string>('GLOBAL');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setErrorMessage(null);
      api.getServers().then((res) => {
        if (res) setServers(res);
      }).catch(() => {});
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const quickTemplates = [
    '⚠️ Server maintenance scheduled in 15 minutes. Please complete your current tasks.',
    '🎉 Double Drop Multiplier and 2x XP is now active on all servers!',
    '🛡️ Anticheat engine updated to latest GrimAC build. Fair play enforced.',
    '⚡ New server event starting in 5 minutes! Use /event to join.',
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await api.broadcast(message.trim(), targetServerId === 'GLOBAL' ? undefined : targetServerId);
      addToast({
        type: 'success',
        title: 'Broadcast Dispatched',
        message: `Alert transmitted across ${targetServerId === 'GLOBAL' ? 'all nodes' : targetServerId}.`,
      });
      onClose();
      setMessage('');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to dispatch broadcast.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm font-sans">
      <div className="w-full max-w-xl rounded-2xl border border-[#1e1b4b] bg-[#0d1127] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#1e1b4b] bg-[#070914] px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-purple-500/40 bg-purple-950/40 text-purple-400">
              <Megaphone className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white font-mono">Broadcast Network Announcement</h2>
              <p className="text-xs text-slate-400 font-sans">
                Dispatch alerts to online Minecraft players via MiniMessage bridge
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

          {/* Scope */}
          <div>
            <label className="block text-slate-300 mb-1 font-semibold">Target Server Scope</label>
            <select
              value={targetServerId}
              onChange={(e) => setTargetServerId(e.target.value)}
              className="w-full rounded-xl border border-[#1e1b4b] bg-[#070914] px-3.5 py-2.5 text-white focus:border-purple-500 focus:outline-none cursor-pointer"
            >
              <option value="GLOBAL">Global (All Connected Minecraft Nodes)</option>
              {servers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.id})
                </option>
              ))}
            </select>
          </div>

          {/* Message text */}
          <div>
            <label className="block text-slate-300 mb-1 font-semibold">Broadcast Message *</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              placeholder="Enter announcement text (supports MiniMessage format e.g. <gradient:red:gold>Alert</gradient>)..."
              required
              className="w-full rounded-xl border border-[#1e1b4b] bg-[#070914] p-3 text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none font-sans"
            />
          </div>

          {/* Preset templates */}
          <div>
            <label className="block text-slate-400 mb-1 text-[11px]">Quick Templates</label>
            <div className="space-y-1.5">
              {quickTemplates.map((t, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setMessage(t)}
                  className="w-full text-left p-2 rounded-lg border border-[#1e1b4b] bg-[#070914] text-[11px] text-slate-300 hover:text-purple-300 hover:border-purple-500/40 transition truncate cursor-pointer"
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Footer actions */}
          <div className="flex justify-end gap-3 pt-3 border-t border-[#1e1b4b]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-[#1e1b4b] bg-[#070914] text-slate-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !message.trim()}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-xl border border-purple-500/50 bg-purple-600 hover:bg-purple-500 text-white font-bold transition disabled:opacity-50 cursor-pointer shadow-[0_0_12px_rgba(168,85,247,0.3)]"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Transmitting...</span>
                </>
              ) : (
                <>
                  <Send className="h-3.5 w-3.5" />
                  <span>Send Broadcast</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
