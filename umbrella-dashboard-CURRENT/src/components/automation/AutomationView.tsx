import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { AutomationCronTask } from '../../types/dashboard';
import { CreateCronModal } from '../modals/CreateCronModal';
import {
  Clock,
  Play,
  Pause,
  Plus,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Shield,
  RefreshCw,
  Activity,
  Terminal,
  Trash2,
  Server,
  Layers
} from 'lucide-react';

interface AutomationViewProps {
  onOpenCreateCronModal?: () => void;
}

export const AutomationView: React.FC<AutomationViewProps> = ({ onOpenCreateCronModal }) => {
  const {
    crons,
    toggleCronTask,
    runCronTaskNow,
    deleteCronTask,
    servers,
    addToast
  } = useDashboard();

  const [createModalOpen, setCreateModalOpen] = useState(false);

  const handleOpenModal = () => {
    if (onOpenCreateCronModal) {
      onOpenCreateCronModal();
    } else {
      setCreateModalOpen(true);
    }
  };

  return (
    <div className="space-y-6 pb-12 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <Clock className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight font-display">
                Automations & Cron Task Schedules
              </h1>
              <p className="text-xs text-slate-400">
                Scheduled world backups, memory leak auto-scavengers, Discord relays, and autonomous TPS stabilizers
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleOpenModal}
            className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2 text-xs font-semibold text-white hover:from-cyan-500 hover:to-blue-500 transition-all shadow-md cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Create Cron Schedule</span>
          </button>
        </div>
      </div>

      {/* Active Cron Tasks List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white tracking-tight font-display">Active Cron Schedules & Jobs</h2>
          <span className="text-xs font-mono text-slate-400">{crons.length} Jobs Configured</span>
        </div>

        <div className="space-y-3">
          {crons.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-8 text-center text-xs text-slate-500 font-mono">
              No cron tasks scheduled. Click "Create Cron Schedule" to configure automated routines.
            </div>
          ) : (
            crons.map(cron => (
              <div
                key={cron.id}
                className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-slate-700 transition-colors shadow-sm"
              >
                <div className="space-y-2 max-w-xl">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="font-bold text-white text-sm">{cron.name}</span>
                    <span className="font-mono text-xs text-cyan-300 bg-cyan-950/60 border border-cyan-500/30 px-2 py-0.5 rounded">
                      {cron.cronExpression}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                      cron.lastRunStatus === 'SUCCESS' ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30' :
                      'bg-rose-950/40 text-rose-300 border-rose-500/30'
                    }`}>
                      {cron.lastRunStatus} ({cron.durationMs}ms)
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed font-mono">
                    {cron.description}
                  </p>

                  <div className="flex items-center gap-4 text-xs font-mono text-slate-400 flex-wrap">
                    <span>Last Run: {cron.lastRunTime || 'Never'}</span>
                    <span>Next Run: {cron.nextRunTime}</span>
                    <span>Targets: {cron.targetServerIds.join(', ')}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => runCronTaskNow(cron.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 text-xs font-semibold text-slate-200 hover:text-white transition-colors cursor-pointer"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    <span>Run Now</span>
                  </button>

                  <button
                    onClick={() => toggleCronTask(cron.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold font-mono transition-colors border cursor-pointer ${
                      cron.enabled
                        ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30 hover:bg-slate-800 hover:text-slate-200'
                        : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-emerald-300'
                    }`}
                  >
                    {cron.enabled ? 'Enabled' : 'Paused'}
                  </button>

                  <button
                    onClick={() => deleteCronTask(cron.id)}
                    className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-950/30 transition-colors cursor-pointer"
                    title="Delete scheduled cron"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Create Cron Modal */}
      <CreateCronModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
      />
    </div>
  );
};
