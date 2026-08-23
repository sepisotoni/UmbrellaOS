import React, { useState, useEffect } from 'react';
import { api, FeatureFlag } from '../../lib/api';
import { useDashboard } from '../../context/DashboardContext';
import { DisconnectedBanner } from '../common/DisconnectedBanner';
import {
  Flag,
  Plus,
  Trash2,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  XCircle,
  X,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react';

export const FeatureFlagsView: React.FC = () => {
  const { addToast } = useDashboard();
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // New flag modal
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [newName, setNewName] = useState<string>('');
  const [newDescription, setNewDescription] = useState<string>('');
  const [newEnabled, setNewEnabled] = useState<boolean>(true);
  const [newPercentage, setNewPercentage] = useState<number>(100);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const fetchFlags = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getFeatureFlags();
      setFlags(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load feature flags');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFlags();
  }, []);

  const handleToggle = async (flag: FeatureFlag) => {
    try {
      await api.setFeatureFlag({
        name: flag.name,
        enabled: !flag.enabled,
        description: flag.description,
        percentage: flag.percentage,
      });
      addToast({
        type: 'success',
        title: 'Flag Toggled',
        message: `${flag.name} is now ${!flag.enabled ? 'Enabled' : 'Disabled'}.`,
      });
      fetchFlags();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Toggle Failed',
        message: err.message,
      });
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete feature flag "${name}"?`)) return;

    try {
      await api.deleteFeatureFlag(name);
      addToast({
        type: 'success',
        title: 'Flag Deleted',
        message: `Removed ${name}.`,
      });
      fetchFlags();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Delete Failed',
        message: err.message,
      });
    }
  };

  const handleCreateFlag = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;

    setIsSubmitting(true);
    try {
      await api.setFeatureFlag({
        name: newName.trim(),
        enabled: newEnabled,
        description: newDescription.trim() || undefined,
        percentage: newPercentage,
      });
      addToast({
        type: 'success',
        title: 'Flag Created',
        message: `Registered feature flag "${newName.trim()}".`,
      });
      setIsAddModalOpen(false);
      setNewName('');
      setNewDescription('');
      setNewPercentage(100);
      fetchFlags();
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'Create Failed',
        message: err.message,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div id="umbrella-feature-flags-view" className="space-y-6">
      <DisconnectedBanner />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <span>Dynamic Feature Flags</span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-purple-950/80 border border-purple-800/40 text-purple-300">
              {flags.length} Flags
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Toggle network subsystems, roll out beta capabilities, and manage gradual feature rollouts.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            id="create-flag-btn"
            onClick={() => setIsAddModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-purple-500/40 bg-purple-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-purple-500 transition cursor-pointer shadow-[0_0_12px_rgba(168,85,247,0.3)]"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Create Flag</span>
          </button>

          <button
            id="flags-refresh-btn"
            onClick={fetchFlags}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e1b4b] bg-[#0d1127] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-purple-500/40 hover:text-white transition cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
          <div>
            <span className="font-bold">Error loading feature flags:</span>
            <p className="mt-0.5 text-rose-200/80">{error}</p>
          </div>
        </div>
      )}

      {/* Feature Flags Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {isLoading ? (
          <div className="col-span-full py-12 text-center text-xs text-slate-500 font-mono">
            Loading feature flags from core...
          </div>
        ) : flags.length === 0 ? (
          <div className="col-span-full py-12 text-center text-xs text-slate-500 font-mono">
            No dynamic feature flags registered yet.
          </div>
        ) : (
          flags.map((flag) => (
            <div
              key={flag.name}
              className="rounded-xl border border-[#1e1b4b] bg-[#0d1127] p-5 shadow-xl flex flex-col justify-between font-mono text-xs"
            >
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-[#1e1b4b]">
                  <div className="flex items-center gap-2">
                    <Flag className="h-4 w-4 text-purple-400" />
                    <span className="font-bold text-white text-sm">{flag.name}</span>
                  </div>

                  <button
                    onClick={() => handleToggle(flag)}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-bold transition cursor-pointer ${
                      flag.enabled
                        ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/40'
                        : 'bg-slate-900 text-slate-400 border border-slate-800'
                    }`}
                  >
                    {flag.enabled ? 'ENABLED' : 'DISABLED'}
                  </button>
                </div>

                <div className="mt-3 text-slate-300 font-sans text-xs">
                  {flag.description || 'No description provided.'}
                </div>

                <div className="mt-4 flex items-center justify-between text-slate-400 text-[11px]">
                  <span>Rollout Target:</span>
                  <span className="text-purple-300 font-bold">{flag.percentage || 100}%</span>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-[#1e1b4b] flex justify-end">
                <button
                  onClick={() => handleDelete(flag.name)}
                  className="inline-flex items-center gap-1 text-[11px] text-slate-500 hover:text-rose-400 transition cursor-pointer"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>Delete Flag</span>
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal: Create Feature Flag */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-[#1e1b4b] bg-[#0d1127] p-6 shadow-2xl space-y-5 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-[#1e1b4b] pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Flag className="h-4 w-4 text-purple-400" />
                <span>Register Feature Flag</span>
              </h3>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateFlag} className="space-y-4">
              <div>
                <label className="block text-slate-300 mb-1">Flag Name (Key)</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. enable_ai_appeals, beta_anticheat_v2"
                  required
                  className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1">Description</label>
                <textarea
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Briefly describe what this feature controls..."
                  rows={2}
                  className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none font-sans"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1">Rollout Percentage (0 - 100%)</label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={newPercentage}
                  onChange={(e) => setNewPercentage(Number(e.target.value))}
                  className="w-full rounded-lg border border-[#1e1b4b] bg-[#070914] p-2.5 text-white focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="flag-new-enabled"
                  checked={newEnabled}
                  onChange={(e) => setNewEnabled(e.target.checked)}
                  className="rounded border-[#1e1b4b] bg-[#070914] text-purple-600 focus:ring-purple-500"
                />
                <label htmlFor="flag-new-enabled" className="text-slate-300">
                  Enable Immediately
                </label>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="flex-1 py-2 rounded-lg border border-[#1e1b4b] bg-[#070914] text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 py-2 rounded-lg border border-purple-500/50 bg-purple-600 hover:bg-purple-500 text-white font-bold disabled:opacity-50"
                >
                  {isSubmitting ? 'Saving...' : 'Create Flag'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
