import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { AutomationCronTask } from '../../types/dashboard';
import {
  Clock,
  X,
  Plus,
  Play,
  Server,
  Zap,
  HardDrive,
  RefreshCw,
  Bot,
  Flame,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

interface CreateCronModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CreateCronModal: React.FC<CreateCronModalProps> = ({ isOpen, onClose }) => {
  const { servers, createCronTask, addToast } = useDashboard();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [actionType, setActionType] = useState<AutomationCronTask['actionType']>('BACKUP_WORLDS');
  const [cronPreset, setCronPreset] = useState<'custom' | '15m' | 'hourly' | '6h' | 'daily_4am' | 'weekly'>('hourly');
  const [customCron, setCustomCron] = useState('0 * * * *');
  const [selectedServers, setSelectedServers] = useState<string[]>(['ALL']);
  const [enabled, setEnabled] = useState(true);

  if (!isOpen) return null;

  const presets = [
    { id: '15m', label: 'Every 15 Minutes', expr: '*/15 * * * *', desc: 'Frequent synchronization & memory checks' },
    { id: 'hourly', label: 'Every Hour', expr: '0 * * * *', desc: 'Hourly world deltas & player data snapshots' },
    { id: '6h', label: 'Every 6 Hours', expr: '0 */6 * * *', desc: 'Periodic logs truncation & DB vacuum' },
    { id: 'daily_4am', label: 'Daily at 4:00 AM (Quiet Hours)', expr: '0 4 * * *', desc: 'Full safe world backup and rolling restarts' },
    { id: 'weekly', label: 'Weekly on Sunday', expr: '0 3 * * 0', desc: 'Comprehensive snapshot archiving & telemetry cleanup' },
    { id: 'custom', label: 'Custom Cron Expression', expr: customCron, desc: 'Advanced cron syntax (Minute Hour DOM Month DOW)' }
  ];

  const handlePresetSelect = (pId: typeof cronPreset, expr: string) => {
    setCronPreset(pId);
    if (pId !== 'custom') {
      setCustomCron(expr);
    }
  };

  const handleToggleServer = (sId: string) => {
    if (sId === 'ALL') {
      setSelectedServers(['ALL']);
      return;
    }
    const withoutAll = selectedServers.filter(s => s !== 'ALL');
    if (withoutAll.includes(sId)) {
      const next = withoutAll.filter(s => s !== sId);
      setSelectedServers(next.length ? next : ['ALL']);
    } else {
      setSelectedServers([...withoutAll, sId]);
    }
  };

  const calculateNextRun = (expr: string): string => {
    if (expr.includes('*/15')) return 'In 15 minutes';
    if (expr.includes('0 * * * *')) return 'In 1 hour';
    if (expr.includes('0 */6')) return 'In 6 hours';
    if (expr.includes('0 4 * * *')) return 'Tomorrow at 04:00 AM UTC';
    if (expr.includes('0 3 * * 0')) return 'Next Sunday at 03:00 AM UTC';
    return 'Calculated on daemon save';
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      addToast('warning', 'Task Name Required', 'Please enter a name for the cron schedule.');
      return;
    }

    const effectiveCron = cronPreset === 'custom' ? customCron.trim() : (presets.find(p => p.id === cronPreset)?.expr || customCron);

    createCronTask({
      name: name.trim(),
      description: description.trim() || `Automated ${actionType.replace('_', ' ')} routine`,
      cronExpression: effectiveCron,
      actionType,
      targetServerIds: selectedServers,
      enabled,
      nextRunTime: calculateNextRun(effectiveCron)
    });

    onClose();
    // Reset fields
    setName('');
    setDescription('');
    setCronPreset('hourly');
    setCustomCron('0 * * * *');
    setSelectedServers(['ALL']);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 font-sans animate-in fade-in duration-150">
      <div className="w-full max-w-xl rounded-2xl border border-slate-700 bg-[#0d1117] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/90 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <Clock className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white font-display">Create Scheduled Cron Task</h2>
              <p className="text-xs text-slate-400 font-sans">Automate cluster maintenance, backups, and watchdog tasks</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto font-sans flex-1 text-xs">
          {/* Task Name & Action Type */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Task Name *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Hourly World Delta Backup"
                required
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Action Executed</label>
              <select
                value={actionType}
                onChange={(e) => setActionType(e.target.value as any)}
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none font-mono cursor-pointer"
              >
                <option value="BACKUP_WORLDS">📦 World & Inventory Snapshot (ZFS/R2)</option>
                <option value="RESTART_SERVER">🔄 Graceful Node Restart with 60s Warning</option>
                <option value="GC_SWEEP">⚡ JVM ZGC Garbage Sweep & RAM Reclaim</option>
                <option value="PURGE_LOGS">🧹 Vacuum Old Logs & Truncate Redis Streams</option>
                <option value="GRIM_SELF_TUNE">🛡️ GrimAC Vector Auto-Tuner & Threshold Sync</option>
                <option value="DISCORD_SYNC">🤖 DiscordSRV Player Stats & Leaderboard Sync</option>
              </select>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Description / Purpose</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Scans heap allocations, forces clean chunk write, and notifies Discord"
              className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
            />
          </div>

          {/* Cron Interval Presets */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2 flex items-center justify-between">
              <span>Execution Frequency</span>
              <span className="font-mono text-cyan-400 text-[11px]">
                {cronPreset === 'custom' ? customCron : (presets.find(p => p.id === cronPreset)?.expr || customCron)}
              </span>
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {presets.map((preset) => {
                const isSelected = cronPreset === preset.id;
                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => handlePresetSelect(preset.id as any, preset.expr)}
                    className={`text-left p-2.5 rounded-lg border transition-all cursor-pointer ${
                      isSelected
                        ? 'border-cyan-500/50 bg-cyan-950/30 text-white shadow-sm'
                        : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs text-slate-200">{preset.label}</span>
                      <span className="font-mono text-[10px] text-cyan-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                        {preset.expr}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1 truncate">{preset.desc}</p>
                  </button>
                );
              })}
            </div>

            {cronPreset === 'custom' && (
              <div className="mt-2.5">
                <label className="block text-[11px] text-slate-400 mb-1 font-mono">Custom Cron Syntax (Min Hour DOM Month DOW)</label>
                <input
                  type="text"
                  value={customCron}
                  onChange={(e) => setCustomCron(e.target.value)}
                  placeholder="0 4 * * 1-5"
                  className="w-full rounded-lg border border-cyan-500/40 bg-slate-900 px-3 py-2 text-xs font-mono text-cyan-300 focus:outline-none"
                />
              </div>
            )}
          </div>

          {/* Target Nodes Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
              <Server className="h-3.5 w-3.5 text-cyan-400" />
              <span>Target Server Nodes</span>
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => handleToggleServer('ALL')}
                className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition-all cursor-pointer border ${
                  selectedServers.includes('ALL')
                    ? 'bg-cyan-600 text-white border-cyan-500 shadow-sm'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                🌐 All Network Nodes
              </button>
              {servers.map(s => {
                const isSelected = selectedServers.includes(s.id);
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => handleToggleServer(s.id)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer border ${
                      isSelected && !selectedServers.includes('ALL')
                        ? 'bg-cyan-950/80 text-cyan-300 border-cyan-500/50'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {s.name}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Enable Toggle */}
          <div className="pt-2 flex items-center justify-between border-t border-slate-800">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-cyan-500 cursor-pointer"
              />
              <span className="text-xs text-slate-300 font-medium">
                Activate schedule immediately upon creation
              </span>
            </label>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2 text-xs font-semibold text-white hover:from-cyan-500 hover:to-blue-500 transition-all shadow-md cursor-pointer"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Save & Schedule Task</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
