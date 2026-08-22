import React, { useState } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { SnapshotCheckpoint } from '../../types/dashboard';
import {
  History,
  Camera,
  RotateCcw,
  Clock,
  HardDrive,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  Tag,
  Search,
  Filter,
  Plus
} from 'lucide-react';

export const SnapshotsView: React.FC = () => {
  const {
    snapshots,
    servers,
    createSnapshot,
    rollbackToSnapshot,
    addToast
  } = useDashboard();

  const [selectedServerId, setSelectedServerId] = useState<string>(servers[0]?.id || 'survival-alpha');
  const [snapshotType, setSnapshotType] = useState<SnapshotCheckpoint['type']>('MANUAL');
  const [tagInput, setTagInput] = useState<string>('checkpoint, staff-review');
  const [searchQuery, setSearchQuery] = useState('');

  const handleCaptureSnapshot = () => {
    const tags = tagInput.split(',').map(t => t.trim()).filter(Boolean);
    createSnapshot(selectedServerId, snapshotType, tags.length ? tags : ['manual']);
  };

  const filteredSnapshots = snapshots.filter(s => {
    const matchesSearch = !searchQuery || 
      s.serverName.toLowerCase().includes(searchQuery.toLowerCase()) || 
      s.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.tags.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesSearch;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Top Bar Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-950/40 text-cyan-400">
              <History className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight font-display">
                Time-Travel Snapshots & Delta Rollback Studio
              </h1>
              <p className="text-xs text-slate-400">
                Hourly automated delta world snapshots, player inventory state time-machine, and 1-click disaster recovery
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-2.5 py-1 rounded">
            ZFS / CoW Delta Active
          </span>
        </div>
      </div>

      {/* Snapshot Capture Station */}
      <div className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 space-y-4 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Camera className="h-4 w-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white font-display">Capture Immediate Snapshot Checkpoint</h3>
          </div>
          <span className="text-xs font-mono text-slate-400">Sub-second freeze</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-xs">
          <div>
            <label className="block font-semibold text-slate-300 mb-1">Target Instance</label>
            <select
              value={selectedServerId}
              onChange={(e) => setSelectedServerId(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none font-mono"
            >
              {servers.map(s => (
                <option key={s.id} value={s.id}>{s.name} ({s.playersCount} players online)</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-300 mb-1">Snapshot Type</label>
            <select
              value={snapshotType}
              onChange={(e) => setSnapshotType(e.target.value as any)}
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none font-mono"
            >
              <option value="MANUAL">Manual Operator Checkpoint</option>
              <option value="PRE_DEPLOY">Pre-Deployment Freeze</option>
              <option value="INCIDENT_FREEZE">Incident Griefing / Exploit Freeze</option>
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-300 mb-1">Tags (Comma-Separated)</label>
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              placeholder="e.g. boss-fight, pre-reset, audit"
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
            />
          </div>
        </div>

        <div className="flex items-center justify-end pt-1">
          <button
            onClick={handleCaptureSnapshot}
            className="flex items-center gap-2 rounded-lg bg-cyan-600 px-5 py-2 text-xs font-semibold text-white hover:bg-cyan-500 transition-colors shadow-sm font-mono"
          >
            <Camera className="h-4 w-4" />
            <span>Capture Snapshot Now</span>
          </button>
        </div>
      </div>

      {/* Snapshot List & Rollback Catalog */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 bg-[#0c1017] p-3 rounded-xl border border-slate-800 font-mono">
          <div className="flex items-center gap-2 flex-1 max-w-md">
            <Search className="h-4 w-4 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search snapshots by ID, server, or tags..."
              className="w-full bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none font-mono"
            />
          </div>
          <span className="text-xs font-mono text-slate-400">{filteredSnapshots.length} Checkpoints Available</span>
        </div>

        <div className="space-y-3">
          {filteredSnapshots.length === 0 ? (
            <div className="p-8 rounded-xl border border-slate-800 bg-[#0c1017] text-center text-xs text-slate-500 font-mono">
              No snapshot checkpoints created yet. Click "Capture Snapshot Now" to record a restore point.
            </div>
          ) : (
            filteredSnapshots.map(snap => (
              <div
                key={snap.id}
                className="rounded-xl border border-slate-800 bg-[#0c1017] p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-slate-700 transition-colors"
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-white text-sm font-mono">{snap.serverName}</span>
                    <span className="text-[11px] font-mono text-cyan-300 bg-cyan-950/60 border border-cyan-500/30 px-2 py-0.5 rounded">
                      {snap.id}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                      snap.type === 'INCIDENT_FREEZE' ? 'bg-rose-950/40 text-rose-300 border-rose-500/30' :
                      snap.type === 'AUTO_HOURLY' ? 'bg-indigo-950/40 text-indigo-300 border-indigo-500/30' :
                      'bg-slate-800 text-slate-300 border-slate-700'
                    }`}>
                      {snap.type}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-xs font-mono text-slate-400 flex-wrap">
                    <span>📅 {snap.timestamp}</span>
                    <span>📦 Size: {snap.sizeMb} MB</span>
                    <span>🧱 {snap.blockChangesCount.toLocaleString()} Block Changes</span>
                    <span>👤 {snap.playerStatesCount} Player Inventories</span>
                  </div>

                  <div className="flex items-center gap-1.5 flex-wrap">
                    {snap.tags.map(tag => (
                      <span key={tag} className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-400 flex items-center gap-1">
                        <Tag className="h-2.5 w-2.5 text-cyan-400" />
                        <span>{tag}</span>
                      </span>
                    ))}
                    <span className="text-[10px] font-mono text-slate-600 truncate max-w-xs">{snap.hash}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 font-mono">
                  <button
                    onClick={() => rollbackToSnapshot(snap.id)}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold transition-colors shadow-sm"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    <span>Restore Snapshot</span>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
