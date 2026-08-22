import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { Key, X, Plus, Shield } from 'lucide-react';

interface CreateApiKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CreateApiKeyModal: React.FC<CreateApiKeyModalProps> = ({ isOpen, onClose }) => {
  const { createApiKey, addToast } = useDashboard();

  const [name, setName] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<string[]>(['read:servers', 'read:players']);

  if (!isOpen) return null;

  const availableScopes = [
    { id: 'read:servers', label: 'read:servers', desc: 'Query live instance TPS, player counts and metrics' },
    { id: 'write:servers', label: 'write:servers', desc: 'Create, modify and stop server containers' },
    { id: 'exec:console', label: 'exec:console', desc: 'Send console commands to server processes' },
    { id: 'read:punishments', label: 'read:punishments', desc: 'Read bans, mutes, kicks and warnings' },
    { id: 'write:punishments', label: 'write:punishments', desc: 'Issue new punishments and pardons' },
    { id: 'read:players', label: 'read:players', desc: 'Query player accounts, ranks, and alt graphs' },
    { id: 'manage:plugins', label: 'manage:plugins', desc: 'Hot-reload and modify plugin configurations' },
    { id: 'manage:snapshots', label: 'manage:snapshots', desc: 'Trigger rollbacks and delta snapshots' }
  ];

  const toggleScope = (scopeId: string) => {
    setSelectedScopes(prev => 
      prev.includes(scopeId) ? prev.filter(s => s !== scopeId) : [...prev, scopeId]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    createApiKey(name.trim(), selectedScopes);
    onClose();
    setName('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 font-sans animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-[#0f131a] shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/80 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <Key className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white font-display">Generate Scoped API Key</h3>
              <p className="text-[11px] text-slate-400">Fine-grained RBAC permissions for bots, webstores and integrations</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs font-sans">
          <div>
            <label className="block font-semibold text-slate-300 mb-1">Key Name / Identifier</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Tebex Webstore Ingestion Bot"
              required
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-300 mb-2">Select Scopes & Capabilities</label>
            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
              {availableScopes.map(scope => {
                const checked = selectedScopes.includes(scope.id);
                return (
                  <div
                    key={scope.id}
                    onClick={() => toggleScope(scope.id)}
                    className={`flex items-start gap-2.5 p-2 rounded-lg border cursor-pointer transition-colors ${
                      checked ? 'bg-cyan-950/30 border-cyan-500/40 text-white' : 'bg-slate-900/60 border-slate-800 text-slate-400'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => {}}
                      className="mt-0.5 h-3.5 w-3.5 rounded border-slate-700 bg-slate-800 text-cyan-500 pointer-events-none"
                    />
                    <div>
                      <div className="font-mono text-[11px] font-bold text-cyan-300">{scope.label}</div>
                      <div className="text-[10px] text-slate-400">{scope.desc}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 border-t border-slate-800 pt-4 mt-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-slate-700 px-4 py-2 font-semibold text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-md bg-cyan-600 px-4 py-2 font-semibold text-white hover:bg-cyan-500 transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm"
            >
              <Key className="h-3.5 w-3.5" />
              <span>Generate API Key</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
